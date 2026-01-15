# 🚀 LifePilot — Smart Personal Life OS

A local-first personal productivity app with AI-powered categorization and prioritization. All data stored locally in SQLite.

![LifePilot](https://img.shields.io/badge/Status-MVP-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11+-blue) ![React](https://img.shields.io/badge/React-18-61DAFB)

## ✨ Features

- **Universal Inbox** — Capture anything: tasks, notes, decisions, reminders
- **AI Auto-Categorization** — Automatically classifies and extracts metadata using Groq AI
- **Today's Focus** — AI-selected priorities for maximum daily impact
- **Privacy-First** — PII stripping before AI calls, all data stored locally
- **Beautiful Dark UI** — Premium glassmorphism design with smooth animations

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLite |
| Frontend | React 18, Vite, TailwindCSS |
| AI | Groq API (llama3-8b-8192, llama3-70b-8192) |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API Key ([Get one free](https://console.groq.com))

### 1. Clone & Setup Environment

```bash
cd lifepilot
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open in Browser

Navigate to **http://localhost:5173**

## 📁 Project Structure

```
lifepilot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite management
│   ├── models.py            # Pydantic models
│   ├── routers/
│   │   ├── items.py         # Item CRUD endpoints
│   │   └── focus.py         # Today's Focus endpoint
│   └── services/
│       ├── groq_service.py  # Groq API wrapper
│       ├── categorizer.py   # AI categorization
│       ├── focus_picker.py  # AI focus selection
│       └── pii_stripper.py  # PII sanitization
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── InboxInput.jsx
│           ├── ItemCard.jsx
│           ├── TodayFocus.jsx
│           └── Dashboard.jsx
└── README.md
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/items` | Create & categorize new item |
| GET | `/api/items` | List items (filterable) |
| PATCH | `/api/items/{id}` | Update item |
| DELETE | `/api/items/{id}` | Delete item |
| GET | `/api/focus/today` | Get AI-selected focus items |

## 🧠 AI Models Used

- **llama3-8b-8192** — Fast categorization (~200ms)
- **llama3-70b-8192** — Smart focus selection (~1s)

## 🔒 Privacy

- All data stored locally in `./database/lifepilot.db`
- PII (emails, phones, names) stripped before AI calls
- No data sent to cloud except anonymized text to Groq

## 📝 License

MIT
