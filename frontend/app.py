"""Procurement demo portal — Flask app.

Board + chat widget frontend for the ProcurementFlow AMP deployment.
See docs/frontend-plan.md and docs/amp-contract.md (repo root) for the contract.
"""

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")  # OPENAI_API_KEY for local in-process mode

import markdown as md
import requests as http
from flask import Flask, jsonify, render_template, request

import amp
from db import allocate_pr, db, get_employee, init_db, now, upsert_artifact

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("portal")

app = Flask(__name__)

EXAMPLES_DIR = HERE.parent / "docs" / "examples"
FIXTURE_CALLBACK = "fixture:noop"


# ---------------------------------------------------------------- helpers

def strip_md_fence(text):
    """The backend usually strips ```markdown fences from documents, but real
    envelopes have arrived with them intact — strip defensively before storing."""
    text = (text or "").strip()
    m = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n?```$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def render_md(text):
    return md.markdown(text, extensions=["tables", "sane_lists"]) if text else None


def set_status(conn, pr_number, status, phase=None):
    conn.execute(
        "UPDATE purchase_requests SET status=?, phase=?, updated_at=? WHERE pr_number=?",
        (status, phase, now(), pr_number),
    )


def build_triage_inputs(pr_number):
    with db() as conn:
        pr = conn.execute(
            "SELECT * FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()
        items = [dict(r) for r in conn.execute(
            "SELECT catalog_item_id, sku, name, quantity, unit_price_usd, line_total_usd"
            " FROM request_items WHERE pr_number=?", (pr_number,)).fetchall()]
        employee = get_employee(conn, pr["employee_id"])
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        recent = []
        for r in conn.execute(
            "SELECT pr_number, estimated_total_usd, created_at FROM purchase_requests"
            " WHERE employee_id=? AND pr_number!=? AND created_at>=?",
            (pr["employee_id"], pr_number, cutoff),
        ).fetchall():
            cats = [c[0] for c in conn.execute(
                "SELECT DISTINCT ci.category FROM request_items ri"
                " JOIN catalog_items ci ON ci.id=ri.catalog_item_id WHERE ri.pr_number=?",
                (r["pr_number"],)).fetchall() if c[0]]
            recent.append({
                "pr_number": r["pr_number"],
                "estimated_total_usd": r["estimated_total_usd"],
                "category_summary": ", ".join(cats) or "general",
                "created_at": (r["created_at"] or "")[:10],
            })
    return {
        "mode": "triage",
        "request": {
            "pr_number": pr_number,
            "line_items": items,
            "justification": pr["justification"] or "",
            "urgency": pr["urgency"] or "normal",
            "unmatched": json.loads(pr["unmatched_json"] or "[]"),
            "estimated_total_usd": pr["estimated_total_usd"] or 0,
            "detected_language": pr["detected_language"] or "en",
            "requested_by": employee["name"],
        },
        "employee": employee,
        "recent_requests": recent,
    }


# ------------------------------------------------------- envelope pipeline

def process_envelope(pr_number, kickoff_id, envelope, chain=True):
    """Single idempotent sink for results from webhook, watchdog, local runs
    and fixtures. Terminal envelopes are claimed atomically; a triage
    `needs_review` snapshot is NON-terminal — it is the only pre-resolution
    source of alerts[]/escalation_md, so persist those and keep polling."""
    with db() as conn:
        row = conn.execute(
            "SELECT mode, state FROM kickoffs WHERE kickoff_id=?", (kickoff_id,)
        ).fetchone()
    if row is None:
        log.warning("envelope for unknown kickoff %s — ignored", kickoff_id)
        return

    mode = row["mode"]
    final_status = envelope.get("final_status") or ""
    is_terminal = (mode == "intake" and final_status == "submitted") or (
        mode == "triage" and final_status in ("approved", "rejected")
    )

    if not is_terminal:
        if mode == "triage" and final_status == "needs_review":
            with db() as conn:
                if envelope.get("alerts"):
                    upsert_artifact(conn, pr_number, "alerts", json.dumps(envelope["alerts"]))
                if envelope.get("escalation_md"):
                    upsert_artifact(conn, pr_number, "escalation_memo",
                                    strip_md_fence(envelope["escalation_md"]))
                if envelope.get("screening"):
                    upsert_artifact(conn, pr_number, "screening", json.dumps(envelope["screening"]))
                if envelope.get("sourcing"):
                    upsert_artifact(conn, pr_number, "sourcing", json.dumps(envelope["sourcing"]))
                conn.execute(
                    "UPDATE purchase_requests SET status='awaiting_review', updated_at=?"
                    " WHERE pr_number=? AND status NOT IN ('awaiting_review','approved','rejected')",
                    (now(), pr_number),
                )
        return

    with db() as conn:
        claimed = conn.execute(
            "UPDATE kickoffs SET state='done', updated_at=? WHERE kickoff_id=? AND state!='done'",
            (now(), kickoff_id),
        ).rowcount
    if not claimed:
        return  # webhook/watchdog race — the other path won

    if mode == "intake":
        draft = envelope.get("request_draft") or {}
        with db() as conn:
            conn.execute(
                "UPDATE purchase_requests SET justification=?, urgency=?, detected_language=?,"
                " estimated_total_usd=?, unmatched_json=?, status='in_triage', updated_at=?"
                " WHERE pr_number=?",
                (draft.get("justification"), draft.get("urgency"),
                 draft.get("detected_language"), draft.get("estimated_total_usd"),
                 json.dumps(draft.get("unmatched", [])), now(), pr_number),
            )
            conn.execute("DELETE FROM request_items WHERE pr_number=?", (pr_number,))
            for li in draft.get("line_items", []):
                conn.execute(
                    "INSERT INTO request_items (pr_number, catalog_item_id, sku, name,"
                    " quantity, unit_price_usd, line_total_usd) VALUES (?,?,?,?,?,?,?)",
                    (pr_number, li.get("catalog_item_id"), li.get("sku"), li.get("name"),
                     li.get("quantity"), li.get("unit_price_usd"), li.get("line_total_usd")),
                )
        if chain:
            amp.start_kickoff(pr_number, "triage", build_triage_inputs(pr_number))
        log.info("%s intake done → triage %s", pr_number, "kicked" if chain else "skipped")
    else:
        with db() as conn:
            for kind, key, is_md in (
                ("screening", "screening", False), ("sourcing", "sourcing", False),
                ("alerts", "alerts", False), ("purchase_order", "po_md", True),
                ("escalation_memo", "escalation_md", True), ("rejection_note", "rejection_md", True),
            ):
                val = envelope.get(key)
                if val:
                    upsert_artifact(conn, pr_number, kind,
                                    strip_md_fence(val) if is_md else json.dumps(val))
            set_status(conn, pr_number, final_status)
            conn.execute("UPDATE pending_reviews SET resolved_at=COALESCE(resolved_at, ?)"
                         " WHERE pr_number=?", (now(), pr_number))
        log.info("%s triage done → %s", pr_number, final_status)


def _submit_pipeline(pr_number, employee):
    """Background: wakeup ping, then the intake kickoff. Never blocks the ack."""
    try:
        amp.wakeup()
        with db() as conn:
            raw = conn.execute("SELECT raw_message FROM purchase_requests WHERE pr_number=?",
                               (pr_number,)).fetchone()["raw_message"]
        amp.start_kickoff(pr_number, "intake",
                          {"mode": "intake", "message": raw, "employee": employee})
    except Exception:
        log.exception("intake kickoff failed for %s", pr_number)


# ----------------------------------------------------------------- routes

@app.get("/")
def index():
    with db() as conn:
        employees = [dict(r) for r in conn.execute("SELECT * FROM employees").fetchall()]
    return render_template("index.html", employees=employees)


@app.get("/api/requests")
def list_requests():
    with db() as conn:
        rows = conn.execute(
            "SELECT pr.*, e.name AS employee_name, e.role AS employee_role,"
            " (SELECT COUNT(*) FROM request_items ri WHERE ri.pr_number=pr.pr_number) AS items_count,"
            " (SELECT content FROM request_artifacts a WHERE a.pr_number=pr.pr_number AND a.kind='alerts') AS alerts_json,"
            " (SELECT COUNT(*) FROM pending_reviews v WHERE v.pr_number=pr.pr_number AND v.resolved_at IS NULL) AS pending_review"
            " FROM purchase_requests pr JOIN employees e ON e.id=pr.employee_id"
            " ORDER BY pr.created_at DESC"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["alerts_count"] = len(json.loads(d.pop("alerts_json") or "[]"))
        d["unmatched"] = json.loads(d.pop("unmatched_json") or "[]")
        out.append(d)
    return jsonify(out)


@app.post("/api/requests")
def create_request():
    data = request.get_json(force=True)
    employee_id, message = data.get("employee_id"), (data.get("message") or "").strip()
    if not message or not employee_id:
        return jsonify({"error": "employee_id and message required"}), 400
    with db() as conn:
        employee = get_employee(conn, employee_id)
    if not employee:
        return jsonify({"error": "unknown employee"}), 400
    pr_number = allocate_pr(employee_id, message)
    threading.Thread(target=_submit_pipeline, args=(pr_number, employee), daemon=True).start()
    return jsonify({"pr_number": pr_number}), 201


@app.get("/api/requests/<pr_number>")
def request_detail(pr_number):
    with db() as conn:
        pr = conn.execute("SELECT * FROM purchase_requests WHERE pr_number=?", (pr_number,)).fetchone()
        if not pr:
            return jsonify({"error": "not found"}), 404
        d = dict(pr)
        d["employee"] = get_employee(conn, pr["employee_id"])
        d["unmatched"] = json.loads(d.pop("unmatched_json") or "[]")
        d["items"] = [dict(r) for r in conn.execute(
            "SELECT * FROM request_items WHERE pr_number=?", (pr_number,)).fetchall()]
        arts = {r["kind"]: r["content"] for r in conn.execute(
            "SELECT kind, content FROM request_artifacts WHERE pr_number=?", (pr_number,)).fetchall()}
        review = conn.execute(
            "SELECT * FROM pending_reviews WHERE pr_number=?", (pr_number,)).fetchone()
    for kind in ("screening", "sourcing", "alerts"):
        d[kind] = json.loads(arts[kind]) if kind in arts else None
    for kind in ("purchase_order", "escalation_memo", "rejection_note"):
        d[kind + "_html"] = render_md(arts.get(kind))
    d["pending_review"] = bool(review and not review["resolved_at"])
    d["review_resolved"] = bool(review and review["resolved_at"])
    return jsonify(d)


def _decide(pr_number, feedback):
    with db() as conn:
        review = conn.execute("SELECT * FROM pending_reviews WHERE pr_number=? AND resolved_at IS NULL",
                              (pr_number,)).fetchone()
    if not review:
        return jsonify({"error": "no pending review"}), 409
    if review["callback_url"] != FIXTURE_CALLBACK:
        resp = http.post(review["callback_url"],
                         json={"feedback": feedback, "source": "procurement-portal"}, timeout=30)
        resp.raise_for_status()
    with db() as conn:
        conn.execute("UPDATE pending_reviews SET resolved_at=? WHERE pr_number=?", (now(), pr_number))
    return jsonify({"ok": True, "feedback": feedback})


@app.post("/api/requests/<pr_number>/approve")
def approve(pr_number):
    return _decide(pr_number, "approved")


@app.post("/api/requests/<pr_number>/reject")
def reject(pr_number):
    return _decide(pr_number, "rejected")


def _find_key(obj, *names):
    """Recursive defensive search — webhook wrapper shapes are undocumented."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names and v:
                return v
        for v in obj.values():
            found = _find_key(v, *names)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key(v, *names)
            if found:
                return found
    return None


@app.post("/api/webhook/<pr_number>")
def flow_webhook(pr_number):
    auth = request.headers.get("Authorization", "")
    if amp.WEBHOOK_TOKEN and auth != f"Bearer {amp.WEBHOOK_TOKEN}":
        log.warning("webhook for %s with bad auth — dropped (watchdog will cover)", pr_number)
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(force=True, silent=True) or {}
    log.info("webhook %s: %s", pr_number, json.dumps(body)[:1500])

    events = body if isinstance(body, list) else [body]
    for event in events:
        name = _find_key(event, "event", "event_type", "type") or ""
        if name.startswith("tool_usage"):
            role = (_find_key(event, "agent_role", "agent") or "").lower()
            phase = "screening" if "screen" in role else "sourcing" if "sourc" in role else None
            if phase:
                with db() as conn:
                    conn.execute(
                        "UPDATE purchase_requests SET phase=?, updated_at=? WHERE pr_number=?"
                        " AND status IN ('in_triage','awaiting_review')",
                        (phase, now(), pr_number))
        elif name == "flow_finished" or not name:
            flow_name = _find_key(event, "flow_name") or ""
            if flow_name == "AgentExecutor":  # crewai >=1.15 inner-flow quirk
                continue
            envelope = amp.parse_result(event)
            if envelope:
                kickoff_id = _find_key(event, "kickoff_id", "execution_id")
                if not kickoff_id:
                    with db() as conn:
                        r = conn.execute("SELECT kickoff_id FROM kickoffs WHERE pr_number=?"
                                         " AND state='pending' ORDER BY created_at DESC",
                                         (pr_number,)).fetchone()
                    kickoff_id = r["kickoff_id"] if r else None
                if kickoff_id:
                    process_envelope(pr_number, kickoff_id, envelope)
    return jsonify({"ok": True})


@app.post("/api/hitl-webhook")
def hitl_webhook():
    token = request.args.get("token") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if amp.WEBHOOK_TOKEN and token != amp.WEBHOOK_TOKEN:
        # Permissive by design: dropping an escalation mid-demo is worse than
        # a briefly-open endpoint. Log loudly instead of 401ing.
        log.warning("HITL webhook token mismatch — processing anyway")
    body = request.get_json(force=True, silent=True) or {}
    log.info("HITL webhook: %s", json.dumps(body)[:1500])

    callback_url = _find_key(body, "callback_url", "callbackUrl")
    if not callback_url:
        return jsonify({"error": "no callback_url"}), 400
    memo = _find_key(body, "memo", "content", "message", "body") or ""
    kickoff_id = _find_key(body, "kickoff_id", "execution_id", "kickoffId")

    with db() as conn:
        pr_number = None
        if kickoff_id:
            r = conn.execute("SELECT pr_number FROM kickoffs WHERE kickoff_id=?", (kickoff_id,)).fetchone()
            pr_number = r["pr_number"] if r else None
        if not pr_number:
            # Fallback: the only in-flight triage. Fine for a demo, logged loudly.
            rows = conn.execute("SELECT pr_number FROM kickoffs WHERE mode='triage'"
                                " AND state='pending'").fetchall()
            if len(rows) == 1:
                pr_number = rows[0]["pr_number"]
                log.warning("HITL webhook without kickoff_id — matched sole in-flight triage %s", pr_number)
        if not pr_number:
            log.error("HITL webhook could not be matched to a PR — stored nothing")
            return jsonify({"error": "unmatched"}), 202
        conn.execute(
            "INSERT INTO pending_reviews (pr_number, callback_url, memo, received_at)"
            " VALUES (?,?,?,?) ON CONFLICT(pr_number) DO UPDATE SET"
            " callback_url=excluded.callback_url, memo=excluded.memo,"
            " received_at=excluded.received_at, resolved_at=NULL",
            (pr_number, callback_url, memo, now()))
        conn.execute(
            "UPDATE purchase_requests SET status='awaiting_review', updated_at=?"
            " WHERE pr_number=? AND status NOT IN ('approved','rejected')",
            (now(), pr_number))
    return jsonify({"ok": True, "pr_number": pr_number})


@app.post("/api/wakeup")
def wakeup():
    threading.Thread(target=amp.wakeup, daemon=True).start()
    return "", 204


# ------------------------------------------------------------ dev fixtures

@app.cli.command("demo-fixtures")
def demo_fixtures():
    """Replay docs/examples envelopes through process_envelope. Dev-only —
    docs/ is gitignored and never reaches the Heroku slug."""
    if not EXAMPLES_DIR.exists():
        raise SystemExit(f"{EXAMPLES_DIR} not found — demo-fixtures is a local dev tool "
                         "(docs/ is gitignored and absent from deploys)")
    init_db()

    def replay(intake_file, triage_file, escalate=False):
        tri = json.loads((EXAMPLES_DIR / triage_file).read_text())
        pr = tri["request"]["pr_number"]
        emp = tri["employee"]["id"]
        raw = (json.loads((EXAMPLES_DIR / intake_file).read_text())["message"]
               if intake_file else tri["request"].get("justification", ""))
        ts = now()
        req = tri["request"]
        with db() as conn:
            conn.execute("INSERT OR REPLACE INTO purchase_requests"
                         " (pr_number, employee_id, raw_message, status, created_at, updated_at)"
                         " VALUES (?,?,?, 'submitted', ?, ?)", (pr, emp, raw, ts, ts))
            if not intake_file:
                # No intake envelope to replay — backfill the fields intake would have set.
                conn.execute(
                    "UPDATE purchase_requests SET justification=?, urgency=?,"
                    " detected_language=?, estimated_total_usd=?, unmatched_json=?"
                    " WHERE pr_number=?",
                    (req.get("justification"), req.get("urgency"), req.get("detected_language"),
                     req.get("estimated_total_usd"), json.dumps(req.get("unmatched", [])), pr))
                for li in req.get("line_items", []):
                    conn.execute(
                        "INSERT INTO request_items (pr_number, catalog_item_id, sku, name,"
                        " quantity, unit_price_usd, line_total_usd) VALUES (?,?,?,?,?,?,?)",
                        (pr, li.get("catalog_item_id"), li.get("sku"), li.get("name"),
                         li.get("quantity"), li.get("unit_price_usd"), li.get("line_total_usd")))
        for mode, fname in (("intake", intake_file), ("triage", triage_file)):
            if not fname:
                continue
            kid = f"fixture-{uuid.uuid4()}"
            with db() as conn:
                conn.execute("INSERT INTO kickoffs (kickoff_id, pr_number, mode, state,"
                             " created_at, updated_at) VALUES (?,?,?, 'pending', ?, ?)",
                             (kid, pr, mode, now(), now()))
            process_envelope(pr, kid, json.loads((EXAMPLES_DIR / fname).read_text()), chain=False)
        if escalate:
            with db() as conn:
                conn.execute("INSERT OR REPLACE INTO pending_reviews"
                             " (pr_number, callback_url, memo, received_at) VALUES (?,?,?,?)",
                             (pr, FIXTURE_CALLBACK, "Fixture escalation — Approve/Reject are no-ops.",
                              now()))
        print(f"  {pr} ← {triage_file}")

    print("Replaying fixtures:")
    replay("A_happy_es_intake.json", "A_happy_es_triage.json")
    replay(None, "B_escalation_triage.json", escalate=True)
    replay(None, "C_fraud_triage.json")
    print("Done — board now shows one card per state.")


init_db()
amp.start_watchdog()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
