"""
Waseet CRM — Python HTTP Server
Run: python server.py
API: http://localhost:8000/api/...
App: http://localhost:8000/
"""
import json, os, sys, re, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import jwt
from datetime import datetime, timedelta, timezone
import database as db

SECRET = os.environ.get("JWT_SECRET", "waseet-secret-change-in-production-2026")
PORT   = int(os.environ.get("PORT", 8000))
PUBLIC = os.path.join(os.path.dirname(__file__), "public")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
    ".ico":  "image/x-icon",
    ".json": "application/json",
}

# ── JWT helpers ───────────────────────────────────────────────────────────────

def make_token(user_id, agency_id, role):
    payload = {
        "sub": user_id,
        "agency": agency_id,
        "role": role,
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def decode_token(token):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return None

def get_token_from_header(handler):
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return decode_token(auth[7:])
    return None

# ── Request handler ───────────────────────────────────────────────────────────

class CRMHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Suppress default access log

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg, status=400):
        self.send_json({"error": msg}, status)

    def require_auth(self):
        claims = get_token_from_header(self)
        if not claims:
            self.send_error_json("غير مصرح", 401)
            return None
        return claims

    def require_admin(self):
        claims = self.require_auth()
        if claims and claims.get("role") != "admin":
            self.send_error_json("مسؤول فقط", 403)
            return None
        return claims

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.end_headers()

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_DELETE(self):
        self.route("DELETE")

    def route(self, method):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        try:
            # ── Static files ──────────────────────────────────────────────────
            if not path.startswith("/api"):
                self.serve_static(path)
                return

            # ── API routes ────────────────────────────────────────────────────
            # AUTH
            if method == "POST" and path == "/api/auth/register":
                self.handle_register()
            elif method == "POST" and path == "/api/auth/login":
                self.handle_login()
            elif method == "GET" and path == "/api/auth/me":
                self.handle_me()

            # DASHBOARD
            elif method == "GET" and path == "/api/dashboard":
                self.handle_dashboard()

            # CONTACTS
            elif method == "GET" and path == "/api/contacts":
                self.handle_list_contacts(qs)
            elif method == "POST" and path == "/api/contacts":
                self.handle_create_contact()
            elif method == "GET" and re.match(r"^/api/contacts/\d+$", path):
                self.handle_get_contact(int(path.split("/")[-1]))
            elif method == "PUT" and re.match(r"^/api/contacts/\d+$", path):
                self.handle_update_contact(int(path.split("/")[-1]))
            elif method == "DELETE" and re.match(r"^/api/contacts/\d+$", path):
                self.handle_delete_contact(int(path.split("/")[-1]))

            # DEALS
            elif method == "GET" and path == "/api/deals":
                self.handle_list_deals(qs)
            elif method == "POST" and path == "/api/deals":
                self.handle_create_deal()
            elif method == "PUT" and re.match(r"^/api/deals/\d+$", path):
                self.handle_update_deal(int(path.split("/")[-1]))
            elif method == "DELETE" and re.match(r"^/api/deals/\d+$", path):
                self.handle_delete_deal(int(path.split("/")[-1]))

            # PROPERTIES
            elif method == "GET" and path == "/api/properties":
                self.handle_list_properties(qs)
            elif method == "POST" and path == "/api/properties":
                self.handle_create_property()
            elif method == "PUT" and re.match(r"^/api/properties/\d+$", path):
                self.handle_update_property(int(path.split("/")[-1]))
            elif method == "DELETE" and re.match(r"^/api/properties/\d+$", path):
                self.handle_delete_property(int(path.split("/")[-1]))

            # FOLLOW-UPS
            elif method == "GET" and path == "/api/followups":
                self.handle_list_followups(qs)
            elif method == "POST" and path == "/api/followups":
                self.handle_create_followup()
            elif method == "PUT" and re.match(r"^/api/followups/\d+/done$", path):
                self.handle_done_followup(int(path.split("/")[-2]))
            elif method == "DELETE" and re.match(r"^/api/followups/\d+$", path):
                self.handle_delete_followup(int(path.split("/")[-1]))

            # TEAM
            elif method == "GET" and path == "/api/team":
                self.handle_list_team()
            elif method == "POST" and path == "/api/team":
                self.handle_invite_agent()
            elif method == "PUT" and re.match(r"^/api/team/\d+/toggle$", path):
                self.handle_toggle_agent(int(path.split("/")[-2]))

            else:
                self.send_error_json("مسار غير موجود", 404)

        except Exception as e:
            traceback.print_exc()
            self.send_error_json(f"خطأ في الخادم: {str(e)}", 500)

    # ── Static file serving ───────────────────────────────────────────────────

    def serve_static(self, path):
        if path == "/" or not path.endswith((".html",".css",".js",".svg",".png",".ico")):
            path = "/index.html"
        filepath = os.path.join(PUBLIC, path.lstrip("/"))
        if not os.path.isfile(filepath):
            # SPA fallback → app.html for /app routes
            filepath = os.path.join(PUBLIC, "index.html")
        ext = os.path.splitext(filepath)[1]
        mime = MIME.get(ext, "application/octet-stream")
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    # ── AUTH handlers ─────────────────────────────────────────────────────────

    def handle_register(self):
        data = self.read_json()
        if not all([data.get("agency_name"), data.get("name"), data.get("email"), data.get("password")]):
            return self.send_error_json("جميع الحقول مطلوبة")
        if db.get_user_by_email(data["email"]):
            return self.send_error_json("البريد الإلكتروني مسجل مسبقاً")
        result = db.create_agency_and_user(
            data["agency_name"], data["name"], data["email"],
            data["password"], data.get("phone","")
        )
        token = make_token(result["user_id"], result["agency_id"], "admin")
        self.send_json({"token": token, "message": "تم إنشاء الحساب بنجاح"})

    def handle_login(self):
        data = self.read_json()
        user = db.get_user_by_email(data.get("email",""))
        if not user or not db.check_password(user["password_hash"], data.get("password","")):
            return self.send_error_json("البريد أو كلمة المرور غير صحيحة", 401)
        token = make_token(user["id"], user["agency_id"], user["role"])
        user.pop("password_hash", None)
        self.send_json({"token": token, "user": user})

    def handle_me(self):
        claims = self.require_auth()
        if not claims:
            return
        conn = db.get_db()
        try:
            row = conn.execute("SELECT * FROM users WHERE id=?", (claims["sub"],)).fetchone()
            if not row:
                return self.send_error_json("المستخدم غير موجود", 404)
            user = dict(row)
            user.pop("password_hash", None)
            agency = db.get_agency(claims["agency"])
            self.send_json({"user": user, "agency": agency})
        finally:
            conn.close()

    # ── DASHBOARD ─────────────────────────────────────────────────────────────

    def handle_dashboard(self):
        claims = self.require_auth()
        if not claims:
            return
        stats = db.get_dashboard_stats(claims["agency"])
        # Recent contacts
        contacts, _ = db.list_contacts(claims["agency"], limit=5)
        # Today's follow-ups
        followups = db.list_followups(claims["agency"])[:5]
        self.send_json({"stats": stats, "recent_contacts": contacts, "followups_today": followups})

    # ── CONTACTS ─────────────────────────────────────────────────────────────

    def handle_list_contacts(self, qs):
        claims = self.require_auth()
        if not claims:
            return
        rows, total = db.list_contacts(
            claims["agency"],
            search=qs.get("search",[""])[0],
            status=qs.get("status",[""])[0],
            limit=int(qs.get("limit",[50])[0]),
            offset=int(qs.get("offset",[0])[0])
        )
        self.send_json({"contacts": rows, "total": total})

    def handle_get_contact(self, contact_id):
        claims = self.require_auth()
        if not claims:
            return
        contact = db.get_contact(contact_id, claims["agency"])
        if not contact:
            return self.send_error_json("العميل غير موجود", 404)
        # Get related deals and follow-ups
        deals = db.list_deals(claims["agency"])
        contact_deals = [d for d in deals if d.get("contact_id") == contact_id]
        followups = db.list_followups(claims["agency"])
        contact_followups = [f for f in followups if f.get("contact_id") == contact_id]
        self.send_json({"contact": contact, "deals": contact_deals, "followups": contact_followups})

    def handle_create_contact(self):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        if not data.get("name"):
            return self.send_error_json("الاسم مطلوب")
        if not data.get("assigned_to"):
            data["assigned_to"] = claims["sub"]
        cid = db.create_contact(claims["agency"], data)
        self.send_json({"id": cid, "message": "تم إضافة العميل"}, 201)

    def handle_update_contact(self, contact_id):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        db.update_contact(contact_id, claims["agency"], data)
        self.send_json({"message": "تم التحديث"})

    def handle_delete_contact(self, contact_id):
        claims = self.require_auth()
        if not claims:
            return
        db.delete_contact(contact_id, claims["agency"])
        self.send_json({"message": "تم الحذف"})

    # ── DEALS ─────────────────────────────────────────────────────────────────

    def handle_list_deals(self, qs):
        claims = self.require_auth()
        if not claims:
            return
        deals = db.list_deals(claims["agency"], stage=qs.get("stage",[""])[0])
        self.send_json({"deals": deals})

    def handle_create_deal(self):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        if not data.get("title"):
            return self.send_error_json("العنوان مطلوب")
        if not data.get("assigned_to"):
            data["assigned_to"] = claims["sub"]
        did = db.create_deal(claims["agency"], data)
        self.send_json({"id": did, "message": "تم إضافة الصفقة"}, 201)

    def handle_update_deal(self, deal_id):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        db.update_deal(deal_id, claims["agency"], data)
        self.send_json({"message": "تم التحديث"})

    def handle_delete_deal(self, deal_id):
        claims = self.require_auth()
        if not claims:
            return
        db.delete_deal(deal_id, claims["agency"])
        self.send_json({"message": "تم الحذف"})

    # ── PROPERTIES ────────────────────────────────────────────────────────────

    def handle_list_properties(self, qs):
        claims = self.require_auth()
        if not claims:
            return
        props = db.list_properties(
            claims["agency"],
            search=qs.get("search",[""])[0],
            prop_type=qs.get("type",[""])[0],
            status=qs.get("status",[""])[0]
        )
        self.send_json({"properties": props})

    def handle_create_property(self):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        if not data.get("title"):
            return self.send_error_json("العنوان مطلوب")
        data["listed_by"] = claims["sub"]
        pid = db.create_property(claims["agency"], data)
        self.send_json({"id": pid, "message": "تم إضافة العقار"}, 201)

    def handle_update_property(self, prop_id):
        claims = self.require_auth()
        if not claims:
            return
        db.update_property(prop_id, claims["agency"], self.read_json())
        self.send_json({"message": "تم التحديث"})

    def handle_delete_property(self, prop_id):
        claims = self.require_auth()
        if not claims:
            return
        db.delete_property(prop_id, claims["agency"])
        self.send_json({"message": "تم الحذف"})

    # ── FOLLOW-UPS ────────────────────────────────────────────────────────────

    def handle_list_followups(self, qs):
        claims = self.require_auth()
        if not claims:
            return
        done = qs.get("done",["0"])[0] == "1"
        items = db.list_followups(claims["agency"], done=done)
        self.send_json({"followups": items})

    def handle_create_followup(self):
        claims = self.require_auth()
        if not claims:
            return
        data = self.read_json()
        if not data.get("due_date"):
            return self.send_error_json("تاريخ التذكير مطلوب")
        if not data.get("assigned_to"):
            data["assigned_to"] = claims["sub"]
        fid = db.create_followup(claims["agency"], data)
        self.send_json({"id": fid, "message": "تم إضافة التذكير"}, 201)

    def handle_done_followup(self, followup_id):
        claims = self.require_auth()
        if not claims:
            return
        db.mark_followup_done(followup_id, claims["agency"])
        self.send_json({"message": "تم الإنجاز"})

    def handle_delete_followup(self, followup_id):
        claims = self.require_auth()
        if not claims:
            return
        db.delete_followup(followup_id, claims["agency"])
        self.send_json({"message": "تم الحذف"})

    # ── TEAM ─────────────────────────────────────────────────────────────────

    def handle_list_team(self):
        claims = self.require_auth()
        if not claims:
            return
        agents = db.list_agents(claims["agency"])
        self.send_json({"agents": agents})

    def handle_invite_agent(self):
        claims = self.require_admin()
        if not claims:
            return
        data = self.read_json()
        if not all([data.get("name"), data.get("email")]):
            return self.send_error_json("الاسم والبريد مطلوبان")
        if db.get_user_by_email(data["email"]):
            return self.send_error_json("البريد مسجل مسبقاً")
        uid = db.invite_agent(claims["agency"], data["name"], data["email"], data.get("phone",""))
        self.send_json({"id": uid, "message": "تمت الدعوة. كلمة المرور الافتراضية: Waseet123"}, 201)

    def handle_toggle_agent(self, user_id):
        claims = self.require_admin()
        if not claims:
            return
        data = self.read_json()
        db.toggle_agent(user_id, claims["agency"], data.get("is_active", 1))
        self.send_json({"message": "تم التحديث"})


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    server = HTTPServer(("0.0.0.0", PORT), CRMHandler)
    print(f"""
╔══════════════════════════════════════════╗
║         وسيط CRM — Waseet CRM            ║
╠══════════════════════════════════════════╣
║  Server:  http://localhost:{PORT}            ║
║  Press Ctrl+C to stop                    ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
