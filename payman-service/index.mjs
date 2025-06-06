import express from "express";
import cors from "cors";
import { PaymanClient } from "@paymanai/payman-ts";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

if (!process.env.PAYMAN_CLIENT_ID || !process.env.PAYMAN_CLIENT_SECRET) {
  console.error(
    "ERROR: PAYMAN_CLIENT_ID and PAYMAN_CLIENT_SECRET environment variables are required"
  );
  process.exit(1);
}

const config = {
  clientId: process.env.PAYMAN_CLIENT_ID,
  clientSecret: process.env.PAYMAN_CLIENT_SECRET,
};


app.use(
  cors({
    origin: ["http://localhost:8000", "http://localhost:3000"],
    credentials: true,
  })
);
app.use(express.json());

app.get("/health", (req, res) => {
  res.json({ status: "healthy", timestamp: new Date().toISOString() });
});

app.post("/oauth/exchange", async (req, res) => {
  try {
    const { code } = req.body;

    console.log("🔄 Received token exchange request");
    console.log(
      "Code received:",
      code ? code.substring(0, 20) + "..." : "No code"
    );

    if (!code) {
      console.error("No authorization code provided in request");
      return res.status(400).json({
        success: false,
        error: "Authorization code is required",
      });
    }

    console.log("🔄 Creating Payman client with auth code...");

    const client = PaymanClient.withAuthCode(
      {
        clientId: config.clientId,
        clientSecret: config.clientSecret,
      },
      code
    );

    console.log("⏳ Waiting for client initialization...");
    await new Promise((resolve) => setTimeout(resolve, 7000));

    console.log("🔄 Getting access token...");
    const tokenResponse = await client.getAccessToken();

    console.log("Token response received:", !!tokenResponse);

    if (!tokenResponse?.accessToken) {
      console.error("Invalid token response - no access token received");
      console.error("Token response:", tokenResponse);
      return res.status(500).json({
        success: false,
        error: "Invalid token response from Payman",
      });
    }

    console.log("✅ Token exchange successful");

    res.json({
      success: true,
      accessToken: tokenResponse.accessToken,
      expiresIn: tokenResponse.expiresIn,
      userId: tokenResponse.userId
    });
  } catch (error) {
    console.error("Token exchange failed:", error.message);
    console.error("Full error:", error);
    res.status(500).json({
      success: false,
      error: "Token exchange failed: " + error.message,
    });
  }
});

app.post("/charge", async (req, res) => {
  try {
    const { accessToken, amount, description, userId } = req.body;
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    const result = await client.ask(`charge ${userId} $${amount} for ${description}`);
    res.json({ success: true, result });
  } catch (error) {
    console.error("Charge failed:", error);
    res.status(500).json({ error: "Charge failed", details: error.message });
  }
});

app.post("/payout", async (req, res) => {
  try {
    const { accessToken, amount, userId, description } = req.body;
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    const result = await client.ask(`send $${amount} to user ${userId} for ${description}`);
    res.json({ success: true, result });
  } catch (error) {
    console.error("Payout failed:", error);
    res.status(500).json({ error: "Payout failed", details: error.message });
  }
});

app.post("/balance", async (req, res) => {
  try {
    const { accessToken } = req.body;
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    const result = await client.ask("list all my wallets and their balances");
    res.json({ success: true, balance: result });
  } catch (error) {
    console.error("Balance check failed:", error);
    res.status(500).json({ error: "Balance check failed" });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Payman service running on port ${PORT}`);
  console.log(`📍 Health check: http://localhost:${PORT}/health`);
});