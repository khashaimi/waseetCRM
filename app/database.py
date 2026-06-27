"""
Waseet CRM — Database Layer
SQLite + all table definitions + helper queries
"""
import sqlite3, os, hashlib, secrets
from datetime import datetime, timedelta

def _resolve_db_path():
    candidates = [
        os.environ.get("DB_PATH"),
        "/tmp/waseet.db",
        "/var/tmp/waseet.db",
        os.path.join(os.path.expanduser("~"), "waseet.db"),
    ]
    for path in candidates:
        if not path:
            continue
        try:
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
            # Test write access
            conn = sqlite3.connect(path)
            conn.close()
            print(f"[DB] Using database at: {path}", flush=True)
            return path
        except Exception as e:
            print(f"[DB] Cannot use {path}: {e}", flush=True)
    raise RuntimeError("Cannot find a writable path for the database")

DB_PATH = _resolve_db_path()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS agencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        plan TEXT DEFAULT 'trial',
        trial_ends TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER REFERENCES agencies(id),
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        role TEXT DEFAULT 'agent',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        assigned_to INTEGER REFERENCES users(id),
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        source TEXT DEFAULT 'واتساب',
        status TEXT DEFAULT 'جديد',
        budget_min REAL,
        budget_max REAL,
        property_type TEXT,
        preferred_area TEXT,
        notes TEXT,
        next_followup TEXT,
        last_contact TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        assigned_to INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        property_id INTEGER REFERENCES properties(id),
        title TEXT NOT NULL,
        stage TEXT DEFAULT 'جديد',
        value REAL,
        commission_pct REAL DEFAULT 2.5,
        expected_close TEXT,
        closed_at TEXT,
        is_won INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        listed_by INTEGER REFERENCES users(id),
        title TEXT NOT NULL,
        type TEXT DEFAULT 'شقة',
        price REAL,
        area REAL,
        bedrooms INTEGER,
        bathrooms INTEGER,
        city TEXT,
        neighborhood TEXT,
        description TEXT,
        status TEXT DEFAULT 'متاح',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        assigned_to INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        deal_id INTEGER REFERENCES deals(id),
        note TEXT,
        due_date TEXT NOT NULL,
        is_done INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        user_id INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        deal_id INTEGER REFERENCES deals(id),
        type TEXT,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()
    print(f"✓ Database ready at {DB_PATH}")

# ── AUTH ──────────────────────────────────────────────────────────────────────

def create_agency_and_user(agency_name, name, email, password, phone=""):
    conn = get_db()
    try:
        trial_ends = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        c = conn.cursor()
        c.execute("INSERT INTO agencies (name, plan, trial_ends) VALUES (?,?,?)",
                  (agency_name, "trial", trial_ends))
        agency_id = c.lastrowid
        _salt = secrets.token_hex(16)
        pw_hash = "pbkdf2:" + _salt + ":" + hashlib.pbkdf2_hmac("sha256", password.encode(), _salt.encode(), 260000).hex()
        c.execute("""INSERT INTO users (agency_id, name, email, password_hash, phone, role)
                     VALUES (?,?,?,?,?,?)""",
                  (agency_id, name, email, pw_hash, phone, "admin"))
        user_id = c.lastrowid
        conn.commit()
        return {"agency_id": agency_id, "user_id": user_id}
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email=? AND is_active=1", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def check_password(stored_hash, password):
    try:
        _, _salt, _hx = stored_hash.split(":")
        return hashlib.pbkdf2_hmac("sha256", password.encode(), _salt.encode(), 260000).hex() == _hx
    except Exception:
        return False

# ── STATS ─────────────────────────────────────────────────────────────────────

def get_dashboard_stats(agency_id):
    conn = get_db()
    try:
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        stats = {
            "contacts": conn.execute("SELECT COUNT(*) FROM contacts WHERE agency_id=?", (agency_id,)).fetchone()[0],
            "open_deals": conn.execute("SELECT COUNT(*) FROM deals WHERE agency_id=? AND stage NOT IN ('مغلقة','ملغية')", (agency_id,)).fetchone()[0],
            "closed_this_month": conn.execute("SELECT COUNT(*) FROM deals WHERE agency_id=? AND is_won=1 AND closed_at>=?", (agency_id, month_start)).fetchone()[0],
            "revenue_this_month": conn.execute("SELECT COALESCE(SUM(value*(commission_pct/100)),0) FROM deals WHERE agency_id=? AND is_won=1 AND closed_at>=?", (agency_id, month_start)).fetchone()[0],
            "followups_today": conn.execute("SELECT COUNT(*) FROM followups WHERE agency_id=? AND is_done=0 AND date(due_date)<=date('now')", (agency_id,)).fetchone()[0],
            "agents": conn.execute("SELECT COUNT(*) FROM users WHERE agency_id=? AND is_active=1", (agency_id,)).fetchone()[0],
        }
        return stats
    finally:
        conn.close()

