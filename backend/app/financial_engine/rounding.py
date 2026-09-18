"""Single rounding convention for the whole financial_engine (architecture.md §4):
internal figures are quantized to 4dp with ROUND_HALF_UP, matching NUMERIC(14,4) columns
exactly (D-019). Currency display rounding (e.g. 2dp for GMD) is a presentation-layer concern,
not something this package decides.
"""
from decimal import ROUND_HALF_UP, Decimal

QUANTIZE_4DP = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(QUANTIZE_4DP, rounding=ROUND_HALF_UP)
