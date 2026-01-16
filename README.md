# LifePilot 2.0 (2026 Edition)

LifePilot is a comprehensive "Personal Life OS" designed to help you manage tasks, energy, focus, relationships, and decisions with the help of AI agents. It uses a modern tech stack and is designed for both local use and cloud deployment.

## 🌟 Key Features

*   **Task Management**: Smart inbox, recurring tasks, energy-based planning.
*   **AI Agent**: Built-in AI assistant ("Antigravity") powered by Groq (Llama 3, Mixtral) for planning, advice, and automation.
*   **Voice Interface**: Speech-to-text inputs for quick capture.
*   **Personal CRM**: Track relationships, last contact dates, and interaction history.
*   **Energy & Focus Logger**: Track your biorhythms to optimize your schedule.
*   **Decision Journal**: Structured framework for making and reviewing life decisions.
*   **PWA Support**: Installable on mobile devices with offline capabilities and push notifications.
*   **Calendar Integration**: 2-way sync with Google Calendar.

## 🏗️ Architecture

The project is split into two separate applications:

*   **Backend**: Python **FastAPI** application.
    *   REST API, Background Workers, AI Integration.
    *   Database: **SQLite** (Local) or **Turso/libSQL** (Production).
    *   Hosting: **Koyeb** (Recommended Free Tier).
*   **Frontend**: **React** application built with **Vite**.
    *   TailwindCSS for styling.
    *   PWA credentials.
    *   Hosting: **Cloudflare Pages** (Recommended Free Tier).

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites
*   Python 3.11+
*   Node.js 18+ (and npm)
*   Git

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (from console.groq.com)

# Start Server
python -m uvicorn main:app --reload
```
*Backend runs on: `http://localhost:8000`*
*API Docs: `http://localhost:8000/docs`*

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Dev Server
npm run dev
```
*Frontend runs on: `http://localhost:5173`*

---

## ☁️ Deployment Guide (Free Tier)

This stack is optimized for $0/month hosting using **Koyeb** (Backend) and **Cloudflare Pages** (Frontend).

### Phase 1: Database (Turso)
1.  Sign up at [turso.tech](https://turso.tech).
2.  Create a database.
3.  Get the **Database URL** (`libsql://...`) and **Auth Token**.
4.  These will be environment variables for your backend.

### Phase 2: Backend (Koyeb)
1.  Push your code to GitHub.
2.  Sign up at [koyeb.com](https://www.koyeb.com).
3.  Create a new **Web Service** from your GitHub repository.
4.  **Root Directory**: `backend`
5.  **Build Command**: `pip install -r requirements.txt`
6.  **Run Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
7.  **Environment Variables**:
    *   `GROQ_API_KEY`: Your key.
    *   `TURSO_DATABASE_URL`: From Phase 1.
    *   `TURSO_AUTH_TOKEN`: From Phase 1.
    *   `VAPID_...`: See *Push Notifications* section.
    *   `GOOGLE_...`: See *Integrations* section.
    *   `CORS_ORIGINS`: `https://your-frontend.pages.dev` (Add this AFTER deploying frontend).

### Phase 3: Frontend (Cloudflare Pages)
1.  Sign up at [pages.cloudflare.com](https://pages.cloudflare.com).
2.  Create a project -> Connect to GitHub.
3.  **Root Directory**: `frontend`
4.  **Build Command**: `npm run build`
5.  **Output Directory**: `dist`
6.  **Environment Variables**:
    *   `VITE_API_URL`: `https://your-app-name.koyeb.app/api` (URL of your deployed backend).

---

## 🔌 Integrations Configuration

### Push Notifications
1.  Generate keys: `vapid --gen` (install `py-vapid` first).
2.  Add to Backend Env: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL`.
3.  The frontend will automatically use these to subscribe users.

### Google Calendar
1.  Go to Google Cloud Console -> APIs & Services -> Credentials.
2.  Create OAuth 2.0 Web Client.
3.  **Local Redirect URI**: `http://localhost:8000/api/auth/google/callback`
4.  **Production Redirect URI**: `https://your-backend.koyeb.app/api/auth/google/callback`
5.  Add Client ID/Secret to Backend Env: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

---

## 📁 Project Structure

```
lifepilot/
├── backend/             # FastAPI App
│   ├── core/           # Config & Logging
│   ├── database/       # DB connection (SQLite/Turso)
│   ├── routers/        # API Endpoints
│   ├── services/       # Business Logic
│   ├── requirements.txt
│   └── main.py         # Entry point
│
├── frontend/            # React App
│   ├── src/
│   │   ├── api/        # API Client
│   │   ├── components/ # Reusable UI components
│   │   ├── hooks/      # Custom React hooks
│   │   └── pages/      # App screens
│   ├── public/         # Static assets & Service Worker
│   └── vite.config.js
│
└── README.md
