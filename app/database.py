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
    CREATE TABLE IF NOT EXISTS stock_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        name TEXT NOT NULL,
        unit TEXT DEFAULT 'وحدة',
        quantity REAL DEFAULT 0,
        unit_cost REAL DEFAULT 0,
        reorder_point REAL DEFAULT 0,
        category TEXT,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL,
        item_id INTEGER REFERENCES stock_items(id),
        movement_type TEXT NOT NULL,
        quantity REAL NOT NULL,
        reference TEXT,
        note TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        order_number TEXT,
        supplier TEXT,
        status TEXT DEFAULT 'draft',
        expected_date TEXT,
        delivered_date TEXT,
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS purchase_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER REFERENCES purchase_orders(id),
        item_id INTEGER REFERENCES stock_items(id),
        description TEXT,
        quantity REAL NOT NULL,
        unit_cost REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        quote_number TEXT,
        client_name TEXT,
        client_phone TEXT,
        project_name TEXT,
        status TEXT DEFAULT 'draft',
        valid_until TEXT,
        notes TEXT,
        terms TEXT,
        discount_pct REAL DEFAULT 0,
        tax_pct REAL DEFAULT 15,
        subtotal REAL DEFAULT 0,
        total REAL DEFAULT 0,
        approved_by INTEGER REFERENCES users(id),
        approved_at TEXT,
        converted_at TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS quotation_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_id INTEGER REFERENCES quotations(id),
        description TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'وحدة',
        unit_price REAL NOT NULL,
        total REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS sales_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        quotation_id INTEGER REFERENCES quotations(id),
        order_number TEXT,
        client_name TEXT,
        client_phone TEXT,
        project_name TEXT,
        status TEXT DEFAULT 'active',
        total REAL DEFAULT 0,
        notes TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER NOT NULL REFERENCES agencies(id),
        type TEXT NOT NULL,
        category TEXT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        reference TEXT,
        date TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    );

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
    migrate_db()
    print(f"✓ Database ready at {DB_PATH}")

def migrate_db():
    """Add new columns to existing tables without breaking existing data."""
    conn = get_db()
    try:
        migrations = [
            ("contacts",    "image TEXT"),
            ("properties",  "image TEXT"),
            ("stock_items", "image TEXT"),
            ("contacts",    "company TEXT"),
            ("contacts",    "city TEXT"),
            ("deals",       "image TEXT"),
        ]
        for table, col_def in migrations:
            col_name = col_def.split()[0]
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                conn.commit()
                print(f"[DB] Migrated: {table}.{col_name}", flush=True)
            except Exception:
                pass  # Column already exists
    finally:
        conn.close()

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

def get_contact_detail(contact_id, agency_id):
    """Full contact profile: info + deals + quotations + followups."""
    conn = get_db()
    try:
        row = conn.execute("""SELECT c.*, u.name as agent_name FROM contacts c
                              LEFT JOIN users u ON c.assigned_to=u.id
                              WHERE c.id=? AND c.agency_id=?""", (contact_id, agency_id)).fetchone()
        if not row: return None
        contact = dict(row)
        contact["deals"] = [dict(r) for r in conn.execute(
            "SELECT * FROM deals WHERE contact_id=? AND agency_id=? ORDER BY created_at DESC", (contact_id, agency_id)).fetchall()]
        contact["quotations"] = [dict(r) for r in conn.execute(
            "SELECT * FROM quotations WHERE client_name=? AND agency_id=? ORDER BY created_at DESC", (contact["name"], agency_id)).fetchall()]
        contact["followups"] = [dict(r) for r in conn.execute(
            """SELECT f.*, u.name as agent_name FROM followups f LEFT JOIN users u ON f.assigned_to=u.id
               WHERE f.contact_id=? AND f.agency_id=? ORDER BY f.due_date DESC""", (contact_id, agency_id)).fetchall()]
        return contact
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
                  "property_type","preferred_area","notes","next_followup","assigned_to","last_contact","image","company","city"]
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
                  "neighborhood","description","status","listed_by","image"]
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

