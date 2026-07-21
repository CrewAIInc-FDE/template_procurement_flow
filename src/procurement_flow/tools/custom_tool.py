"""AMP Gmail action helper and read-only PDF attachment tool."""

import base64
import io
import json
from functools import cache
from typing import Any

import pdfplumber
from crewai.tools import BaseTool
from crewai_tools import CrewaiPlatformTools
from pydantic import BaseModel, Field


class GmailPdfAttachmentInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID containing the PDF")
    attachment_id: str = Field(..., description="Gmail attachment ID from get_message")


@cache
def _platform_action(action_name: str):
    tools = CrewaiPlatformTools(apps=[action_name])
    action = next(
        (tool for tool in tools if getattr(tool, "action_name", "") == action_name),
        None,
    )
    if action is None:
        raise RuntimeError(f"AMP integration action is unavailable: {action_name}")
    return action


def run_platform_action(action_name: str, **kwargs: Any) -> dict:
    """Run one named AMP integration action and return its JSON response."""
    action = _platform_action(action_name)
    payload = action._run(**kwargs)
    if payload.startswith(("API request failed:", "Error executing action")):
        raise RuntimeError(payload)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AMP integration returned invalid JSON for {action_name}") from exc


def _find_base64_data(value: Any) -> str | None:
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, str) and len(data) > 20:
            return data
        for child in value.values():
            found = _find_base64_data(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_base64_data(child)
            if found:
                return found
    return None


def extract_pdf_text(payload: str) -> str:
    """Decode a Gmail attachment response and return text or a safe warning."""
    try:
        body = json.loads(payload)
        encoded = _find_base64_data(body)
        if not encoded:
            return "WARNING: Gmail returned no attachment data."
        padding = "=" * (-len(encoded) % 4)
        pdf_bytes = base64.urlsafe_b64decode(encoded + padding)
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n\n".join((page.extract_text() or "").strip() for page in pdf.pages).strip()
        if not text:
            return "WARNING: PDF is scanned or has no extractable text; OCR is not enabled."
        return text[:60000]
    except Exception as exc:
        return f"WARNING: Could not read PDF attachment: {exc}"


class ReadGmailPdfAttachmentTool(BaseTool):
    name: str = "read_gmail_pdf_attachment"
    description: str = (
        "Read text from a PDF attachment in an already-fetched Gmail message. "
        "Use only for PDF attachments whose message and attachment IDs came from gmail/get_message."
    )
    args_schema: type[BaseModel] = GmailPdfAttachmentInput

    def _run(self, message_id: str, attachment_id: str) -> str:
        try:
            payload = run_platform_action(
                "gmail/get_attachment", userId="me", messageId=message_id, id=attachment_id
            )
            return extract_pdf_text(json.dumps(payload))
        except RuntimeError as exc:
            return f"WARNING: {exc}"
