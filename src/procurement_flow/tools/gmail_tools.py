"""Composio Gmail helpers and read-only PDF attachment tool."""

import base64
import io
import json
import os
import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import pdfplumber
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

GMAIL_FETCH_EMAILS = "GMAIL_FETCH_EMAILS"
GMAIL_FETCH_MESSAGE = "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID"
GMAIL_GET_ATTACHMENT = "GMAIL_GET_ATTACHMENT"
GMAIL_SEND_EMAIL = "GMAIL_SEND_EMAIL"


class GmailPdfAttachmentInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID containing the PDF")
    attachment_id: str = Field(..., description="Gmail attachment ID from get_message")
    file_name: str = Field(default="quote.pdf", description="PDF attachment filename")


@cache
def _composio():
    api_key = os.getenv("COMPOSIO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is missing")
    os.environ.setdefault(
        "COMPOSIO_CACHE_DIR", str(Path(tempfile.gettempdir()) / "composio-cache")
    )
    from composio import Composio
    from composio_crewai import CrewAIProvider

    return Composio(
        api_key=api_key,
        provider=CrewAIProvider(),
        toolkit_versions={
            "gmail": os.getenv("COMPOSIO_GMAIL_TOOLKIT_VERSION", "20260702_01")
        },
    )


def _composio_user_id() -> str:
    user_id = os.getenv("COMPOSIO_USER_ID", "").strip()
    if not user_id:
        raise RuntimeError("COMPOSIO_USER_ID is missing")
    return user_id


def composio_file_client(upload_dir: str | Path):
    """Return a direct Composio client restricted to one temporary PO directory."""
    upload_path = Path(upload_dir).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if upload_path.parent != temp_root or not upload_path.name.startswith("procurement-po-"):
        raise RuntimeError("PO attachment directory is outside the approved temporary path")
    api_key = os.getenv("COMPOSIO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is missing")
    os.environ.setdefault("COMPOSIO_CACHE_DIR", str(temp_root / "composio-cache"))
    from composio import Composio
    from composio_crewai import CrewAIProvider

    return Composio(
        api_key=api_key,
        provider=CrewAIProvider(),
        toolkit_versions={
            "gmail": os.getenv("COMPOSIO_GMAIL_TOOLKIT_VERSION", "20260702_01")
        },
        dangerously_allow_auto_upload_download_files=True,
        file_upload_dirs=[str(upload_path)],
    )


def composio_attachment_client(download_dir: str | Path):
    """Return a Composio client restricted to one temporary quote directory."""
    download_path = Path(download_dir).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (
        download_path.parent != temp_root
        or not download_path.name.startswith("procurement-quote-")
    ):
        raise RuntimeError("Quote attachment directory is outside the approved temporary path")
    api_key = os.getenv("COMPOSIO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is missing")
    os.environ.setdefault("COMPOSIO_CACHE_DIR", str(temp_root / "composio-cache"))
    from composio import Composio
    from composio_crewai import CrewAIProvider

    return Composio(
        api_key=api_key,
        provider=CrewAIProvider(),
        toolkit_versions={
            "gmail": os.getenv("COMPOSIO_GMAIL_TOOLKIT_VERSION", "20260702_01")
        },
        dangerously_allow_auto_upload_download_files=True,
        file_download_dir=str(download_path),
        file_upload_dirs=False,
    )


def run_composio_action(action_name: str, *, client=None, **arguments: Any) -> dict:
    """Execute one Gmail action for the configured Composio user."""
    result = (client or _composio()).tools.execute(
        action_name,
        arguments=arguments,
        user_id=_composio_user_id(),
    )
    if not result.get("successful"):
        raise RuntimeError(
            f"Composio action {action_name} failed: {result.get('error') or 'unknown error'}"
        )
    data = result.get("data")
    return data if isinstance(data, dict) else {"data": data}


@cache
def gmail_quote_tools() -> list[BaseTool]:
    """Return only the Gmail read tools used by the quote analyst."""
    return _composio().tools.get(
        user_id=_composio_user_id(),
        tools=[GMAIL_FETCH_EMAILS, GMAIL_FETCH_MESSAGE],
    )


@cache
def gmail_dispatch_tools() -> list[BaseTool]:
    """Return only the Gmail tools used by the sourcing dispatch task."""
    return _composio().tools.get(
        user_id=_composio_user_id(),
        tools=[GMAIL_FETCH_EMAILS, GMAIL_SEND_EMAIL],
    )


def find_message_ref(value: Any) -> tuple[str, str]:
    """Find a Gmail message ID and its optional thread ID in a tool response."""
    if isinstance(value, dict):
        message_id = value.get("messageId") or value.get("message_id") or value.get("id")
        thread_id = value.get("threadId") or value.get("thread_id") or ""
        if message_id:
            return str(message_id), str(thread_id)
        for child in value.values():
            found = find_message_ref(child)
            if found[0]:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_message_ref(child)
            if found[0]:
                return found
    return "", ""


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


def _find_downloaded_pdf(value: Any, download_dir: Path) -> Path | None:
    if isinstance(value, str):
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = download_dir / candidate
        candidate = candidate.resolve()
        if (
            candidate.is_relative_to(download_dir)
            and candidate.is_file()
            and candidate.suffix.lower() == ".pdf"
        ):
            return candidate
    elif isinstance(value, dict):
        for child in value.values():
            found = _find_downloaded_pdf(child, download_dir)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_downloaded_pdf(child, download_dir)
            if found:
                return found
    return None


def extract_pdf_text(payload: str, download_dir: str | Path | None = None) -> str:
    """Decode a Gmail attachment response and return text or a safe warning."""
    try:
        body = json.loads(payload)
        downloaded_pdf = (
            _find_downloaded_pdf(body, Path(download_dir).resolve())
            if download_dir
            else None
        )
        if downloaded_pdf:
            with pdfplumber.open(downloaded_pdf) as pdf:
                text = "\n\n".join(
                    (page.extract_text() or "").strip() for page in pdf.pages
                ).strip()
            if not text:
                return "WARNING: PDF is scanned or has no extractable text; OCR is not enabled."
            return text[:60000]
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
        "Use only for PDF attachments whose IDs came from "
        "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID."
    )
    args_schema: type[BaseModel] = GmailPdfAttachmentInput

    def _run(
        self, message_id: str, attachment_id: str, file_name: str = "quote.pdf"
    ) -> str:
        try:
            with tempfile.TemporaryDirectory(prefix="procurement-quote-") as download_dir:
                payload = run_composio_action(
                    GMAIL_GET_ATTACHMENT,
                    client=composio_attachment_client(download_dir),
                    user_id="me",
                    message_id=message_id,
                    attachment_id=attachment_id,
                    file_name=file_name,
                )
                return extract_pdf_text(json.dumps(payload), download_dir)
        except RuntimeError as exc:
            return f"WARNING: {exc}"