def activate_plan(agency_id, plan):
    """Upgrade (or downgrade) an agency's subscription plan."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE agencies SET plan=?, trial_ends=NULL WHERE id=?",
            (plan, agency_id)
        )
        conn.commit()
        print(f"[DB] Agency {agency_id} plan set to '{plan}'", flush=True)
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

# ── STOCK ─────────────────────────────────────────────────────────────────────

def list_stock(agency_id, search=""):
    conn = get_db()
    try:
        q = "SELECT * FROM stock_items WHERE agency_id=? AND is_active=1"
        params = [agency_id]
        if search:
            q += " AND name LIKE ?"
            params.append(f"%{search}%")
        q += " ORDER BY name ASC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]
    finally:
        conn.close()

def create_stock_item(agency_id, data):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO stock_items (agency_id,name,unit,quantity,unit_cost,reorder_point,category,description)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (agency_id, data["name"], data.get("unit","وحدة"),
                   float(data.get("quantity",0)), float(data.get("unit_cost",0)),
                   float(data.get("reorder_point",0)), data.get("category"), data.get("description")))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def update_stock_item(item_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["name","unit","unit_cost","reorder_point","category","description","image"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if sets:
            conn.execute(f"UPDATE stock_items SET {sets} WHERE id=? AND agency_id=?", vals+[item_id,agency_id])
        conn.commit()
    finally:
        conn.close()

def adjust_stock(item_id, agency_id, qty_delta, movement_type="manual", ref="", note="", user_id=None):
    conn = get_db()
    try:
        conn.execute("UPDATE stock_items SET quantity=quantity+? WHERE id=? AND agency_id=?",
                     (qty_delta, item_id, agency_id))
        conn.execute("""INSERT INTO stock_movements (agency_id,item_id,movement_type,quantity,reference,note,created_by)
                        VALUES (?,?,?,?,?,?,?)""",
                     (agency_id, item_id, movement_type, qty_delta, ref, note, user_id))
        conn.commit()
    finally:
        conn.close()

# ── PURCHASE ORDERS ───────────────────────────────────────────────────────────

def _next_seq(conn, table, agency_id, prefix):
    n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE agency_id=?", (agency_id,)).fetchone()[0] + 1
    return f"{prefix}-{datetime.now().year}-{n:04d}"

def list_orders(agency_id, status=""):
    conn = get_db()
    try:
        q = """SELECT po.*, u.name as creator_name,
               (SELECT COALESCE(SUM(quantity*unit_cost),0) FROM purchase_order_items WHERE order_id=po.id) as total
               FROM purchase_orders po LEFT JOIN users u ON po.created_by=u.id
               WHERE po.agency_id=?"""
        params = [agency_id]
        if status:
            q += " AND po.status=?"; params.append(status)
        return [dict(r) for r in conn.execute(q+(" ORDER BY po.created_at DESC"), params).fetchall()]
    finally:
        conn.close()

def get_order(order_id, agency_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM purchase_orders WHERE id=? AND agency_id=?",(order_id,agency_id)).fetchone()
        if not row: return None
        order = dict(row)
        items = conn.execute("""SELECT poi.*, si.name as item_name FROM purchase_order_items poi
                               LEFT JOIN stock_items si ON poi.item_id=si.id WHERE poi.order_id=?""",(order_id,)).fetchall()
        order["items"] = [dict(i) for i in items]
        return order
    finally:
        conn.close()

def create_order(agency_id, data, items, created_by):
    conn = get_db()
    try:
        c = conn.cursor()
        num = _next_seq(conn, "purchase_orders", agency_id, "PO")
        c.execute("""INSERT INTO purchase_orders (agency_id,order_number,supplier,status,expected_date,notes,created_by)
                     VALUES (?,?,?,?,?,?,?)""",
                  (agency_id, num, data.get("supplier"), data.get("status","draft"),
                   data.get("expected_date"), data.get("notes"), created_by))
        oid = c.lastrowid
        for it in items:
            c.execute("INSERT INTO purchase_order_items (order_id,item_id,description,quantity,unit_cost) VALUES (?,?,?,?,?)",
                      (oid, it.get("item_id") or None, it.get("description"),
                       float(it.get("quantity",0)), float(it.get("unit_cost",0))))
        conn.commit()
        return oid
    finally:
        conn.close()

def update_order(order_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["supplier","status","expected_date","notes"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if sets:
            conn.execute(f"UPDATE purchase_orders SET {sets} WHERE id=? AND agency_id=?", vals+[order_id,agency_id])
        conn.commit()
    finally:
        conn.close()

def receive_order(order_id, agency_id, user_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM purchase_orders WHERE id=? AND agency_id=?",(order_id,agency_id)).fetchone()
        if not row: return False, "الطلب غير موجود"
        if dict(row)["status"] == "delivered": return False, "تم استلام هذا الطلب مسبقاً"
        conn.execute("UPDATE purchase_orders SET status='delivered', delivered_date=date('now') WHERE id=? AND agency_id=?",
                     (order_id, agency_id))
        items = conn.execute("SELECT * FROM purchase_order_items WHERE order_id=?",(order_id,)).fetchall()
        for it in items:
            it = dict(it)
            if it.get("item_id"):
                conn.execute("UPDATE stock_items SET quantity=quantity+? WHERE id=? AND agency_id=?",
                             (it["quantity"], it["item_id"], agency_id))
                conn.execute("""INSERT INTO stock_movements (agency_id,item_id,movement_type,quantity,reference,note,created_by)
                                VALUES (?,?,?,?,?,?,?)""",
                             (agency_id, it["item_id"], "in", it["quantity"], f"PO-{order_id}", "استلام طلب شراء", user_id))
        conn.commit()
        return True, "تم الاستلام وإضافة الكميات للمخزون"
    finally:
        conn.close()

# ── QUOTATIONS ────────────────────────────────────────────────────────────────

def _calc_and_save_items(conn, quotation_id, items, discount_pct, tax_pct):
    conn.execute("DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,))
    subtotal = 0
    for it in items:
        qty = float(it.get("quantity",0)); price = float(it.get("unit_price",0)); tot = qty*price
        subtotal += tot
        conn.execute("INSERT INTO quotation_items (quotation_id,description,quantity,unit,unit_price,total) VALUES (?,?,?,?,?,?)",
                     (quotation_id, it.get("description",""), qty, it.get("unit","وحدة"), price, tot))
    discount = subtotal * discount_pct / 100
    after = subtotal - discount
    tax = after * tax_pct / 100
    total = after + tax
    conn.execute("UPDATE quotations SET subtotal=?,total=? WHERE id=?", (subtotal, total, quotation_id))
    return subtotal, total

def list_quotations(agency_id, status=""):
    conn = get_db()
    try:
        q = """SELECT qt.*, u.name as creator_name, a.name as approver_name
               FROM quotations qt LEFT JOIN users u ON qt.created_by=u.id LEFT JOIN users a ON qt.approved_by=a.id
               WHERE qt.agency_id=?"""
        params = [agency_id]
        if status:
            q += " AND qt.status=?"; params.append(status)
        return [dict(r) for r in conn.execute(q+" ORDER BY qt.created_at DESC", params).fetchall()]
    finally:
        conn.close()

def get_quotation(quotation_id, agency_id):
    conn = get_db()
    try:
        row = conn.execute("""SELECT qt.*, u.name as creator_name, a.name as approver_name,
                              ag.name as agency_name
                              FROM quotations qt
                              LEFT JOIN users u ON qt.created_by=u.id
                              LEFT JOIN users a ON qt.approved_by=a.id
                              LEFT JOIN agencies ag ON qt.agency_id=ag.id
                              WHERE qt.id=? AND qt.agency_id=?""",
                           (quotation_id, agency_id)).fetchone()
        if not row: return None
        qt = dict(row)
        qt["items"] = [dict(i) for i in conn.execute(
            "SELECT * FROM quotation_items WHERE quotation_id=? ORDER BY id", (quotation_id,)).fetchall()]
        return qt
    finally:
        conn.close()

def create_quotation(agency_id, data, items, created_by):
    conn = get_db()
    try:
        c = conn.cursor()
        num = _next_seq(conn, "quotations", agency_id, "QT")
        discount_pct = float(data.get("discount_pct", 0))
        tax_pct = float(data.get("tax_pct", 15))
        c.execute("""INSERT INTO quotations
                     (agency_id,quote_number,client_name,client_phone,project_name,
                      valid_until,notes,terms,discount_pct,tax_pct,created_by)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (agency_id, num, data.get("client_name"), data.get("client_phone"),
                   data.get("project_name"), data.get("valid_until"),
                   data.get("notes"), data.get("terms"), discount_pct, tax_pct, created_by))
        qid = c.lastrowid
        _calc_and_save_items(conn, qid, items, discount_pct, tax_pct)
        conn.commit()
        return qid
    finally:
        conn.close()

