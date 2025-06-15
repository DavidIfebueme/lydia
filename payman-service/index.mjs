import express from "express";
import cors from "cors";
import { PaymanClient } from "@paymanai/payman-ts";
import dotenv from "dotenv";
import https from "https";
import http from "http";

dotenv.config();

const httpsAgent = new https.Agent({
  keepAlive: true,
  timeout: 30000,
  keepAliveTimeout: 30000,
  maxSockets: 50
});

const httpAgent = new http.Agent({
  keepAlive: true,
  timeout: 30000,
  keepAliveTimeout: 30000,
  maxSockets: 50
});

https.globalAgent = httpsAgent;
http.globalAgent = httpAgent;

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
    console.log("Code received:", code ? code.substring(0, 20) + "..." : "No code");

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

    console.log("🔄 Getting access token (following official pattern)...");
    
    const tokenResponse = await client.getAccessToken();

    console.log("Token response received:", !!tokenResponse);
    console.log("Token response keys:", tokenResponse ? Object.keys(tokenResponse) : "none");

    if (!tokenResponse?.accessToken) {
      console.error("Invalid token response - no access token received");
      console.error("Token response:", tokenResponse);
      return res.status(500).json({
        success: false,
        error: "Invalid token response from Payman",
        debug: tokenResponse
      });
    }

    console.log("✅ Token exchange successful");
    console.log("Access token length:", tokenResponse.accessToken?.length || 0);

    res.json({
      success: true,
      accessToken: tokenResponse.accessToken,
      expiresIn: tokenResponse.expiresIn,
      userId: tokenResponse.userId || tokenResponse.user_id || "unknown"
    });

  } catch (error) {
    console.error("Token exchange failed:", error.message);
    console.error("Error type:", error.constructor.name);
    console.error("Error code:", error.code);
    console.error("Full error:", error);
    
    res.status(500).json({
      success: false,
      error: "Token exchange failed: " + error.message,
      details: error.code || "unknown",
      type: error.constructor.name
    });
  }
});

app.post("/charge", async (req, res) => {
  try {
    const { accessToken, amount, description, userId } = req.body;
    console.log(`🔄 Attempting to charge $${amount} for: ${description}`);
    
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    
    const result = await client.ask(`charge user ${userId} $${amount} for ${description}`);
    console.log("✅ Charge successful");
    res.json({ success: true, result });
    
  } catch (error) {
    console.error("Charge failed:", error);
    res.status(500).json({ 
      error: "Charge failed", 
      details: error.message,
      code: error.code 
    });
  }
});

app.post("/payout", async (req, res) => {
  try {
    const { accessToken, amount, userId, description } = req.body;
    console.log(`🔄 Attempting payout of $${amount} to user ${userId}`);
    
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    
    const result = await client.ask(`send $${amount} to user ${userId} for ${description}`);
    console.log("✅ Payout successful");
    res.json({ success: true, result });
    
  } catch (error) {
    console.error("Payout failed:", error);
    res.status(500).json({ 
      error: "Payout failed", 
      details: error.message 
    });
  }
});

app.post("/balance", async (req, res) => {
  try {
    const { accessToken } = req.body;
    console.log("🔄 Checking wallet balance");
    
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    
    const result = await client.ask("list all my wallets and their balances");
    console.log("✅ Balance check successful");
    res.json({ success: true, balance: result });
    console.log("Balance data:", result);
    
  } catch (error) {
    console.error("Balance check failed:", error);
    res.status(500).json({ 
      error: "Balance check failed", 
      details: error.message 
    });
  }
});


process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Payman service running on port ${PORT}`);
  console.log(`📍 Health check: http://localhost:${PORT}/health`);
  console.log(`🌐 Network agents configured for better connectivity`);
});