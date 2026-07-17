from pydantic import BaseModel


class LineItem(BaseModel):
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
    unmatched: list[str]  # descriptors we couldn't map to catalog items
    estimated_total_usd: float
    detected_language: str  # ISO code of the message language (es, en, pt, ...)


class ScreeningResult(BaseModel):
    verdict: str  # pass | flag | reject
    violations: list[str]
    anomalies: list[str]
    reasoning: str


class SourcingRecommendation(BaseModel):
    recommended_supplier: str
    total_cost_usd: float
    runner_up: str
    key_risks: list[str]
    rationale: str
    confidence: str  # high | medium | low