def update_quotation(quotation_id, agency_id, data, items=None):
    conn = get_db()
    try:
        fields = ["client_name","client_phone","project_name","status","valid_until","notes","terms","discount_pct","tax_pct"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if sets:
            conn.execute(f"UPDATE quotations SET {sets} WHERE id=? AND agency_id=?", vals+[quotation_id,agency_id])
        if items is not None:
            row = conn.execute("SELECT discount_pct,tax_pct FROM quotations WHERE id=?",(quotation_id,)).fetchone()
            dp = float(data.get("discount_pct", dict(row)["discount_pct"] if row else 0))
            tp = float(data.get("tax_pct", dict(row)["tax_pct"] if row else 15))
            _calc_and_save_items(conn, quotation_id, items, dp, tp)
        conn.commit()
    finally:
        conn.close()

def approve_quotation(quotation_id, agency_id, approved_by):
    conn = get_db()
    try:
        row = conn.execute("SELECT status FROM quotations WHERE id=? AND agency_id=?",(quotation_id,agency_id)).fetchone()
        if not row: return False, "عرض السعر غير موجود"
        if dict(row)["status"] not in ("draft","sent"): return False, "لا يمكن اعتماد هذا العرض بحالته الحالية"
        conn.execute("UPDATE quotations SET status='approved',approved_by=?,approved_at=datetime('now') WHERE id=? AND agency_id=?",
                     (approved_by, quotation_id, agency_id))
        conn.commit()
        return True, "تم اعتماد عرض السعر"
    finally:
        conn.close()

def convert_quotation(quotation_id, agency_id, user_id):
    conn = get_db()
    try:
        qt = conn.execute("SELECT * FROM quotations WHERE id=? AND agency_id=?",(quotation_id,agency_id)).fetchone()
        if not qt: return False, "عرض السعر غير موجود"
        qt = dict(qt)
        if qt["status"] != "approved": return False, "يجب اعتماد عرض السعر أولاً قبل التحويل"
        num = _next_seq(conn, "sales_orders", agency_id, "SO")
        conn.execute("""INSERT INTO sales_orders (agency_id,quotation_id,order_number,client_name,client_phone,project_name,total,created_by)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (agency_id, quotation_id, num, qt["client_name"], qt["client_phone"],
                      qt["project_name"], qt["total"], user_id))
        conn.execute("UPDATE quotations SET status='converted',converted_at=datetime('now') WHERE id=? AND agency_id=?",
                     (quotation_id, agency_id))
        conn.commit()
        return True, f"تم تحويل عرض السعر إلى أمر بيع رقم {num}"
    finally:
        conn.close()

# ── SALES ORDERS ──────────────────────────────────────────────────────────────

def list_sales_orders(agency_id, status=""):
    conn = get_db()
    try:
        q = """SELECT so.*, u.name as creator_name FROM sales_orders so
               LEFT JOIN users u ON so.created_by=u.id WHERE so.agency_id=?"""
        params = [agency_id]
        if status:
            q += " AND so.status=?"; params.append(status)
        return [dict(r) for r in conn.execute(q+" ORDER BY so.created_at DESC", params).fetchall()]
    finally:
        conn.close()

def update_sales_order(so_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["status","notes"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if sets:
            conn.execute(f"UPDATE sales_orders SET {sets} WHERE id=? AND agency_id=?", vals+[so_id,agency_id])
        conn.commit()
    finally:
        conn.close()

# ── ACCOUNTING ────────────────────────────────────────────────────────────────

def list_transactions(agency_id, type_filter="", start="", end="", include_archived=False):
    conn = get_db()
    try:
        q = "SELECT t.*, u.name as creator_name FROM transactions t LEFT JOIN users u ON t.created_by=u.id WHERE t.agency_id=?"
        params = [agency_id]
        if not include_archived:
            q += " AND t.status='active'"
        if type_filter:
            q += " AND t.type=?"; params.append(type_filter)
        if start:
            q += " AND t.date>=?"; params.append(start)
        if end:
            q += " AND t.date<=?"; params.append(end)
        return [dict(r) for r in conn.execute(q+" ORDER BY t.date DESC, t.id DESC", params).fetchall()]
    finally:
        conn.close()

def get_accounting_summary(agency_id):
    conn = get_db()
    try:
        month = datetime.now().strftime("%Y-%m")
        income  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE agency_id=? AND type='income' AND status='active'",(agency_id,)).fetchone()[0]
        expense = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE agency_id=? AND type='expense' AND status='active'",(agency_id,)).fetchone()[0]
        m_income  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE agency_id=? AND type='income' AND status='active' AND strftime('%Y-%m',date)=?",(agency_id,month)).fetchone()[0]
        m_expense = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE agency_id=? AND type='expense' AND status='active' AND strftime('%Y-%m',date)=?",(agency_id,month)).fetchone()[0]
        return {"total_income":income,"total_expense":expense,"net":income-expense,
                "month_income":m_income,"month_expense":m_expense,"month_net":m_income-m_expense}
    finally:
        conn.close()

def create_transaction(agency_id, data, created_by):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO transactions (agency_id,type,category,description,amount,reference,date,created_by)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (agency_id, data["type"], data.get("category"), data["description"],
                   float(data["amount"]), data.get("reference"),
                   data.get("date", datetime.now().strftime("%Y-%m-%d")), created_by))
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()

def update_transaction(tx_id, agency_id, data):
    conn = get_db()
    try:
        fields = ["type","category","description","amount","reference","date"]
        sets = ", ".join(f"{f}=?" for f in fields if f in data)
        vals = [data[f] for f in fields if f in data]
        if sets:
            conn.execute(f"UPDATE transactions SET {sets} WHERE id=? AND agency_id=? AND status='active'", vals+[tx_id,agency_id])
        conn.commit()
    finally:
        conn.close()

def archive_transaction(tx_id, agency_id):
    conn = get_db()
    try:
        conn.execute("UPDATE transactions SET status='archived' WHERE id=? AND agency_id=?", (tx_id, agency_id))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
