"""SQLite storage for the procurement demo portal.

Ephemeral by design (Heroku dyno filesystem) — seeded on boot from the same
JSON files bundled with the AMP deployment, so ids agree on both sides.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = os.environ.get("DB_PATH", str(HERE / "portal.db"))

# Local dev = full repo checkout; Heroku = subtree-split slug with bundled copies.
SEED_DIRS = [HERE.parent / "data" / "seed", HERE / "seed_data"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, role TEXT,
  department TEXT, approval_limit_usd REAL
);
CREATE TABLE IF NOT EXISTS catalog_items (
  id TEXT PRIMARY KEY, sku TEXT, name TEXT, description TEXT,
  category TEXT, unit TEXT, unit_price_usd REAL
);
CREATE TABLE IF NOT EXISTS suppliers (
  id TEXT PRIMARY KEY, name TEXT, data_json TEXT
);
CREATE TABLE IF NOT EXISTS purchase_requests (
  pr_number TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL,
  raw_message TEXT,
  justification TEXT,
  urgency TEXT,
  detected_language TEXT,
  estimated_total_usd REAL,
  unmatched_json TEXT DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'submitted',
  phase TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS request_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pr_number TEXT NOT NULL REFERENCES purchase_requests(pr_number),
  catalog_item_id TEXT, sku TEXT, name TEXT,
  quantity INTEGER, unit_price_usd REAL, line_total_usd REAL
);
CREATE TABLE IF NOT EXISTS request_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pr_number TEXT NOT NULL REFERENCES purchase_requests(pr_number),
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(pr_number, kind)
);
CREATE TABLE IF NOT EXISTS kickoffs (
  kickoff_id TEXT PRIMARY KEY,
  pr_number TEXT NOT NULL REFERENCES purchase_requests(pr_number),
  mode TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_reviews (
  pr_number TEXT PRIMARY KEY REFERENCES purchase_requests(pr_number),
  callback_url TEXT NOT NULL,
  memo TEXT,
  received_at TEXT NOT NULL,
  resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS purchase_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pr_number TEXT NOT NULL REFERENCES purchase_requests(pr_number),
  po_number TEXT NOT NULL UNIQUE,
  supplier_id TEXT NOT NULL,
  supplier_name TEXT NOT NULL,
  markdown TEXT NOT NULL,
  total_usd REAL NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(pr_number, supplier_id)
);
CREATE TABLE IF NOT EXISTS purchase_order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  po_id INTEGER NOT NULL REFERENCES purchase_orders(id),
  request_item_id INTEGER NOT NULL UNIQUE REFERENCES request_items(id),
  quote_id TEXT NOT NULL,
  supplier_id TEXT NOT NULL,
  supplier_name TEXT NOT NULL,
  unit_price REAL NOT NULL,
  currency TEXT NOT NULL,
  line_total REAL NOT NULL,
  line_total_usd REAL NOT NULL,
  delivery_days INTEGER NOT NULL,
  risk_notes_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

# Required comparison FX. An empty value deliberately blocks quote review until
# an analyst configures it in the portal (or CLP_PER_USD is set at deploy time).
DEFAULT_CLP_PER_USD = os.environ.get("CLP_PER_USD", "")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _seed_path(name):
    for d in SEED_DIRS:
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(f"seed file {name} not found in {SEED_DIRS}")


def init_db():
    with db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
            for e in json.loads(_seed_path("employees.json").read_text()):
                conn.execute(
                    "INSERT INTO employees VALUES (?,?,?,?,?,?)",
                    (e["id"], e["name"], e.get("email"), e.get("role"),
                     e.get("department"), e.get("approval_limit_usd")),
                )
            for c in json.loads(_seed_path("catalog_items.json").read_text()):
                conn.execute(
                    "INSERT INTO catalog_items VALUES (?,?,?,?,?,?,?)",
                    (c["id"], c.get("sku"), c.get("name"), c.get("description"),
                     c.get("category"), c.get("unit"), c.get("unit_price_usd")),
                )
            for s in json.loads(_seed_path("suppliers.json").read_text()):
                conn.execute(
                    "INSERT INTO suppliers VALUES (?,?,?)",
                    (s["id"], s.get("name"), json.dumps(s)),
                )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('clp_per_usd', ?)",
            (DEFAULT_CLP_PER_USD,),
        )


def allocate_pr(employee_id, message):
    """Insert a placeholder PR row and return its new PR number."""
    with db() as conn:
        # BEGIN IMMEDIATE takes the write lock before the SELECT so two
        # concurrent submits can't allocate the same number.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(pr_number, 4) AS INTEGER)) FROM purchase_requests"
        ).fetchone()
        n = max(row[0] or 1000, 1000) + 1
        pr = f"PR-{n}"
        ts = now()
        conn.execute(
            "INSERT INTO purchase_requests (pr_number, employee_id, raw_message, status, created_at, updated_at)"
            " VALUES (?,?,?, 'submitted', ?, ?)",
            (pr, employee_id, message, ts, ts),
        )
    return pr


def upsert_artifact(conn, pr_number, kind, content):
    conn.execute(
        "INSERT INTO request_artifacts (pr_number, kind, content, created_at) VALUES (?,?,?,?)"
        " ON CONFLICT(pr_number, kind) DO UPDATE SET content=excluded.content",
        (pr_number, kind, content, now()),
    )


def get_employee(conn, employee_id):
    row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    return dict(row) if row else None


def get_setting(key, default=None):
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def allocate_employee_id(conn):
    """Next E-00N id, gap-tolerant."""
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 3) AS INTEGER)) FROM employees WHERE id LIKE 'E-%'"
    ).fetchone()
    return f"E-{(row[0] or 0) + 1:03d}"
