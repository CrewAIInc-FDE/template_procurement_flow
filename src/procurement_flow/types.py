from pydantic import BaseModel, Field


class LineItem(BaseModel):
    request_item_id: int | None = None
    catalog_item_id: str
    sku: str = ""
    name: str = ""
    quantity: int
    unit_price_usd: float
    line_total_usd: float


class RequestDraft(BaseModel):
    """Structured purchase request extracted from the employee's message."""

    line_items: list[LineItem]
    justification: str
    urgency: str  # low | normal | high
    unmatched: list[str]
    estimated_total_usd: float
    detected_language: str


class ScreeningResult(BaseModel):
    verdict: str  # pass | flag | reject
    violations: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    reasoning: str


class ExtractedQuote(BaseModel):
    """One supplier quote line extracted from an email body or PDF."""

    quote_id: str
    supplier_id: str = ""
    supplier_name: str
    request_item_id: int
    unit_price: float
    currency: str
    delivery_days: int
    received_at: str
    message_id: str
    source: str = "email"
    risk_notes: list[str] = Field(default_factory=list)


class QuoteCollection(BaseModel):
    quotes: list[ExtractedQuote] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QuoteOption(BaseModel):
    quote_id: str
    supplier_id: str
    supplier_name: str
    request_item_id: int
    unit_price: float
    currency: str
    normalized_unit_price_usd: float
    line_total: float
    line_total_usd: float
    delivery_days: int
    price_score: float
    delivery_score: float
    total_score: float
    is_cheapest: bool
    is_fastest: bool
    received_at: str
    message_id: str
    source: str
    risk_notes: list[str] = Field(default_factory=list)


class QuoteReviewLine(BaseModel):
    request_item_id: int
    catalog_item_id: str
    sku: str = ""
    item_name: str
    quantity: int
    suggested_quote_id: str
    options: list[QuoteOption]


class QuoteReview(BaseModel):
    pr_number: str
    clp_per_usd: float
    lines: list[QuoteReviewLine] = Field(default_factory=list)
    uncovered_item_ids: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AwardSelection(BaseModel):
    request_item_id: int
    quote_id: str


class AwardedItem(BaseModel):
    request_item_id: int
    catalog_item_id: str
    sku: str = ""
    item_name: str
    quantity: int
    quote_id: str
    supplier_id: str
    supplier_name: str
    unit_price: float
    currency: str
    line_total: float
    line_total_usd: float
    delivery_days: int
    risk_notes: list[str] = Field(default_factory=list)


class PurchaseOrderDocument(BaseModel):
    po_number: str
    pr_number: str
    supplier_id: str
    supplier_name: str
    total_usd: float
    item_ids: list[int]
    items: list[AwardedItem]
    markdown: str
