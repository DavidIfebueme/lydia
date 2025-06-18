import { PaymanClient } from "@paymanai/payman-ts";
import fs from "fs/promises";
import path from "path";

class TokenManager {
  constructor(clientId, clientSecret) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.tokenFile = path.join(process.cwd(), "app-token.json");
    this.tokenData = null;
    this.refreshing = false;
  }

  async initialize() {
    try {
      await this.loadTokenFromFile();
      
      if (this.shouldRefreshToken()) {
        await this.refreshToken();
      }
      
      console.log("✅ Token manager initialized");
    } catch (error) {
      console.error("Error initializing token manager:", error);
      await this.refreshToken();
    }
    
    this.startRefreshTimer();
  }
  
  async loadTokenFromFile() {
    try {
      const data = await fs.readFile(this.tokenFile, 'utf8');
      this.tokenData = JSON.parse(data);
      console.log("📄 Loaded token from file, expires:", new Date(this.tokenData.expiresAt).toISOString());
    } catch (error) {
      console.log("📄 No token file found or invalid format, will create new token");
      this.tokenData = null;
    }
  }
  
  async saveTokenToFile() {
    try {
      await fs.writeFile(this.tokenFile, JSON.stringify(this.tokenData), 'utf8');
      console.log("📝 Saved token to file");
    } catch (error) {
      console.error("Error saving token to file:", error);
    }
  }
  
  shouldRefreshToken() {
    if (!this.tokenData || !this.tokenData.accessToken || !this.tokenData.expiresAt) {
      return true;
    }
    
    const expiresAt = new Date(this.tokenData.expiresAt);
    const now = new Date();
    const fifteenMinutesFromNow = new Date(now.getTime() + 15 * 60 * 1000);
    
    return expiresAt <= fifteenMinutesFromNow;
  }
  
  startRefreshTimer() {
    if (!this.tokenData || !this.tokenData.expiresAt) return;
    
    const expiresAt = new Date(this.tokenData.expiresAt);
    const now = new Date();
    
    let refreshTime = expiresAt.getTime() - now.getTime() - (15 * 60 * 1000);
    if (refreshTime < 60000) refreshTime = 60000;
    
    console.log(`🕒 Token refresh scheduled in ${Math.round(refreshTime/60000)} minutes`);
    
    setTimeout(() => {
      console.log("⏰ Refreshing token from scheduled timer");
      this.refreshToken().catch(err => console.error("Scheduled token refresh failed:", err));
      
      this.startRefreshTimer();
    }, refreshTime);
  }
  
  async refreshToken() {
    if (this.refreshing) {
      console.log("🔄 Token refresh already in progress, waiting...");
      return new Promise(resolve => {
        const checkInterval = setInterval(() => {
          if (!this.refreshing) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 500);
      });
    }
    
    this.refreshing = true;
    console.log("🔄 Refreshing app access token...");
    
    try {
      const client = PaymanClient.withClientCredentials({
        clientId: this.clientId,
        clientSecret: this.clientSecret
      });
      
      const tokenResponse = await client.getAccessToken();
      
      if (!tokenResponse?.accessToken) {
        throw new Error("Failed to get access token");
      }
      
      const expiresIn = tokenResponse.expiresIn || 3600;
      const expiresAt = new Date(Date.now() + expiresIn * 1000);
      
      this.tokenData = {
        accessToken: tokenResponse.accessToken,
        expiresIn: expiresIn,
        expiresAt: expiresAt.toISOString(),
        refreshedAt: new Date().toISOString()
      };
      
      await this.saveTokenToFile();
      
      console.log("✅ App token refreshed successfully, expires:", expiresAt.toISOString());
      this.refreshing = false;
      return this.tokenData.accessToken;
    } catch (error) {
      console.error("Failed to refresh app token:", error);
      this.refreshing = false;
      throw error;
    }
  }
  
  async getToken() {
    if (this.shouldRefreshToken()) {
      await this.refreshToken();
    }
    return this.tokenData?.accessToken;
  }
}

export default TokenManager;