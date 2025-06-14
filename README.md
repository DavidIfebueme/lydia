# 💰 Lydia

A global, real-money problem solving game powered by [Payman](https://paymanai.com).  
Users pay a small fee to guess the answer to a riddle or problem.  
Each guess contributes to the prize pool. First correct guess wins the pot.

---

## 🔥 How It Works

1. Connect your wallet using Payman OAuth.
2. View the current challenge (riddle/problem).
3. Submit a guess (each guess costs a small amount).
4. Prize pool grows with each incorrect guess.
5. First user to submit the correct answer gets the pot — instantly.
6. Game auto-resets with a new problem.

---

## 🧱 Monorepo Structure
```
payman-riddle-game/
├── backend/ # FastAPI backend API
├── frontend/ # Next.js frontend UI
├── .env # Shared environment variables

```
---

## ⚙️ Tech Stack

**Backend**
- Python 3.12
- FastAPI
- PostgreSQL DB
- Payman SDK (via natural-language `ask()` calls)

**Frontend**
- Next.js (App Router, TypeScript)
- Tailwind CSS
- Payman OAuth (Connect button)

**Other**
- Monorepo layout
- `.env` support

---

