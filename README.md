# Lydia - Telegram Game Bot

Lydia is a Telegram bot that creates an engaging problem solving and guessing game with real monetary stakes using Payman for wallet connections and transactions.


## 🚀 Features

- **Problem Solving and Guessing Games**: Solve puzzles and win real rewards
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

1. **Find the Bot on Telegram**: Search for `@Lydia_Payman_Bot` or [click here](https://t.me/lydia_payman_bot)
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

cost = base_cost * φ^(hours/6) * (1 + e^(hours/72)/10)


This creates an elegant progression:
- Hour 0-6: $0.50 - $0.81
- Hour 6-12: $0.81 - $1.31
- Hour 12-18: $1.31 - $2.12
- Hour 18-24: $2.12 - $3.43
- Hour 24+: Exponential growth

## 🛠️ Development Setup

### Prerequisites

- Python 3.9+
- Node.js 14+
- PostgreSQL 12+
- Poetry (Python package manager)
- Telegram Bot Token
- Payman Developer Account

### Local Development

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/lydia.git
cd lydia
```
2. **Set up backend**
```bash
cd backend
poetry install
touch .env  # Edit with your credentials
poetry run alembic upgrade head
poetry run python -m app.scripts.seed_problem
```
3. **Start Payman Service**
```bash
cd ../payman-service
npm install
cp .env.example .env  # Edit with your credentials
node index.mjs
```
4. **Run the fastapi backend**
```bash
cd ../backend
poetry run uvicorn app.main:app --reload
```


## 3. Testing Instructions for Your Team/Users

Here's a detailed testing guide you can share with your users or team members:

### How to Test Lydia Bot

1. **Initial Setup**
   - Open Telegram and search for `@Lydia_Payman_Bot`
   - Start a chat with the bot by clicking the "Start" button
   - Send the `/start` command

2. **Connecting Your Wallet**
   - Click the "Connect Your Payman Wallet" button that appears
   - You'll be redirected to the Payman authorization page
   - Grant access to your Payman wallet
   - After successful connection, you'll see a confirmation message

3. **Viewing the Current Problem**
   - Send `/problem` to see the active challenge
   - You'll see:
     - The problem description
     - Current prize pool amount
     - Current attempt cost
     - Time elapsed since problem started
     - Total attempts made

4. **Making an Attempt**
   - Simply send your answer as a text message
   - For the current problem ("I'm thinking of a random number between 1 and 200"), try any number
   - Check your wallet - you'll be charged the current attempt cost
   - The prize pool will increase by the amount you paid

5. **Checking Your Balance**
   - Send `/balance` to view your current Payman wallet balance
   - This helps verify that transactions are working correctly

6. **Winning the Prize** (for testing purposes)
   - When you send the correct answer, you'll:
     - Win 80% of the current prize pool
     - See funds transferred to your wallet immediately
     - Notice a new problem is generated automatically with 20% of the previous pool

This comprehensive testing approach ensures all aspects of your application function correctly, from wallet connection to prize distribution.