# ── CONTACTS ─────────────────────────────────────────────────────────────────

def list_contacts(agency_id, search="", status="", assigned_to=None, limit=100, offset=0):
    conn = get_db()
    try:
        q = "SELECT c.*, u.name as agent_name FROM contacts c LEFT JOIN users u ON c.assigned_to=u.id WHERE c.agency_id=?"
        params = [agency_id]
        if search:
            q += " AND (c.name LIKE ? OR c.phone LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if status:
            q += " AND c.status=?"
            params.append(status)
        if assigned_to:
            q += " AND c.assigned_to=?"
            params.append(assigned_to)
        q += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(q, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM contacts WHERE agency_id=?", (agency_id,)).fetchone()[0]
        return [dict(r) for r in rows], total
    finally:
        conn.close()

def get_contact(contact_id, agency_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT c.*, u.name as agent_name FROM contacts c LEFT JOIN users u ON c.assigned_to=u.id WHERE c.id=? AND c.agency_id=?", (contact_id, agency_id)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_contact(agency_id, data):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO contacts (agency_id,assigned_to,name,phone,email,source,status,
                     budget_min,budget_max,property_type,preferred_area,notes,next_followup)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (agency_id, data.get("assigned_to"), data.get("name"), data.get("phone"),
                   data.get("email"), data.get("source","واتساب"), data.get("status","جديد"),
                   data.get("budget_min"), data.get("budget_max"), data.get("property_type"),
                   data.get("preferred_area"), data.get("notes"), data.get("next_followup")))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def update_contact(contact_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["name","phone","email","source","status","budget_min","budget_max",
                  "property_type","preferred_area","notes","next_followup","assigned_to","last_contact"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return False
        conn.execute(f"UPDATE contacts SET {sets} WHERE id=? AND agency_id=?", vals + [contact_id, agency_id])
        conn.commit()
        return True
    finally:
        conn.close()

def delete_contact(contact_id, agency_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM contacts WHERE id=? AND agency_id=?", (contact_id, agency_id))
        conn.commit()
    finally:
        conn.close()

# ── DEALS ─────────────────────────────────────────────────────────────────────

def list_deals(agency_id, stage="", assigned_to=None):
    conn = get_db()
    try:
        q = """SELECT d.*, c.name as contact_name, c.phone as contact_phone,
               u.name as agent_name, p.title as property_title
               FROM deals d
               LEFT JOIN contacts c ON d.contact_id=c.id
               LEFT JOIN users u ON d.assigned_to=u.id
               LEFT JOIN properties p ON d.property_id=p.id
               WHERE d.agency_id=?"""
        params = [agency_id]
        if stage:
            q += " AND d.stage=?"
            params.append(stage)
        if assigned_to:
            q += " AND d.assigned_to=?"
            params.append(assigned_to)
        q += " ORDER BY d.created_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def create_deal(agency_id, data):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO deals (agency_id,assigned_to,contact_id,property_id,title,stage,
                     value,commission_pct,expected_close,notes)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (agency_id, data.get("assigned_to"), data.get("contact_id"),
                   data.get("property_id"), data.get("title"), data.get("stage","جديد"),
                   data.get("value"), data.get("commission_pct",2.5),
                   data.get("expected_close"), data.get("notes")))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def update_deal(deal_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["title","stage","value","commission_pct","expected_close","notes",
                  "assigned_to","contact_id","property_id","is_won","closed_at"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return False
        # Auto-set closed_at when won
        if data.get("is_won") and "closed_at" not in data:
            sets += ", closed_at=datetime('now')"
        conn.execute(f"UPDATE deals SET {sets} WHERE id=? AND agency_id=?", vals + [deal_id, agency_id])
        conn.commit()
        return True
    finally:
        conn.close()

def delete_deal(deal_id, agency_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM deals WHERE id=? AND agency_id=?", (deal_id, agency_id))
        conn.commit()
    finally:
        conn.close()

# ── PROPERTIES ────────────────────────────────────────────────────────────────

def list_properties(agency_id, search="", prop_type="", status=""):
    conn = get_db()
    try:
        q = "SELECT p.*, u.name as agent_name FROM properties p LEFT JOIN users u ON p.listed_by=u.id WHERE p.agency_id=?"
        params = [agency_id]
        if search:
            q += " AND (p.title LIKE ? OR p.neighborhood LIKE ? OR p.city LIKE ?)"
            params += [f"%{search}%"]*3
        if prop_type:
            q += " AND p.type=?"
            params.append(prop_type)
        if status:
            q += " AND p.status=?"
            params.append(status)
        q += " ORDER BY p.created_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def create_property(agency_id, data):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO properties (agency_id,listed_by,title,type,price,area,
                     bedrooms,bathrooms,city,neighborhood,description,status)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (agency_id, data.get("listed_by"), data.get("title"), data.get("type","شقة"),
                   data.get("price"), data.get("area"), data.get("bedrooms"),
                   data.get("bathrooms"), data.get("city"), data.get("neighborhood"),
                   data.get("description"), data.get("status","متاح")))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def update_property(prop_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["title","type","price","area","bedrooms","bathrooms","city",
                  "neighborhood","description","status","listed_by"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if not sets:
            return False
        conn.execute(f"UPDATE properties SET {sets} WHERE id=? AND agency_id=?", vals + [prop_id, agency_id])
        conn.commit()
        return True
    finally:
        conn.close()

def delete_property(prop_id, agency_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM properties WHERE id=? AND agency_id=?", (prop_id, agency_id))
        conn.commit()
    finally:
        conn.close()

# ── FOLLOW-UPS ────────────────────────────────────────────────────────────────

def list_followups(agency_id, done=False, assigned_to=None):
    conn = get_db()
    try:
        q = """SELECT f.*, c.name as contact_name, c.phone as contact_phone,
               u.name as agent_name
               FROM followups f
               LEFT JOIN contacts c ON f.contact_id=c.id
               LEFT JOIN users u ON f.assigned_to=u.id
               WHERE f.agency_id=? AND f.is_done=?"""
        params = [agency_id, 1 if done else 0]
        if assigned_to:
            q += " AND f.assigned_to=?"
            params.append(assigned_to)
        q += " ORDER BY f.due_date ASC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def create_followup(agency_id, data):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO followups (agency_id,assigned_to,contact_id,deal_id,note,due_date)
                     VALUES (?,?,?,?,?,?)""",
                  (agency_id, data.get("assigned_to"), data.get("contact_id"),
                   data.get("deal_id"), data.get("note"), data.get("due_date")))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def mark_followup_done(followup_id, agency_id):
    conn = get_db()
    try:
        conn.execute("UPDATE followups SET is_done=1 WHERE id=? AND agency_id=?", (followup_id, agency_id))
        conn.commit()
    finally:
        conn.close()

def delete_followup(followup_id, agency_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM followups WHERE id=? AND agency_id=?", (followup_id, agency_id))
        conn.commit()
    finally:
        conn.close()

# ── TEAM ─────────────────────────────────────────────────────────────────────

def list_agents(agency_id):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT u.*,
                (SELECT COUNT(*) FROM contacts WHERE assigned_to=u.id) as contact_count,
                (SELECT COUNT(*) FROM deals WHERE assigned_to=u.id AND stage NOT IN ('مغلقة','ملغية')) as open_deals,
                (SELECT COUNT(*) FROM deals WHERE assigned_to=u.id AND is_won=1 AND strftime('%Y-%m',closed_at)=strftime('%Y-%m','now')) as closed_month
            FROM users u WHERE u.agency_id=? AND u.is_active=1 ORDER BY u.created_at ASC""",
            (agency_id,)).fetchall()
        agents = [dict(r) for r in rows]
        for a in agents:
            a.pop("password_hash", None)
        return agents
    finally:
        conn.close()

def invite_agent(agency_id, name, email, phone=""):
    conn = get_db()
    try:
        # Default password = phone or "Waseet123"
        default_pw = phone if phone else "Waseet123"
        _salt = secrets.token_hex(16)
        pw_hash = "pbkdf2:" + _salt + ":" + hashlib.pbkdf2_hmac("sha256", default_pw.encode(), _salt.encode(), 260000).hex()
        c = conn.cursor()
        c.execute("""INSERT INTO users (agency_id,name,email,password_hash,phone,role)
                     VALUES (?,?,?,?,?,?)""",
                  (agency_id, name, email, pw_hash, phone, "agent"))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def toggle_agent(user_id, agency_id, is_active):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET is_active=? WHERE id=? AND agency_id=?", (is_active, user_id, agency_id))
        conn.commit()
    finally:
        conn.close()

def update_profile(user_id, data):
    """Update user's own name/phone and optionally their password."""
    conn = get_db()
    try:
        # Update name/phone
        if data.get("name"):
            conn.execute("UPDATE users SET name=?, phone=? WHERE id=?",
                         (data["name"], data.get("phone",""), user_id))
            conn.commit()
        # Change password if provided
        if data.get("old_password") and data.get("new_password"):
            row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                return False, "المستخدم غير موجود"
            if not check_password(row["password_hash"], data["old_password"]):
                return False, "كلمة المرور الحالية غير صحيحة"
            _salt = secrets.token_hex(16)
            pw_hash = "pbkdf2:" + _salt + ":" + hashlib.pbkdf2_hmac(
                "sha256", data["new_password"].encode(), _salt.encode(), 260000).hex()
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (pw_hash, user_id))
            conn.commit()
        return True, "تم الحفظ"
    finally:
        conn.close()

def get_agency(agency_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM agencies WHERE id=?", (agency_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
