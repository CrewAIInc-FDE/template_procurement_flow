"""Procurement demo portal — Flask app.

Board + chat widget frontend for the ProcurementFlow AMP deployment.
See docs/frontend-plan.md and docs/amp-contract.md (repo root) for the contract.
"""
# ruff: noqa: E402

import json
import logging
import threading
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
from db import (
    allocate_employee_id,
    allocate_pr,
    db,
    get_employee,
    get_setting,
    init_db,
    now,
    set_setting,
    upsert_artifact,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("portal")

app = Flask(__name__)

FIXTURE_CALLBACK = "fixture:noop"


# ---------------------------------------------------------------- helpers

def strip_md_fence(text):
    """The backend usually strips ```markdown fences from documents, but real
    envelopes have arrived with them intact — strip defensively before storing."""
    text = (text or "").strip()
    opening, separator, body = text.partition("\n")
    if (
        separator
        and opening.strip() in {"```", "```markdown", "```md"}
        and body.endswith("```")
    ):
        return body[:-3].strip()
    return text


def render_md(text):
    return md.markdown(text, extensions=["tables", "sane_lists"]) if text else None


def set_status(conn, pr_number, status, phase=None):
    conn.execute(
        "UPDATE purchase_requests SET status=?, phase=?, updated_at=? WHERE pr_number=?",
        (status, phase, now(), pr_number),
    )


def recent_requests(conn, employee_id, pr_number):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    recent = []
    for row in conn.execute(
        "SELECT pr_number, estimated_total_usd, created_at FROM purchase_requests"
        " WHERE employee_id=? AND pr_number!=? AND created_at>=?",
        (employee_id, pr_number, cutoff),
    ).fetchall():
        categories = [category[0] for category in conn.execute(
            "SELECT DISTINCT ci.category FROM request_items ri"
            " JOIN catalog_items ci ON ci.id=ri.catalog_item_id WHERE ri.pr_number=?",
            (row["pr_number"],),
        ).fetchall() if category[0]]
        recent.append({
            "pr_number": row["pr_number"],
            "estimated_total_usd": row["estimated_total_usd"],
            "category_summary": ", ".join(categories) or "general",
            "created_at": (row["created_at"] or "")[:10],
        })
    return recent


def rfq_dispatches(conn, pr_number):
    return [dict(row) for row in conn.execute(
        "SELECT rfq_id, supplier_id, supplier_name, intended_recipient, actual_recipient,"
        " override_applied, gmail_message_id, gmail_thread_id, status, error, sent_at,"
        " reply_count, last_reply_at FROM rfq_dispatches WHERE pr_number=? ORDER BY supplier_name",
        (pr_number,),
    ).fetchall()]


def upsert_rfq_dispatches(conn, pr_number, dispatches):
    for dispatch in dispatches or []:
        conn.execute(
            "INSERT INTO rfq_dispatches"
            " (rfq_id, pr_number, supplier_id, supplier_name, intended_recipient,"
            " actual_recipient, override_applied, gmail_message_id, gmail_thread_id,"
            " status, error, sent_at, reply_count, last_reply_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(rfq_id) DO UPDATE SET"
            " intended_recipient=excluded.intended_recipient,"
            " actual_recipient=excluded.actual_recipient,"
            " override_applied=excluded.override_applied,"
            " gmail_message_id=excluded.gmail_message_id,"
            " gmail_thread_id=excluded.gmail_thread_id, status=excluded.status,"
            " error=excluded.error, sent_at=excluded.sent_at,"
            " reply_count=excluded.reply_count, last_reply_at=excluded.last_reply_at",
            (
                dispatch["rfq_id"], pr_number, dispatch["supplier_id"],
                dispatch["supplier_name"], dispatch.get("intended_recipient", ""),
                dispatch.get("actual_recipient", ""), int(dispatch.get("override_applied", False)),
                dispatch.get("gmail_message_id", ""), dispatch.get("gmail_thread_id", ""),
                dispatch.get("status", "failed"), dispatch.get("error", ""),
                dispatch.get("sent_at", ""), int(dispatch.get("reply_count", 0)),
                dispatch.get("last_reply_at", ""),
            ),
        )


def build_quote_review_inputs(pr_number):
    with db() as conn:
        pr = conn.execute(
            "SELECT * FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()
        items = [dict(r) for r in conn.execute(
            "SELECT ri.id AS request_item_id, ri.catalog_item_id, ri.sku, ri.name,"
            " ri.quantity, ri.unit_price_usd, ri.line_total_usd FROM request_items ri"
            " LEFT JOIN purchase_order_items poi ON poi.request_item_id=ri.id"
            " WHERE ri.pr_number=? AND poi.id IS NULL ORDER BY ri.id",
            (pr_number,),
        ).fetchall()]
        employee = get_employee(conn, pr["employee_id"])
        existing_awards = []
        for row in conn.execute(
            "SELECT poi.request_item_id, ri.catalog_item_id, ri.sku, ri.name AS item_name,"
            " ri.quantity, poi.quote_id, poi.supplier_id, poi.supplier_name,"
            " poi.unit_price, poi.currency, poi.line_total, poi.line_total_usd,"
            " poi.delivery_days, poi.risk_notes_json FROM purchase_order_items poi"
            " JOIN request_items ri ON ri.id=poi.request_item_id"
            " WHERE ri.pr_number=? ORDER BY poi.request_item_id",
            (pr_number,),
        ).fetchall():
            award = dict(row)
            award["risk_notes"] = json.loads(award.pop("risk_notes_json") or "[]")
            existing_awards.append(award)
        existing_purchase_orders = [dict(r) for r in conn.execute(
            "SELECT po_number, supplier_id, supplier_name FROM purchase_orders"
            " WHERE pr_number=? ORDER BY po_number", (pr_number,)).fetchall()]
        recent = recent_requests(conn, pr["employee_id"], pr_number)
        dispatches = rfq_dispatches(conn, pr_number)
    clp_per_usd = float(get_setting("clp_per_usd"))
    return {
        "mode": "quote_review",
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
        "clp_per_usd": clp_per_usd,
        "existing_awards": existing_awards,
        "existing_purchase_orders": existing_purchase_orders,
        "rfq_dispatches": dispatches,
    }


def build_po_retry_inputs(pr_number):
    inputs = build_quote_review_inputs(pr_number)
    with db() as conn:
        status = conn.execute(
            "SELECT status FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()[0]
        rows = [dict(row) for row in conn.execute(
            "SELECT po_number, supplier_id, supplier_name, markdown, total_usd"
            " FROM purchase_orders WHERE pr_number=? ORDER BY po_number",
            (pr_number,),
        ).fetchall()]
        artifacts = {
            row["kind"]: json.loads(row["content"])
            for row in conn.execute(
                "SELECT kind, content FROM request_artifacts"
                " WHERE pr_number=? AND kind IN ('warnings','alerts')",
                (pr_number,),
            ).fetchall()
        }

    def is_delivery_warning(message):
        return (
            "generated but not delivered" in message
            or message.startswith("PO delivery is retryable:")
        )

    awards_by_supplier = {}
    for award in inputs["existing_awards"]:
        awards_by_supplier.setdefault(award["supplier_id"], []).append(award)
    inputs.update({
        "operation": "retry_pos",
        "retry_return_status": status,
        "purchase_orders": [
            {
                **row,
                "pr_number": pr_number,
                "items": awards_by_supplier.get(row["supplier_id"], []),
                "item_ids": [
                    item["request_item_id"]
                    for item in awards_by_supplier.get(row["supplier_id"], [])
                ],
            }
            for row in rows
        ],
        "warnings": [
            warning
            for warning in artifacts.get("warnings", [])
            if not is_delivery_warning(warning)
        ],
        "alerts": [
            alert
            for alert in artifacts.get("alerts", [])
            if not is_delivery_warning(alert.get("message", ""))
        ],
    })
    return inputs


# ------------------------------------------------------- envelope pipeline

def process_envelope(pr_number, kickoff_id, envelope):
    """Idempotent result sink shared by webhooks, polling, and local runs."""
    with db() as conn:
        row = conn.execute(
            "SELECT mode, state FROM kickoffs WHERE kickoff_id=?", (kickoff_id,)
        ).fetchone()
    if row is None:
        log.warning("envelope for unknown kickoff %s — ignored", kickoff_id)
        return

    mode = row["mode"]
    final_status = envelope.get("final_status") or ""
    is_terminal = (mode == "intake" and final_status in ("awaiting_quotes", "rfq_failed", "rejected")) or (
        mode == "quote_review"
        and final_status in ("approved", "rejected", "awaiting_quotes")
    )

    if not is_terminal:
        if mode == "quote_review" and final_status == "needs_review":
            with db() as conn:
                upsert_rfq_dispatches(conn, pr_number, envelope.get("rfq_dispatches"))
                for kind in ("alerts", "screening", "quote_review", "warnings"):
                    if envelope.get(kind):
                        upsert_artifact(conn, pr_number, kind, json.dumps(envelope[kind]))
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
                " estimated_total_usd=?, unmatched_json=?, status=?, phase=NULL, updated_at=?"
                " WHERE pr_number=?",
                (draft.get("justification"), draft.get("urgency"),
                 draft.get("detected_language"), draft.get("estimated_total_usd"),
                 json.dumps(draft.get("unmatched", [])), final_status, now(), pr_number),
            )
            conn.execute("DELETE FROM request_items WHERE pr_number=?", (pr_number,))
            for li in draft.get("line_items", []):
                conn.execute(
                    "INSERT INTO request_items (pr_number, catalog_item_id, sku, name,"
                    " quantity, unit_price_usd, line_total_usd) VALUES (?,?,?,?,?,?,?)",
                    (pr_number, li.get("catalog_item_id"), li.get("sku"), li.get("name"),
                     li.get("quantity"), li.get("unit_price_usd"), li.get("line_total_usd")),
                )
            upsert_rfq_dispatches(conn, pr_number, envelope.get("rfq_dispatches"))
            for kind, key, is_md in (
                ("screening", "screening", False),
                ("alerts", "alerts", False),
                ("warnings", "warnings", False),
                ("rejection_note", "rejection_md", True),
            ):
                value = envelope.get(key)
                if value:
                    upsert_artifact(
                        conn, pr_number, kind,
                        strip_md_fence(value) if is_md else json.dumps(value),
                    )
        log.info("%s intake done → %s", pr_number, final_status)
    else:
        with db() as conn:
            upsert_rfq_dispatches(conn, pr_number, envelope.get("rfq_dispatches"))
            for kind, key, is_md in (
                ("screening", "screening", False),
                ("quote_review", "quote_review", False),
                ("alerts", "alerts", False),
                ("warnings", "warnings", False),
                ("po_dispatch_batch", "po_dispatch_batch", False),
                ("rejection_note", "rejection_md", True),
            ):
                val = envelope.get(key)
                if val or kind in {"alerts", "warnings", "po_dispatch_batch"}:
                    empty_value = {} if kind == "po_dispatch_batch" else []
                    upsert_artifact(conn, pr_number, kind,
                                    strip_md_fence(val) if is_md else json.dumps(val or empty_value))
            for po in envelope.get("purchase_orders") or []:
                ts = now()
                conn.execute(
                    "INSERT INTO purchase_orders"
                    " (pr_number, po_number, supplier_id, supplier_name, markdown, total_usd, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(pr_number, supplier_id) DO UPDATE SET"
                    " po_number=excluded.po_number, supplier_name=excluded.supplier_name,"
                    " markdown=excluded.markdown, total_usd=excluded.total_usd, updated_at=excluded.updated_at",
                    (pr_number, po["po_number"], po["supplier_id"], po["supplier_name"],
                     po["markdown"], po["total_usd"], ts, ts),
                )
                po_id = conn.execute(
                    "SELECT id FROM purchase_orders WHERE pr_number=? AND supplier_id=?",
                    (pr_number, po["supplier_id"]),
                ).fetchone()[0]
                for item in po.get("items", []):
                    conn.execute(
                        "INSERT INTO purchase_order_items"
                        " (po_id, request_item_id, quote_id, supplier_id, supplier_name, unit_price,"
                        " currency, line_total, line_total_usd, delivery_days, risk_notes_json, created_at, updated_at)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(request_item_id) DO UPDATE SET"
                        " po_id=excluded.po_id, quote_id=excluded.quote_id, supplier_id=excluded.supplier_id,"
                        " supplier_name=excluded.supplier_name, unit_price=excluded.unit_price,"
                        " currency=excluded.currency, line_total=excluded.line_total,"
                        " line_total_usd=excluded.line_total_usd, delivery_days=excluded.delivery_days,"
                        " risk_notes_json=excluded.risk_notes_json, updated_at=excluded.updated_at",
                        (po_id, item["request_item_id"], item["quote_id"], item["supplier_id"],
                         item["supplier_name"], item["unit_price"], item["currency"],
                         item["line_total"], item["line_total_usd"], item["delivery_days"],
                         json.dumps(item.get("risk_notes", [])), ts, ts),
                    )
            if final_status == "approved":
                outstanding = conn.execute(
                    "SELECT COUNT(*) FROM request_items ri LEFT JOIN purchase_order_items poi"
                    " ON poi.request_item_id=ri.id WHERE ri.pr_number=? AND poi.id IS NULL",
                    (pr_number,),
                ).fetchone()[0]
                final_status = "awaiting_quotes" if outstanding else "approved"
            set_status(conn, pr_number, final_status)
            conn.execute("UPDATE pending_reviews SET resolved_at=COALESCE(resolved_at, ?)"
                         " WHERE pr_number=?", (now(), pr_number))
        log.info("%s quote review done → %s", pr_number, final_status)


def _submit_pipeline(pr_number, employee):
    """Background: wakeup ping, then the intake kickoff. Never blocks the ack."""
    try:
        amp.wakeup()
        with db() as conn:
            row = conn.execute(
                "SELECT raw_message, employee_id FROM purchase_requests WHERE pr_number=?",
                (pr_number,),
            ).fetchone()
            raw = row["raw_message"]
            recent = recent_requests(conn, row["employee_id"], pr_number)
            set_status(conn, pr_number, "submitted", "extracting")
        amp.start_kickoff(
            pr_number,
            "intake",
            {
                "mode": "intake",
                "message": raw,
                "employee": employee,
                "request": {"pr_number": pr_number},
                "recent_requests": recent,
            },
        )
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
            " FROM purchase_requests pr LEFT JOIN employees e ON e.id=pr.employee_id"
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
            "SELECT ri.*, poi.quote_id, poi.supplier_name AS awarded_supplier,"
            " po.po_number FROM request_items ri"
            " LEFT JOIN purchase_order_items poi ON poi.request_item_id=ri.id"
            " LEFT JOIN purchase_orders po ON po.id=poi.po_id"
            " WHERE ri.pr_number=? ORDER BY ri.id", (pr_number,)).fetchall()]
        d["outstanding_items"] = [item for item in d["items"] if not item["quote_id"]]
        arts = {r["kind"]: r["content"] for r in conn.execute(
            "SELECT kind, content FROM request_artifacts WHERE pr_number=?", (pr_number,)).fetchall()}
        review = conn.execute(
            "SELECT * FROM pending_reviews WHERE pr_number=?", (pr_number,)).fetchone()
        purchase_orders = [dict(r) for r in conn.execute(
            "SELECT po_number, supplier_id, supplier_name, markdown, total_usd"
            " FROM purchase_orders WHERE pr_number=? ORDER BY po_number",
            (pr_number,),
        ).fetchall()]
        d["rfq_dispatches"] = rfq_dispatches(conn, pr_number)
    for kind in ("screening", "quote_review", "alerts", "warnings"):
        d[kind] = json.loads(arts[kind]) if kind in arts else None
    po_dispatch_batch = json.loads(arts["po_dispatch_batch"]) if "po_dispatch_batch" in arts else {}
    if not isinstance(po_dispatch_batch, dict):
        po_dispatch_batch = {}
    d["po_dispatches"] = po_dispatch_batch.get("dispatches", [])
    d["rejection_note_html"] = render_md(arts.get("rejection_note"))
    d["purchase_orders"] = []
    for po in purchase_orders:
        markdown = po.pop("markdown")
        d["purchase_orders"].append({**po, "html": render_md(markdown)})
    if review and review["memo"]:
        try:
            d["quote_review"] = json.loads(strip_md_fence(review["memo"]))
        except (TypeError, ValueError):
            pass
    d["pending_review"] = bool(review and not review["resolved_at"])
    d["review_resolved"] = bool(review and review["resolved_at"])
    return jsonify(d)


