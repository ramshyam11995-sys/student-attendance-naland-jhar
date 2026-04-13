# 🎓 Student ID Verification System v2

Full-stack system with **separate admin login page**, **password protection**, **session auth**, and **deployment guide**.

---

## 📁 Project Structure

```
student-id-system-v2/
├── backend/
│   ├── app.py              ← Flask API + SQLite + session auth
│   ├── requirements.txt
│   ├── Procfile            ← For Render / Railway / Heroku
│   └── uploads/            ← Uploaded ID card images (auto-created)
├── frontend/
│   └── index.html          ← Student submission form
├── admin/
│   ├── login.html          ← 🔐 Admin login page (password protected)
│   └── dashboard.html      ← Admin review panel (session guarded)
├── render.yaml             ← One-click Render.com deploy config
└── README.md
```

---

## 🔐 Admin Access

| URL | Purpose |
|-----|---------|
| `admin/login.html` | Admin login (username + password) |
| `admin/dashboard.html` | Protected dashboard (auto-redirects to login if not authenticated) |
| `frontend/index.html` | Public student submission form |

**Default credentials** (change before going live!):
- Username: `admin`
- Password: `Admin@1234`

Change via environment variables:
```bash
export ADMIN_USERNAME="your_username"
export ADMIN_PASSWORD="YourStr0ngP@ssword"
export SECRET_KEY="any_long_random_string"
```

---

## 🚀 Run Locally

```bash
cd backend
pip install -r requirements.txt

# Set credentials (optional — defaults work for testing)
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="Admin@1234"

python app.py
```

Then open in browser:
- Student form: `frontend/index.html`
- Admin login:  `admin/login.html`

---

## 🌐 Going Live — Step by Step

### Option A — Render.com (Recommended, Free)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/student-id-system.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to https://render.com → New → Web Service
   - Connect your GitHub repo
   - Set **Root Directory** to `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
   - Add environment variables (see below)
   - Click **Deploy** → you get a URL like `https://student-id-xyz.onrender.com`

3. **Update API_BASE in your HTML files**
   In `frontend/index.html` and `admin/login.html` and `admin/dashboard.html`:
   ```js
   const API = "https://student-id-xyz.onrender.com";  // ← your Render URL
   ```

4. **Host the frontend** (pick any):
   - **Netlify**: drag-and-drop the `frontend/` and `admin/` folders → free HTTPS URL
   - **GitHub Pages**: push to a `gh-pages` branch
   - **Vercel**: import repo, set output dir to `/`

### Option B — Railway.app

1. Push to GitHub (same as above)
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Set root to `backend/`, add env vars
4. Railway auto-detects `Procfile` and deploys

### Option C — VPS (DigitalOcean / AWS)

```bash
# On the server
sudo apt update && sudo apt install python3-pip nginx certbot -y
pip3 install -r requirements.txt

# Run with gunicorn
gunicorn app:app --bind 127.0.0.1:5000 --workers 4 --daemon

# Set up Nginx reverse proxy (example)
# /etc/nginx/sites-available/student-id
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable HTTPS
sudo certbot --nginx -d yourdomain.com
```

---

## 🔑 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_PASSWORD` | `Admin@1234` | Admin login password |
| `SECRET_KEY` | random | Flask session secret (auto on Render) |
| `TWILIO_ACCOUNT_SID` | `""` | Twilio account SID for WhatsApp |
| `TWILIO_AUTH_TOKEN` | `""` | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | sandbox number | Twilio WhatsApp sender |

---

## 📱 Twilio WhatsApp Setup

1. Sign up at https://www.twilio.com
2. Enable WhatsApp Sandbox in Console → Messaging → Try it out → WhatsApp
3. Copy Account SID and Auth Token to env vars
4. Recipients must join the sandbox first (they send a join code to the sandbox number)
5. For production: apply for a dedicated WhatsApp number in Twilio Console

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/submit` | Public | Submit application |
| GET  | `/applications` | Admin | List all applications |
| POST | `/approve/<id>` | Admin | Approve + WhatsApp |
| POST | `/reject/<id>` | Admin | Reject |
| POST | `/admin/login` | Public | Get session cookie |
| POST | `/admin/logout` | Admin | Clear session |
| GET  | `/admin/me` | Public | Check auth status |
| GET  | `/uploads/<file>` | Public | Serve ID card image |
| GET  | `/health` | Public | Health check |

---

## ⚠️ Production Checklist

- [ ] Change `ADMIN_PASSWORD` to something strong
- [ ] Set a random `SECRET_KEY` (Render does this automatically)
- [ ] Change CORS in `app.py` from `"*"` to your actual frontend domain
- [ ] Use HTTPS on both frontend and backend
- [ ] Set `debug=False` in `app.py` (gunicorn handles this)
- [ ] Consider migrating from SQLite → PostgreSQL for scale
