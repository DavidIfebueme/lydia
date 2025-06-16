# Lydia - Mathematical Guessing Game Bot

Lydia is a Telegram bot that creates an engaging problem solving and guessing game with real monetary stakes using Payman for wallet connections and transactions.


## 🚀 Features

- **Problem Solving and Guessing Games**: Solve puzzles and win cryptocurrency rewards
- **Dynamic Cost Structure**: Uses the Golden Ratio and e to create a natural cost progression
- **Real-Time Prize Pools**: See the prize pool grow as players make attempts
- **Seamless Wallet Integration**: Connect your Payman wallet directly through Telegram
- **Automatic Payouts**: Winners receive rewards instantly to their connected wallet

## 🧠 How It Works

1. **Connect Your Payman Wallet**: Use the `/start` command to connect your Payman wallet
2. **View Current Problem**: Use `/problem` to see the active problem and prize pool
3. **Make an Attempt**: Simply send your answer as a message
4. **Win or Try Again**: Correct answers win 80% of the prize pool!

## 🔧 Technical Architecture

- **FastAPI Backend**: Handles Telegram webhooks and game logic
- **Node.js Payman Service**: Manages wallet connections and transactions
- **PostgreSQL Database**: Stores users, problems, attempts, and prize pools
- **Telegram Bot API**: Provides the user interface

## 🧪 Testing the Bot

1. **Find the Bot on Telegram**: Search for `@LydiaMathBot` or [click here](https://t.me/lydia_payman_bot)
2. **Connect Your Wallet**:
   - Send `/start` to the bot
   - Click the "Connect Your Payman Wallet" button
   - Complete the OAuth flow to grant access to your wallet
3. **View the Current Problem**:
   - Send `/problem` to see the active challenge
   - Note the current prize pool and attempt cost
4. **Make an Attempt**:
   - Send your answer as a message
   - If incorrect, the attempt cost will be charged to your wallet
   - The prize pool increases with each attempt
5. **Check Your Balance**:
   - Send `/balance` to view your wallet balance
6. **Win the Prize**:
   - If your answer is correct, you'll win 80% of the prize pool
   - Funds are automatically transferred to your wallet
   - A new problem begins with 20% of the previous pool

## 📊 Cost Structure

The attempt cost increases over time using a mathematical formula based on the Golden Ratio (φ) and Euler's number (e):
