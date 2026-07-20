"""AMP transport: kickoff/status/wakeup, plus a local in-process fallback and
the status-polling watchdog.

The watchdog is NOT a nicety: while quote review is paused on AMP's
@human_feedback gate, polling GET /status remains the fallback for dropped
flow/HITL webhooks. Do not remove.
"""

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

import requests

from db import db, now

log = logging.getLogger("amp")

DEPLOYMENT_URL = os.environ.get("DEPLOYMENT_URL", "").rstrip("/")
DEPLOYMENT_KEY = os.environ.get("DEPLOYMENT_KEY", "")
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

WEBHOOK_EVENTS = ["flow_started", "tool_usage_started", "tool_usage_finished", "flow_finished"]

_auth = {"Authorization": f"Bearer {DEPLOYMENT_KEY}"}


def wakeup():
    """GET /inputs doubles as a wakeup ping — deployments sleep."""
    if not DEPLOYMENT_URL:
        return
    try:
        requests.get(f"{DEPLOYMENT_URL}/inputs", headers=_auth, timeout=30)
    except requests.RequestException as e:
        log.warning("wakeup ping failed: %s", e)


def start_kickoff(pr_number, mode, inputs):
    """Fire a kickoff (AMP or local in-process) and record it. Returns kickoff_id."""
    if DEPLOYMENT_URL:
        body = {"inputs": inputs}
        if PUBLIC_BASE_URL and WEBHOOK_TOKEN:
            body["webhooks"] = {
                "events": WEBHOOK_EVENTS,
                "url": f"{PUBLIC_BASE_URL}/api/webhook/{pr_number}",
                "realtime": True,
                "authentication": {"strategy": "bearer", "token": WEBHOOK_TOKEN},
            }
        resp = requests.post(f"{DEPLOYMENT_URL}/kickoff", json=body, headers=_auth, timeout=60)
        resp.raise_for_status()
        kickoff_id = resp.json()["kickoff_id"]
    else:
        kickoff_id = f"local-{uuid.uuid4()}"

    with db() as conn:
        conn.execute(
            "INSERT INTO kickoffs (kickoff_id, pr_number, mode, state, created_at, updated_at)"
            " VALUES (?,?,?, 'pending', ?, ?)",
            (kickoff_id, pr_number, mode, now(), now()),
        )

    if not DEPLOYMENT_URL:
        threading.Thread(
            target=_run_local, args=(pr_number, kickoff_id, mode, inputs), daemon=True
        ).start()
    return kickoff_id


def _run_local(pr_number, kickoff_id, mode, inputs):
    """Local dev without AMP: run ProcurementFlow in-process (needs OPENAI_API_KEY).

    Quote review BLOCKS here on a console approved/rejected prompt —
    the HITL webhook/board-button channel only exists on AMP.
    """
    from app import process_envelope  # late import — app imports us at module load

    try:
        try:
            from procurement_flow.main import ProcurementFlow
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from procurement_flow.main import ProcurementFlow

        log.warning("[local] %s kickoff for %s — quote approval blocks on a console prompt "
                    "in THIS terminal", mode, pr_number)
        flow = ProcurementFlow()
        flow.kickoff(inputs=inputs)
        envelope = flow.state.model_dump(mode="json")
        process_envelope(pr_number, kickoff_id, envelope)
    except Exception:
        log.exception("[local] kickoff failed for %s", pr_number)


def parse_result(payload):
    """Defensively pull the result envelope out of a webhook/status payload."""
    if payload is None:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return None
    if not isinstance(payload, dict):
        return None
    if "final_status" in payload:
        return payload
    for key in ("result", "data", "output"):
        found = parse_result(payload.get(key))
        if found:
            return found
    return None


def poll_status(kickoff_id):
    resp = requests.get(f"{DEPLOYMENT_URL}/status/{kickoff_id}", headers=_auth, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _watchdog_loop():
    from app import process_envelope  # late import

    while True:
        time.sleep(10)
        try:
            with db() as conn:
                rows = conn.execute(
                    "SELECT kickoff_id, pr_number FROM kickoffs WHERE state='pending'"
                ).fetchall()
            for row in rows:
                kid = row["kickoff_id"]
                if kid.startswith(("local-", "fixture-")):
                    continue
                try:
                    envelope = parse_result(poll_status(kid))
                    if envelope:
                        process_envelope(row["pr_number"], kid, envelope)
                except requests.RequestException as e:
                    log.warning("status poll failed for %s: %s", kid, e)
        except Exception:
            log.exception("watchdog iteration failed")


def start_watchdog():
    if DEPLOYMENT_URL:
        threading.Thread(target=_watchdog_loop, daemon=True).start()
        log.info("watchdog polling started")
