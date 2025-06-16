import express from "express";
import cors from "cors";
import { PaymanClient } from "@paymanai/payman-ts";
import dotenv from "dotenv";
import https from "https";
import http from "http";
import { randomInt } from "crypto";

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

    const payeeName = `Test Payee ${Date.now()}`;
    console.log("🔄 Creating test payee with name:", payeeName);

    let payeeId = null;
    try {
      const payeeResponse = await client.ask(`create a test payee for this account with name ${payeeName}`);
      console.log("Payee created response:", payeeResponse);
      
      if (payeeResponse?.artifacts) {
        for (const artifact of payeeResponse.artifacts) {
          if (artifact.name === 'response' && artifact.content) {
            console.log("Found response artifact with content");
            const content = artifact.content;
            
            const pdIndex = content.indexOf('pd-');
            
            if (pdIndex !== -1) {
              const payeeIdStart = content.substring(pdIndex);
              const idPattern = /pd-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/;
              const match = payeeIdStart.match(idPattern);
              
              if (match && match[0]) {
                payeeId = match[0];
                console.log("✅ Extracted Payee ID:", payeeId);
              } else {
                const simpleMatch = payeeIdStart.match(/^(pd-[a-f0-9-]+)/);
                if (simpleMatch && simpleMatch[1]) {
                  payeeId = simpleMatch[1];
                  console.log("✅ Extracted Payee ID (simple method):", payeeId);
                } else {
                  console.log("Could not extract payee ID with standard patterns");
                }
              }
            } else {
              console.log("No pd- pattern found in response content");
            }
          }
        }
      }
        } catch (err) {
          console.error("Error creating payee:", err);
        }

        const responseData = {
          success: true,
          accessToken: tokenResponse.accessToken,
          expiresIn: tokenResponse.expiresIn,
          userId: tokenResponse.paymanUserId || tokenResponse.payman_user_id || "unknown",
          payeeId: payeeId
        };

        res.json(responseData);

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
    
    const APP_WALLET_ID = process.env.PAYMAN_APP_WALLET_ID;
    
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    
    const result = await client.ask(`charge user ${userId} $${amount} for ${description} and deposit to wallet ${APP_WALLET_ID}`);
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
    const { accessToken, amount, payeeId, description } = req.body;
    console.log(`🔄 Attempting payout of $${amount} to user ${payeeId}`);
    
    const APP_WALLET_ID = process.env.PAYMAN_APP_WALLET_ID;
    
    const client = PaymanClient.withToken(config.clientId, {
      accessToken,
      expiresIn: 3600
    });
    
    const result = await client.ask(`send $${amount} from wallet ${APP_WALLET_ID} to payee ${payeeId} for ${description}`);
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