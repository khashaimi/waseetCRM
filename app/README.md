# Waseet CRM (وسيط) — Quick Start Guide

## Run Locally (Now)

**Requirements:** Python 3.8+ (already installed on most computers)

```bash
cd waseet-crm
python server.py
```

Open http://localhost:8000 → redirects to login → create your first account.

---

## First Time Setup

1. Open a terminal (Command Prompt on Windows, Terminal on Mac)
2. Navigate to this folder: `cd path/to/waseet-crm`
3. Run: `python server.py`
4. Open browser: http://localhost:8000
5. Click "إنشاء حساب" (Create Account)
6. Enter your agency name, your name, email, and password
7. You get 30 days free trial automatically

---

## File Structure

```
waseet-crm/
├── server.py        ← Main server (run this)
├── database.py      ← Database logic
├── waseet.db        ← Your data (auto-created)
├── public/
│   ├── index.html   ← Root redirect
│   ├── login.html   ← Login / Register page
│   ├── app.html     ← The full CRM application
│   └── lead.html    ← Public lead capture form
```

---

## Deploy to Railway (Free Hosting)

Railway gives you a free public URL so clients can access Waseet CRM from anywhere.

### Step 1: Push to GitHub
1. Install Git: git-scm.com
2. Create a free GitHub account: github.com
3. Create a new repository called "waseet-crm"
4. Upload all files from this folder to the repository

### Step 2: Deploy on Railway
1. Go to railway.app and sign up (free)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your "waseet-crm" repository
4. Railway will detect Python automatically

### Step 3: Set Environment Variables in Railway
In your Railway project → Settings → Environment Variables:
```
JWT_SECRET = [a long random string, e.g. "waseet-2026-my-secret-key-xyz"]
PORT       = 8000
DB_PATH    = /data/waseet.db
```

### Step 4: Add Persistent Storage
In Railway → your project → Add Service → Volume
- Mount path: `/data`

This ensures your database survives restarts.

### Step 5: Get Your URL
Railway gives you a URL like: `https://waseet-crm-production.up.railway.app`
Share this with your clients and agents.

**Free Railway plan:** 500 hours/month (enough for testing, upgrade when you have paying customers)

---

## Deploy to Render (Alternative — also free)

1. Sign up at render.com
2. New → Web Service → Connect GitHub repo
3. Build Command: (leave empty)
4. Start Command: `python server.py`
5. Environment variables: `JWT_SECRET`, `PORT=8000`
6. Add a Disk: mount path `/data`, then set `DB_PATH=/data/waseet.db`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `JWT_SECRET` | `waseet-secret-...` | **Change this in production!** |
| `DB_PATH` | `waseet.db` (next to server.py) | SQLite database file path |

---

## Lead Capture Form

Share this URL with potential clients:
```
https://your-domain.com/lead.html
```

When they submit the form, they appear as a new contact in your CRM immediately.

---

## WhatsApp Number Update

Replace `966541482208` with your real WhatsApp number in:
- `public/app.html` (settings page support link)
- `public/lead.html` (not present, but add if needed)
- `landing/index.html` (the marketing landing page)

Example: if your number is 0501234567 → use `966501234567`

---

## Custom Domain

Once deployed on Railway or Render, you can add a custom domain (e.g. `waseetcrm.sa`):

1. Buy domain at GoDaddy or Namecheap (~50 SAR/year for .com)
2. In Railway: Settings → Domains → Add Custom Domain
3. Update your DNS records as instructed

---

## Backup Your Data

Your SQLite database (`waseet.db`) is a single file — back it up regularly:
```bash
cp waseet.db waseet_backup_$(date +%Y%m%d).db
```

---

## Need Help?

- WhatsApp: [your number]
- Email: support@waseetcrm.com
