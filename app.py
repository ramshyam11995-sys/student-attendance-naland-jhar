"""
Student ID Verification System — Flask Backend v2
New: admin login/logout, session-based auth, password protection,
     all admin routes require @admin_required decorator.
"""

import os
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ── Optional Twilio ─────────────────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# ── Config (override via environment variables in production) ────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH    = os.path.join(BASE_DIR, "applications.db")

ALLOWED_EXTENSIONS   = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
MAX_CONTENT_LENGTH   = 10 * 1024 * 1024   # 10 MB

# ⚠️  Set these as environment variables before going live!
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")
SECRET_KEY     = os.getenv("SECRET_KEY",     secrets.token_hex(32))

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID",   "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN",     "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM",  "whatsapp:+14155238886")

# ── App ──────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"]         = MAX_CONTENT_LENGTH
app.config["SESSION_COOKIE_HTTPONLY"]    = True
app.config["SESSION_COOKIE_SAMESITE"]   = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

# In production, change origins to your actual domain: ["https://yourdomain.com"]
CORS(app, supports_credentials=True, origins="*")

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = SECRET_KEY.encode()
    return hmac.new(salt, password.encode(), hashlib.sha256).hexdigest()

def check_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(plain), hashed)

ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)


# ── Auth decorator ───────────────────────────────────────────────────────────

def admin_required(f):
    """Reject any request that doesn't have an active admin session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"success": False, "error": "Unauthorised. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated


# ── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                whatsapp_number TEXT NOT NULL,
                id_card_image   TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                created_at      TEXT NOT NULL
            )
        """)
        conn.commit()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── WhatsApp ─────────────────────────────────────────────────────────────────

def send_whatsapp(to_number: str, message: str) -> dict:
    if not TWILIO_AVAILABLE:
        return {"success": False, "error": "twilio not installed"}
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {"success": False, "error": "Twilio credentials not configured"}
    clean = to_number.strip().replace(" ", "").replace("-", "")
    if not clean.startswith("+"):
        clean = "+91" + clean.lstrip("0")
    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{clean}", body=message)
        return {"success": True, "sid": msg.sid}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES  (Students)
# ════════════════════════════════════════════════════════════════════════════
from flask import render_template

@app.route("/")
def home():
    return render_template("index.html")
@app.route("/")
def index():
    from flask import render_template
    return render_template("index.html")
@app.route("/submit", methods=["POST"])
def submit():
    name            = request.form.get("name", "").strip()
    whatsapp_number = request.form.get("whatsapp_number", "").strip()
    errors = []
    if not name:
        errors.append("Full name is required.")
    if not whatsapp_number or len(whatsapp_number.replace(" ", "")) < 7:
        errors.append("A valid WhatsApp number is required.")
    if "id_card" not in request.files or request.files["id_card"].filename == "":
        errors.append("ID card image is required.")
    elif not allowed_file(request.files["id_card"].filename):
        errors.append("Unsupported file type.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    file        = request.files["id_card"]
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stored_name = f"{ts}_{secure_filename(file.filename)}"
    file.save(os.path.join(UPLOAD_DIR, stored_name))

    created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO applications (name, whatsapp_number, id_card_image, status, created_at)"
            " VALUES (?, ?, ?, 'pending', ?)",
            (name, whatsapp_number, stored_name, created_at),
        )
        conn.commit()

    return jsonify({
        "success": True,
        "message": "Application submitted! You will be notified once reviewed.",
        "id": cur.lastrowid,
    }), 201


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()}), 200


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN AUTH ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["POST"])
def admin_login():
    """POST /admin/login  { username, password }"""
    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if username == ADMIN_USERNAME and check_password(password, ADMIN_PASSWORD_HASH):
        session.permanent = True
        session["admin_logged_in"] = True
        session["admin_username"]  = username
        return jsonify({"success": True, "message": "Logged in."}), 200

    return jsonify({"success": False, "error": "Invalid username or password."}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return jsonify({"success": True}), 200


@app.route("/admin/me")
def admin_me():
    if session.get("admin_logged_in"):
        return jsonify({"authenticated": True, "username": session.get("admin_username")}), 200
    return jsonify({"authenticated": False}), 200


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN PROTECTED ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/applications", methods=["GET"])
@admin_required
def get_applications():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        ).fetchall()
    return jsonify({"success": True, "applications": [dict(r) for r in rows]}), 200


@app.route("/approve/<int:app_id>", methods=["POST"])
@admin_required
def approve(app_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
        if not row:
            return jsonify({"success": False, "error": "Not found."}), 404
        conn.execute("UPDATE applications SET status='approved' WHERE id=?", (app_id,))
        conn.commit()
    msg = f"Hello {row['name']}, your student ID verification has been approved. Welcome! 🎓"
    wa  = send_whatsapp(row["whatsapp_number"], msg)
    return jsonify({"success": True, "message": f"#{app_id} approved.", "whatsapp": wa}), 200


@app.route("/reject/<int:app_id>", methods=["POST"])
@admin_required
def reject(app_id):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applications WHERE id=?", (app_id,)).fetchone()
        if not row:
            return jsonify({"success": False, "error": "Not found."}), 404
        conn.execute("UPDATE applications SET status='rejected' WHERE id=?", (app_id,))
        conn.commit()
    return jsonify({"success": True, "message": f"#{app_id} rejected."}), 200


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "_main_":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"🔐  Admin username={ADMIN_USERNAME} password={ADMIN_PASSWORD}")
    print(f"🚀  Running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