@app.post("/api/requests/<pr_number>/review-quotes")
def review_quotes(pr_number):
    force = request.args.get("force") == "1"
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        pr = conn.execute(
            "SELECT status FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()
        if not pr:
            return jsonify({"error": "not found"}), 404
        pending = conn.execute(
            "SELECT kickoff_id FROM kickoffs WHERE pr_number=? AND mode='quote_review'"
            " AND state='pending' ORDER BY created_at DESC LIMIT 1",
            (pr_number,),
        ).fetchone()
        if force and pr["status"] == "awaiting_review":
            conn.execute(
                "UPDATE pending_reviews SET resolved_at=?"
                " WHERE pr_number=? AND resolved_at IS NULL",
                (now(), pr_number),
            )
            conn.execute(
                "UPDATE kickoffs SET state='superseded', updated_at=?"
                " WHERE pr_number=? AND mode='quote_review' AND state='pending'",
                (now(), pr_number),
            )
            pending = None
        if pending or pr["status"] in ("reviewing_quotes", "awaiting_review"):
            if not (force and pr["status"] == "awaiting_review"):
                return jsonify({
                    "kickoff_id": pending["kickoff_id"] if pending else None,
                    "already_running": True,
                }), 202
        if pr["status"] != "awaiting_quotes" and not (
            force and pr["status"] == "awaiting_review"
        ):
            return jsonify({"error": "request is not awaiting quotes"}), 409
        setting = conn.execute(
            "SELECT value FROM settings WHERE key='clp_per_usd'"
        ).fetchone()
        try:
            clp_per_usd = float(setting["value"] if setting else None)
        except (TypeError, ValueError):
            clp_per_usd = 0
        if clp_per_usd <= 0:
            return jsonify({"error": "configure a positive CLP per USD rate first"}), 400
        outstanding = conn.execute(
            "SELECT COUNT(*) FROM request_items ri LEFT JOIN purchase_order_items poi"
            " ON poi.request_item_id=ri.id WHERE ri.pr_number=? AND poi.id IS NULL",
            (pr_number,),
        ).fetchone()[0]
        if not outstanding:
            return jsonify({"error": "no outstanding items"}), 409
        set_status(conn, pr_number, "reviewing_quotes", "gmail")
    try:
        kickoff_id = amp.start_kickoff(
            pr_number, "quote_review", build_quote_review_inputs(pr_number)
        )
    except Exception:
        log.exception("quote review kickoff failed for %s", pr_number)
        with db() as conn:
            set_status(conn, pr_number, "awaiting_quotes")
        return jsonify({"error": "could not start quote review"}), 502
    return jsonify({"kickoff_id": kickoff_id, "already_running": False}), 202


@app.post("/api/requests/<pr_number>/retry-pos")
def retry_pos(pr_number):
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        pr = conn.execute(
            "SELECT status FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()
        if not pr:
            return jsonify({"error": "not found"}), 404
        if pr["status"] not in ("approved", "awaiting_quotes"):
            return jsonify({"error": "request has no retryable PO delivery"}), 409
        artifact = conn.execute(
            "SELECT content FROM request_artifacts"
            " WHERE pr_number=? AND kind='po_dispatch_batch'",
            (pr_number,),
        ).fetchone()
        batch = json.loads(artifact["content"]) if artifact else {}
        if not any(row.get("status") == "failed" for row in batch.get("dispatches", [])):
            return jsonify({"error": "request has no failed PO delivery"}), 409
        pending = conn.execute(
            "SELECT kickoff_id FROM kickoffs WHERE pr_number=? AND mode='quote_review'"
            " AND state='pending' ORDER BY created_at DESC LIMIT 1",
            (pr_number,),
        ).fetchone()
        if pending:
            return jsonify({
                "kickoff_id": pending["kickoff_id"],
                "already_running": True,
            }), 202
        conn.execute(
            "UPDATE purchase_requests SET phase='po_delivery', updated_at=?"
            " WHERE pr_number=?",
            (now(), pr_number),
        )
    try:
        kickoff_id = amp.start_kickoff(
            pr_number, "quote_review", build_po_retry_inputs(pr_number)
        )
    except Exception:
        log.exception("PO delivery retry failed to start for %s", pr_number)
        with db() as conn:
            conn.execute(
                "UPDATE purchase_requests SET phase=NULL, updated_at=? WHERE pr_number=?",
                (now(), pr_number),
            )
        return jsonify({"error": "could not retry PO delivery"}), 502
    return jsonify({"kickoff_id": kickoff_id, "already_running": False}), 202


@app.post("/api/requests/<pr_number>/retry-rfqs")
def retry_rfqs(pr_number):
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        pr = conn.execute(
            "SELECT employee_id, status FROM purchase_requests WHERE pr_number=?", (pr_number,)
        ).fetchone()
        if not pr:
            return jsonify({"error": "not found"}), 404
        if pr["status"] != "rfq_failed":
            return jsonify({"error": "request does not have a failed RFQ dispatch"}), 409
        pending = conn.execute(
            "SELECT 1 FROM kickoffs WHERE pr_number=? AND mode='intake' AND state='pending'",
            (pr_number,),
        ).fetchone()
        if pending:
            return jsonify({"already_running": True}), 202
        employee = get_employee(conn, pr["employee_id"])
        set_status(conn, pr_number, "submitted", "extracting")
    threading.Thread(target=_submit_pipeline, args=(pr_number, employee), daemon=True).start()
    return jsonify({"already_running": False}), 202


def _validate_portal_awards(conn, pr_number, proposal, awards):
    lines = proposal.get("lines") or []
    if not isinstance(awards, list) or len(awards) != len(lines):
        raise ValueError("exactly one award is required for every covered item")
    line_by_item = {int(line["request_item_id"]): line for line in lines}
    normalized = []
    seen = set()
    for award in awards:
        try:
            item_id = int(award["request_item_id"])
            quote_id = str(award["quote_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("each award needs request_item_id and quote_id") from exc
        line = line_by_item.get(item_id)
        if not line or item_id in seen:
            raise ValueError(f"invalid or duplicate request item {item_id}")
        if quote_id not in {str(option["quote_id"]) for option in line.get("options", [])}:
            raise ValueError(f"quote {quote_id} is not valid for item {item_id}")
        item = conn.execute(
            "SELECT ri.id, poi.id AS award_id FROM request_items ri"
            " LEFT JOIN purchase_order_items poi ON poi.request_item_id=ri.id"
            " WHERE ri.id=? AND ri.pr_number=?", (item_id, pr_number),
        ).fetchone()
        if not item or item["award_id"]:
            raise ValueError(f"item {item_id} is unknown or already awarded")
        seen.add(item_id)
        normalized.append({"request_item_id": item_id, "quote_id": quote_id})
    return sorted(normalized, key=lambda award: award["request_item_id"])


def _decide(pr_number, feedback):
    with db() as conn:
        review = conn.execute("SELECT * FROM pending_reviews WHERE pr_number=? AND resolved_at IS NULL",
                              (pr_number,)).fetchone()
    if not review:
        return jsonify({"error": "no pending review"}), 409
    if review["callback_url"] != FIXTURE_CALLBACK:
        try:
            resp = http.post(review["callback_url"],
                             json={"feedback": feedback, "source": "procurement-portal"}, timeout=30)
            resp.raise_for_status()
        except http.RequestException:
            log.exception("decision delivery failed for %s", pr_number)
            return jsonify({"error": "could not deliver decision"}), 502
    with db() as conn:
        conn.execute("UPDATE pending_reviews SET resolved_at=? WHERE pr_number=?", (now(), pr_number))
        conn.execute(
            "UPDATE purchase_requests SET status='reviewing_quotes', phase='approval', updated_at=?"
            " WHERE pr_number=? AND status='awaiting_review'", (now(), pr_number)
        )
    return jsonify({"ok": True, "feedback": feedback})


@app.post("/api/requests/<pr_number>/approve")
def approve(pr_number):
    data = request.get_json(force=True, silent=True) or {}
    with db() as conn:
        review = conn.execute(
            "SELECT memo FROM pending_reviews WHERE pr_number=? AND resolved_at IS NULL",
            (pr_number,),
        ).fetchone()
        if not review:
            return jsonify({"error": "no pending review"}), 409
        try:
            proposal = json.loads(strip_md_fence(review["memo"]))
            awards = _validate_portal_awards(conn, pr_number, proposal, data.get("awards"))
        except (TypeError, ValueError):
            return jsonify({"error": "invalid award selection"}), 400
    feedback = json.dumps({"decision": "approved", "awards": awards}, separators=(",", ":"))
    return _decide(pr_number, feedback)


@app.post("/api/requests/<pr_number>/reject")
def reject(pr_number):
    return _decide(pr_number, json.dumps({"decision": "rejected"}))


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
            phase = "screening" if "screen" in role else "gmail" if "quote" in role or "inbox" in role else None
            if phase:
                with db() as conn:
                    conn.execute(
                        "UPDATE purchase_requests SET phase=?, updated_at=? WHERE pr_number=?"
                        " AND status IN ('submitted','reviewing_quotes','awaiting_review')",
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
        # Permissive by design: dropping a quote review mid-demo is worse than
        # a briefly-open endpoint. Log loudly instead of 401ing.
        log.warning("HITL webhook token mismatch — processing anyway")
    body = request.get_json(force=True, silent=True) or {}
    log.info("HITL webhook: %s", json.dumps(body)[:1500])

    callback_url = _find_key(body, "callback_url", "callbackUrl")
    if not callback_url:
        return jsonify({"error": "no callback_url"}), 400
    # The HITL method returns the structured quote proposal in `output`.
    proposal = _find_key(body, "output", "memo", "content", "body") or {}
    if isinstance(proposal, str):
        try:
            proposal = json.loads(strip_md_fence(proposal))
        except (TypeError, ValueError):
            proposal = {}
    if not isinstance(proposal, dict) or not proposal.get("lines"):
        return jsonify({"error": "HITL output is not a structured quote review"}), 400
    # AMP correlates by flow_id (== the kickoff_id returned by /kickoff == execution_id).
    kickoff_id = _find_key(body, "kickoff_id", "execution_id", "kickoffId", "flow_id")

    with db() as conn:
        pr_number = None
        if kickoff_id:
            r = conn.execute("SELECT pr_number FROM kickoffs WHERE kickoff_id=?", (kickoff_id,)).fetchone()
            pr_number = r["pr_number"] if r else None
        if not pr_number:
            # Fallback: the only in-flight quote review. Fine for a demo, logged loudly.
            rows = conn.execute("SELECT pr_number FROM kickoffs WHERE mode='quote_review'"
                                " AND state='pending'").fetchall()
            if len(rows) == 1:
                pr_number = rows[0]["pr_number"]
                log.warning("HITL webhook without kickoff_id — matched sole quote review %s", pr_number)
        if not pr_number:
            log.error("HITL webhook could not be matched to a PR — stored nothing")
            return jsonify({"error": "unmatched"}), 202
        if proposal.get("pr_number") and proposal["pr_number"] != pr_number:
            return jsonify({"error": "proposal PR does not match kickoff"}), 400
        conn.execute(
            "INSERT INTO pending_reviews (pr_number, callback_url, memo, received_at)"
            " VALUES (?,?,?,?) ON CONFLICT(pr_number) DO UPDATE SET"
            " callback_url=excluded.callback_url, memo=excluded.memo,"
            " received_at=excluded.received_at, resolved_at=NULL",
            (pr_number, callback_url, json.dumps(proposal), now()))
        if proposal:
            upsert_artifact(conn, pr_number, "quote_review", json.dumps(proposal))
        conn.execute(
            "UPDATE purchase_requests SET status='awaiting_review', updated_at=?"
            " WHERE pr_number=? AND status NOT IN ('approved','rejected')",
            (now(), pr_number))
    return jsonify({"ok": True, "pr_number": pr_number})


@app.post("/api/wakeup")
def wakeup():
    threading.Thread(target=amp.wakeup, daemon=True).start()
    return "", 204


# ------------------------------------------------------- config & profiles

def _clean_employee_payload(data, require_name=True):
    """Validate at the trust boundary. Returns (fields_dict, error_response|None)."""
    out = {}
    if "name" in data or require_name:
        name = (data.get("name") or "").strip()
        if require_name and not name:
            return None, (jsonify({"error": "name is required"}), 400)
        out["name"] = name
    for f in ("email", "role", "department"):
        if f in data:
            out[f] = (data.get(f) or "").strip()
    if "approval_limit_usd" in data:
        try:
            limit = float(data["approval_limit_usd"])
        except (TypeError, ValueError):
            return None, (jsonify({"error": "approval_limit_usd must be a number"}), 400)
        if limit < 0:
            return None, (jsonify({"error": "approval_limit_usd must be ≥ 0"}), 400)
        out["approval_limit_usd"] = limit
    return out, None


@app.get("/api/employees")
def list_employees():
    with db() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM employees ORDER BY id").fetchall()]
    return jsonify(rows)


@app.post("/api/employees")
def create_employee():
    data = request.get_json(force=True)
    fields, err = _clean_employee_payload(data, require_name=True)
    if err:
        return err
    with db() as conn:
        emp_id = allocate_employee_id(conn)
        conn.execute(
            "INSERT INTO employees (id, name, email, role, department, approval_limit_usd)"
            " VALUES (?,?,?,?,?,?)",
            (emp_id, fields.get("name"), fields.get("email"), fields.get("role"),
             fields.get("department"), fields.get("approval_limit_usd", 0)),
        )
        row = dict(conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone())
    return jsonify(row), 201


@app.patch("/api/employees/<emp_id>")
def update_employee(emp_id):
    data = request.get_json(force=True)
    fields, err = _clean_employee_payload(data, require_name=False)
    if err:
        return err
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    with db() as conn:
        if not conn.execute("SELECT 1 FROM employees WHERE id=?", (emp_id,)).fetchone():
            return jsonify({"error": "not found"}), 404
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE employees SET {sets} WHERE id=?", (*fields.values(), emp_id))
        row = dict(conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone())
    return jsonify(row)


@app.delete("/api/employees/<emp_id>")
def delete_employee(emp_id):
    with db() as conn:
        used = conn.execute(
            "SELECT COUNT(*) FROM purchase_requests WHERE employee_id=?", (emp_id,)).fetchone()[0]
        if used:
            return jsonify({"error": "persona has requests on the board"}), 409
        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    return jsonify({"ok": True})


@app.get("/api/settings")
def get_settings():
    try:
        clp_per_usd = float(get_setting("clp_per_usd"))
    except (TypeError, ValueError):
        clp_per_usd = None
    return jsonify({"clp_per_usd": clp_per_usd})


@app.patch("/api/settings")
def patch_settings():
    data = request.get_json(force=True)
    if "clp_per_usd" in data:
        try:
            clp_per_usd = float(data["clp_per_usd"])
        except (TypeError, ValueError):
            return jsonify({"error": "clp_per_usd must be a number"}), 400
        if clp_per_usd <= 0:
            return jsonify({"error": "clp_per_usd must be greater than zero"}), 400
        set_setting("clp_per_usd", clp_per_usd)
    return get_settings()


@app.get("/api/catalog")
def list_catalog():
    """Read-only — products are backend-controlled (bundled with the deployment)."""
    with db() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, sku, name, description, category, unit, unit_price_usd"
            " FROM catalog_items ORDER BY category, name").fetchall()]
    return jsonify(rows)


@app.get("/api/suppliers")
def list_suppliers():
    """Read-only — suppliers are backend-controlled (bundled with the deployment)."""
    with db() as conn:
        rows = conn.execute("SELECT data_json FROM suppliers ORDER BY name").fetchall()
    return jsonify([json.loads(r["data_json"]) for r in rows])


init_db()
amp.start_watchdog()

if __name__ == "__main__":
    app.run(port=5001)
