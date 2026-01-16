# 🚀 LifePilot — Smart Personal Life OS

A local-first personal productivity app with AI-powered categorization and prioritization. All data stored locally in SQLite.

![LifePilot](https://img.shields.io/badge/Status-Production%20Ready-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11+-blue) ![React](https://img.shields.io/badge/React-18-61DAFB)

---

## ✨ Features

- **Universal Inbox** — Capture anything: tasks, notes, decisions, reminders
- **AI Auto-Categorization** — Automatically classifies and extracts metadata using Groq AI
- **Today's Focus** — AI-selected priorities for maximum daily impact
- **Smart Bookmarks** — Web clipping and read-later functionality
- **Decision Tracking** — Track important decisions with outcomes
- **Weekly Reviews** — Guided reflection and planning
- **Personal CRM** — Manage contacts, interactions, and follow-ups
- **Energy Logger** — Track and analyze energy patterns
- **Pattern Analysis** — AI-powered insights on your productivity
- **AI Agent** — Chat-based assistant with tool capabilities
- **Push Notifications** — Smart reminders (requires VAPID setup)
- **Calendar Integration** — Google Calendar sync (requires OAuth setup)
- **Privacy-First** — PII stripping before AI calls, all data stored locally
- **Beautiful Dark UI** — Premium glassmorphism design with smooth animations
- **Responsive Design** — Works seamlessly on desktop, tablet, and mobile

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLite |
| Frontend | React 18, Vite, TailwindCSS |
| AI | Groq API (llama3-8b-8192, llama3-70b-8192) |

---

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

---

## � Production Deployment

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GROQ_API_KEY=your_production_groq_api_key

# Optional (defaults shown)
DATABASE_PATH=./database/lifepilot.db
ENVIRONMENT=production
CORS_ORIGINS=["http://localhost:5173","https://yourdomain.com"]
```

### Option 1: Local Production Server

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run build
npm run preview
```

### Option 2: Docker Deployment (Recommended)

**Backend Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Option 3: Cloud Deployment

**Backend (Railway, Render, Fly.io):**
- Set environment variables in platform dashboard
- Deploy from `backend/` directory
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Frontend (Vercel, Netlify):**
- Build command: `npm run build`
- Output directory: `dist`
- Add environment variable for API URL if needed

---

## 📁 Project Structure

```
lifepilot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite management
│   ├── models.py            # Pydantic models
│   ├── routers/             # 17 API routers
│   └── services/            # Business logic & AI services
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/      # 16+ React components
│       └── hooks/           # Custom React hooks
├── database/                # SQLite database
└── README.md
```

---

## 🔌 API Endpoints (17 Routers)

| Router | Description |
|--------|-------------|
| Items | CRUD operations, follow-ups |
| Focus | AI-powered daily priorities |
| Bookmarks | Bookmark management |
| Decisions | Decision tracking |
| Reviews | Weekly reviews |
| Contacts | Personal CRM |
| Energy | Energy logging |
| Notifications | Smart notifications |
| Patterns | Pattern analysis |
| Suggestions | AI suggestions |
| Calendar | Calendar integration |
| Auth | OAuth authentication |
| Voice | Voice input |
| Push | Push notifications |
| Agent | LangGraph agent |
| Scheduler | Background tasks |
| Search | Natural language search |

**API Documentation:** `http://localhost:8000/docs`

---

## 📱 Responsive Design

| Viewport | Navigation | Features |
|----------|------------|----------|
| **Desktop** (≥1024px) | 9 tabs in header | Full features |
| **Tablet** (768-1023px) | Adaptive | Touch-friendly |
| **Mobile** (<768px) | 5 tabs bottom nav | Optimized UI |

### Mobile Navigation Tabs
- 📥 Inbox → Tasks
- 🎯 Focus → Today's Focus
- 🔖 Saved → Bookmarks
- 👥 People → Contacts
- ⚙️ Settings

---

## 🧠 AI Models Used

- **llama3-8b-8192** — Fast categorization (~200ms)
- **llama3-70b-8192** — Smart focus selection (~1s)

---

## 🔒 Privacy & Security

- All data stored locally in `./database/lifepilot.db`
- PII (emails, phones, names) stripped before AI calls
- No data sent to cloud except anonymized text to Groq
- CORS configured for allowed origins

### Production Security Checklist
- [ ] Update CORS origins for production domain
- [ ] Enable HTTPS in production
- [ ] Set up rate limiting
- [ ] Secure API keys in environment variables

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Build Time | 3.80s |
| Bundle Size | 305.71 kB (82.87 kB gzipped) |
| CSS Size | 46.56 kB (8.59 kB gzipped) |
| Startup Time | <2s |
| Health Check | <50ms |

---

## 🧪 Verification

### Health Checks
```bash
# Backend health
curl http://localhost:8000/api/health

# Run production tests
cd backend
python verify_production.py
```

### Post-Deployment
- [ ] Verify health endpoint
- [ ] Test all navigation tabs
- [ ] Check responsive layout on real devices
- [ ] Monitor error logs

---

## ⚠️ Known Limitations

1. **Push Notifications**: Requires VAPID keys to be configured
2. **Calendar Integration**: Requires OAuth setup for Google Calendar
3. **Voice Input**: Requires Whisper API configuration
4. **Service Worker**: Currently disabled (can be enabled for offline support)

---

## 📝 License

MIT

---

**Version:** 2.4.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-01-16
