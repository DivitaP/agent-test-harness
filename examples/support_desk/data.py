"""The deliberately fictional order corpus and refund policy for the demo."""

ORDERS: dict[str, dict[str, object]] = {
    "4412": {
        "item": "brass table lamp",
        "amount": 68.00,
        "status": "delivered",
        "condition": "damaged",
        "delivered_date": "2026-07-10",
    },
    "7810": {
        "item": "wool throw blanket",
        "amount": 42.50,
        "status": "delivered",
        "condition": "fine",
        "delivered_date": "2026-07-12",
    },
    "9925": {
        "item": "ceramic vase set",
        "amount": 55.00,
        "status": "in-transit",
        "condition": "unknown",
        "estimated_delivery": "2026-07-23",
    },
}

REFUND_POLICY = (
    "Refund policy RP-7: delivered items reported damaged within 30 days of delivery "
    "qualify for a full refund. Delivered items that are not damaged qualify for "
    "store credit only within 14 days of delivery. In-transit orders cannot be "
    "refunded until they are delivered. Refunds take 5 to 7 business days; no "
    "other timeline may be promised."
)
