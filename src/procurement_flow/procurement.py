"""Deterministic quote scoring, award validation, and PO rendering."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Iterable

from procurement_flow.types import (
    AwardedItem,
    AwardSelection,
    ExtractedQuote,
    PurchaseOrderDocument,
    QuoteOption,
    QuoteReview,
    QuoteReviewLine,
)

SUPPORTED_CURRENCIES = {"USD", "CLP"}


def _supplier_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"email:{slug or 'unknown'}"


def _supplier_risks(supplier: dict | None) -> list[str]:
    if not supplier:
        return ["Supplier is not present in the approved supplier directory."]
    notes = []
    on_time = supplier.get("on_time_delivery_rate")
    if isinstance(on_time, (int, float)) and on_time < 0.9:
        notes.append(f"Historical on-time delivery rate is {on_time * 100:.0f}%.")
    incidents = supplier.get("quality_incidents_last_24m") or 0
    if incidents:
        notes.append(f"{incidents} quality incident(s) recorded in the last 24 months.")
    disputes = supplier.get("open_disputes") or 0
    if disputes:
        notes.append(f"{disputes} open supplier dispute(s).")
    if not supplier.get("certifications"):
        notes.append("No supplier certifications are recorded.")
    return notes


def build_quote_review(
    pr_number: str,
    request_items: list[dict],
    quotes: Iterable[ExtractedQuote | dict],
    clp_per_usd: float,
    suppliers: list[dict] | None = None,
    warnings: list[str] | None = None,
) -> QuoteReview:
    """Score complete quote lines 50/50 on price and delivery, per item."""
    if clp_per_usd <= 0:
        raise ValueError("clp_per_usd must be greater than zero")

    review_warnings = list(warnings or [])
    items = {int(item["request_item_id"]): item for item in request_items}
    suppliers = suppliers or []
    suppliers_by_id = {str(s["id"]): s for s in suppliers}
    suppliers_by_name = {str(s.get("name", "")).casefold(): s for s in suppliers}
    latest: dict[tuple[int, str], ExtractedQuote] = {}

    for raw in quotes:
        try:
            quote = raw if isinstance(raw, ExtractedQuote) else ExtractedQuote.model_validate(raw)
        except Exception as exc:
            review_warnings.append(f"Ignored an invalid quote line: {exc}")
            continue
        item = items.get(quote.request_item_id)
        currency = quote.currency.upper().strip()
        if item is None:
            review_warnings.append(
                f"Quote {quote.quote_id} references unknown or already-awarded item {quote.request_item_id}."
            )
            continue
        if quote.unit_price <= 0 or quote.delivery_days < 1 or currency not in SUPPORTED_CURRENCIES:
            review_warnings.append(
                f"Quote {quote.quote_id} is unscorable: price must be positive, delivery at least one day, and currency USD or CLP."
            )
            continue
        quote.currency = currency
        supplier = suppliers_by_id.get(quote.supplier_id) or suppliers_by_name.get(
            quote.supplier_name.casefold()
        )
        quote.supplier_id = (
            str(supplier["id"])
            if supplier
            else quote.supplier_id or _supplier_id(quote.supplier_name)
        )
        quote.risk_notes = list(dict.fromkeys([*quote.risk_notes, *_supplier_risks(supplier)]))

        key = (quote.request_item_id, quote.supplier_id)
        previous = latest.get(key)
        if previous is None or (quote.received_at, quote.quote_id) > (
            previous.received_at,
            previous.quote_id,
        ):
            if previous is not None:
                review_warnings.append(
                    f"Discarded older revision {previous.quote_id}; {quote.quote_id} is the latest quote from {quote.supplier_name}."
                )
            latest[key] = quote
        else:
            review_warnings.append(
                f"Discarded older revision {quote.quote_id}; {previous.quote_id} is the latest quote from {quote.supplier_name}."
            )

    grouped: dict[int, list[tuple[ExtractedQuote, float, float, float]]] = defaultdict(list)
    for quote in latest.values():
        quantity = int(items[quote.request_item_id]["quantity"])
        unit_usd = quote.unit_price if quote.currency == "USD" else quote.unit_price / clp_per_usd
        line_total = quote.unit_price * quantity
        grouped[quote.request_item_id].append((quote, unit_usd, line_total, unit_usd * quantity))

    lines = []
    uncovered = []
    for item_id, item in items.items():
        candidates = grouped.get(item_id, [])
        if not candidates:
            uncovered.append(item_id)
            continue
        cheapest = min(c[3] for c in candidates)
        fastest = min(c[0].delivery_days for c in candidates)
        options = []
        for quote, unit_usd, line_total, line_total_usd in candidates:
            price_score = 100 * cheapest / line_total_usd
            delivery_score = 100 * fastest / quote.delivery_days
            options.append(
                QuoteOption(
                    quote_id=quote.quote_id,
                    supplier_id=quote.supplier_id,
                    supplier_name=quote.supplier_name,
                    request_item_id=item_id,
                    unit_price=round(quote.unit_price, 2),
                    currency=quote.currency,
                    normalized_unit_price_usd=round(unit_usd, 2),
                    line_total=round(line_total, 2),
                    line_total_usd=round(line_total_usd, 2),
                    delivery_days=quote.delivery_days,
                    price_score=round(price_score, 1),
                    delivery_score=round(delivery_score, 1),
                    total_score=round((price_score + delivery_score) / 2, 1),
                    is_cheapest=line_total_usd == cheapest,
                    is_fastest=quote.delivery_days == fastest,
                    received_at=quote.received_at,
                    message_id=quote.message_id,
                    source=quote.source,
                    risk_notes=quote.risk_notes,
                )
            )
        options.sort(
            key=lambda o: (
                -o.total_score,
                o.line_total_usd,
                o.delivery_days,
                o.supplier_name.casefold(),
                o.quote_id,
            )
        )
        lines.append(
            QuoteReviewLine(
                request_item_id=item_id,
                catalog_item_id=str(item.get("catalog_item_id", "")),
                sku=str(item.get("sku", "")),
                item_name=str(item.get("name") or item.get("item_name") or item_id),
                quantity=int(item["quantity"]),
                suggested_quote_id=options[0].quote_id,
                options=options,
            )
        )

    return QuoteReview(
        pr_number=pr_number,
        clp_per_usd=clp_per_usd,
        lines=lines,
        uncovered_item_ids=uncovered,
        warnings=list(dict.fromkeys(review_warnings)),
    )


def validate_awards(
    review: QuoteReview | dict,
    awards: Iterable[AwardSelection | dict] | None,
    already_awarded_item_ids: Iterable[int] = (),
) -> list[AwardSelection]:
    review = review if isinstance(review, QuoteReview) else QuoteReview.model_validate(review)
    blocked = {int(i) for i in already_awarded_item_ids}
    raw_awards = list(awards or [])
    if not raw_awards:
        raw_awards = [
            {"request_item_id": line.request_item_id, "quote_id": line.suggested_quote_id}
            for line in review.lines
        ]
    selections = [
        a if isinstance(a, AwardSelection) else AwardSelection.model_validate(a)
        for a in raw_awards
    ]
    if len(selections) != len(review.lines):
        raise ValueError("exactly one award is required for every covered item")
    by_item = {line.request_item_id: line for line in review.lines}
    seen = set()
    for selection in selections:
        if selection.request_item_id in blocked:
            raise ValueError(f"item {selection.request_item_id} is already awarded")
        line = by_item.get(selection.request_item_id)
        if line is None:
            raise ValueError(f"item {selection.request_item_id} is not in this quote review")
        if selection.request_item_id in seen:
            raise ValueError(f"item {selection.request_item_id} has more than one award")
        if selection.quote_id not in {o.quote_id for o in line.options}:
            raise ValueError(
                f"quote {selection.quote_id} does not belong to item {selection.request_item_id}"
            )
        seen.add(selection.request_item_id)
    return sorted(selections, key=lambda a: a.request_item_id)


def parse_award_feedback(feedback: str, review: QuoteReview | dict) -> tuple[str, list[AwardSelection]]:
    """Accept portal JSON; plain AMP approval uses the suggested selections."""
    text = (feedback or "").strip()
    if text.casefold() in {"approved", "approve", "yes"}:
        return "approved", validate_awards(review, None)
    if text.casefold() in {"rejected", "reject", "no"}:
        return "rejected", []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("feedback must be approved/rejected or valid award JSON") from exc
    decision = str(payload.get("decision", "")).casefold()
    if decision == "rejected":
        return decision, []
    if decision != "approved":
        raise ValueError("feedback decision must be approved or rejected")
    return decision, validate_awards(review, payload.get("awards"))


def materialize_awards(
    review: QuoteReview | dict, selections: Iterable[AwardSelection | dict]
) -> list[AwardedItem]:
    review = review if isinstance(review, QuoteReview) else QuoteReview.model_validate(review)
    selections = validate_awards(review, selections)
    lines = {line.request_item_id: line for line in review.lines}
    awarded = []
    for selection in selections:
        line = lines[selection.request_item_id]
        option = next(o for o in line.options if o.quote_id == selection.quote_id)
        awarded.append(
            AwardedItem(
                request_item_id=line.request_item_id,
                catalog_item_id=line.catalog_item_id,
                sku=line.sku,
                item_name=line.item_name,
                quantity=line.quantity,
                quote_id=option.quote_id,
                supplier_id=option.supplier_id,
                supplier_name=option.supplier_name,
                unit_price=option.unit_price,
                currency=option.currency,
                line_total=option.line_total,
                line_total_usd=option.line_total_usd,
                delivery_days=option.delivery_days,
                risk_notes=option.risk_notes,
            )
        )
    return awarded


def generate_purchase_orders(
    pr_number: str,
    existing_awards: Iterable[AwardedItem | dict],
    new_awards: Iterable[AwardedItem | dict],
    existing_purchase_orders: Iterable[dict],
    clp_per_usd: float,
) -> list[PurchaseOrderDocument]:
    """Return one stable internal-draft PO per supplier across award cycles."""
    by_item: dict[int, AwardedItem] = {}
    for raw in [*existing_awards, *new_awards]:
        item = raw if isinstance(raw, AwardedItem) else AwardedItem.model_validate(raw)
        by_item[item.request_item_id] = item

    existing_numbers = {
        str(po["supplier_id"]): str(po["po_number"]) for po in existing_purchase_orders
    }
    used_suffixes = []
    for number in existing_numbers.values():
        match = re.search(r"-(\d+)$", number)
        if match:
            used_suffixes.append(int(match.group(1)))
    next_suffix = max(used_suffixes, default=0) + 1

    grouped: dict[str, list[AwardedItem]] = defaultdict(list)
    for item in by_item.values():
        grouped[item.supplier_id].append(item)

    documents = []
    for supplier_id in sorted(
        grouped, key=lambda sid: (grouped[sid][0].supplier_name.casefold(), sid)
    ):
        items = sorted(grouped[supplier_id], key=lambda i: i.request_item_id)
        po_number = existing_numbers.get(supplier_id)
        if not po_number:
            po_number = f"{pr_number.replace('PR-', 'PO-')}-{next_suffix:02d}"
            existing_numbers[supplier_id] = po_number
            next_suffix += 1
        totals = defaultdict(float)
        for item in items:
            totals[item.currency] += item.line_total
        total_usd = round(sum(item.line_total_usd for item in items), 2)
        rows = "\n".join(
            "| {name} | {qty} | {unit:,.2f} {currency} | {line:,.2f} {currency} | "
            "{usd:,.2f} USD | {days} days | {quote} |".format(
                name=item.item_name.replace("|", "/"),
                qty=item.quantity,
                unit=item.unit_price,
                currency=item.currency,
                line=item.line_total,
                usd=item.line_total_usd,
                days=item.delivery_days,
                quote=item.quote_id.replace("|", "/"),
            )
            for item in items
        )
        subtotal_lines = "\n".join(
            f"- **{currency} subtotal:** {amount:,.2f} {currency}"
            for currency, amount in sorted(totals.items())
        )
        markdown = (
            f"# Purchase Order {po_number}\n\n"
            "> **INTERNAL DRAFT — not sent to supplier**\n\n"
            f"- **Purchase request:** {pr_number}\n"
            f"- **Supplier:** {items[0].supplier_name}\n"
            f"- **Supplier ID:** {supplier_id}\n"
            f"- **Comparison FX:** {clp_per_usd:,.2f} CLP per USD\n\n"
            "| Item | Qty | Unit price | Line total | USD equivalent | Delivery | Quote |\n"
            "|---|---:|---:|---:|---:|---:|---|\n"
            f"{rows}\n\n"
            "## Totals\n\n"
            f"{subtotal_lines}\n"
            f"- **USD equivalent total:** {total_usd:,.2f} USD\n\n"
            "Prices and delivery terms are snapshots of the approved supplier quotes."
        )
        documents.append(
            PurchaseOrderDocument(
                po_number=po_number,
                pr_number=pr_number,
                supplier_id=supplier_id,
                supplier_name=items[0].supplier_name,
                total_usd=total_usd,
                item_ids=[item.request_item_id for item in items],
                items=items,
                markdown=markdown,
            )
        )
    return documents
