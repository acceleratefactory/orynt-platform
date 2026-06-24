"""
ORYNT — Data Canonicalisation Layer

Every record that enters ORYNT — order, product, customer, ad spend — must
pass through this module before being written to the database. This enforces
the Global Data Standards from the master implementation document.

Functions:
  - normalize_phone(raw_phone, country_hint=None) -> str
  - canonicalise_monetary(amount_original, currency_code, exchange_rate_api_key) -> dict
  - normalize_order_status(source_status) -> str
  - normalize_category(source_category) -> str
"""

import phonenumbers
import httpx
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical ORYNT product category list
# ---------------------------------------------------------------------------
CANONICAL_CATEGORIES = [
    "fashion-clothing",
    "fashion-footwear",
    "fashion-accessories",
    "beauty-skincare",
    "beauty-haircare",
    "beauty-makeup",
    "health-wellness",
    "food-beverages",
    "home-living",
    "electronics-gadgets",
    "electronics-accessories",
    "baby-kids",
    "sports-fitness",
    "books-education",
    "digital-products",
    "services",
    "other",
]

# ---------------------------------------------------------------------------
# ORYNT canonical order status mapping
# ---------------------------------------------------------------------------
ORDER_STATUS_MAP = {
    # Shopify
    "fulfilled": "completed",
    "unfulfilled": "pending",
    "partially_fulfilled": "processing",
    # Paystack / Flutterwave
    "success": "completed",
    "successful": "completed",
    "failed": "cancelled",
    "abandoned": "cancelled",
    # WooCommerce
    "wc-completed": "completed",
    "wc-processing": "processing",
    "wc-pending": "pending",
    "wc-cancelled": "cancelled",
    "wc-refunded": "refunded",
    "wc-on-hold": "pending",
    "wc-failed": "cancelled",
    # Preorder platform
    "active": "pending",
    "funded": "confirmed",
    "in_production": "processing",
    "shipped": "shipped",
    "customs": "in_transit",
    "warehouse": "in_transit",
    "delivering": "out_for_delivery",
    "completed": "completed",
    "cancelled": "cancelled",
    "refunded": "refunded",
    # Mono / bank transfer
    "pending_match": "pending_match",
    # Generic
    "paid": "completed",
    "confirmed": "confirmed",
    "pending": "pending",
    "processing": "processing",
}


def normalize_phone(raw_phone: str, country_hint: Optional[str] = None) -> str:
    """
    Normalize any phone number to E.164 international format.

    Args:
        raw_phone: The raw phone number string.
        country_hint: ISO 3166-1 alpha-2 code e.g. 'NG', 'GB', 'US', 'GH',
                      'ZA', 'AE'. When available from billing_address.country
                      or organisation.primary_country.

    Returns:
        E.164 formatted string (e.g. +2348012345678) or the raw string unchanged
        if parsing fails.
    """
    if not raw_phone or not raw_phone.strip():
        return raw_phone
    try:
        parsed = phonenumbers.parse(raw_phone, country_hint)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except Exception:
        pass
    return raw_phone  # Store raw rather than corrupt it


def get_usd_exchange_rate(currency_code: str, api_key: str) -> float:
    """
    Fetch current exchange rate: 1 [currency_code] = X USD.

    Uses ExchangeRate-API (v6). Returns 1.0 as fallback if the API call fails.
    """
    if not api_key:
        return 1.0
    if currency_code.upper() == "USD":
        return 1.0
    try:
        response = httpx.get(
            f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{currency_code}/USD",
            timeout=5.0,
        )
        data = response.json()
        if data.get("result") == "success":
            return float(data["conversion_rate"])
    except Exception:
        pass
    return 1.0  # Fallback — log this failure for monitoring


def canonicalise_monetary(
    amount_original: float, currency_code: str, exchange_rate_api_key: str = ""
):
    """
    Convert any monetary amount to amount_usd.

    Args:
        amount_original: The amount in the source currency.
        currency_code: ISO 4217 code (e.g. 'NGN', 'GBP', 'USD', 'EUR').
        exchange_rate_api_key: API key for ExchangeRate-API.

    Returns:
        dict with amount_original, original_currency, amount_usd, exchange_rate.
    """
    rate = get_usd_exchange_rate(currency_code, exchange_rate_api_key)
    return {
        "amount_original": amount_original,
        "original_currency": currency_code.upper(),
        "amount_usd": round(amount_original * rate, 6),
        "exchange_rate": rate,
    }


def normalize_order_status(source_status: str) -> str:
    """Map source platform order status to ORYNT canonical status."""
    if not source_status:
        return "pending"
    return ORDER_STATUS_MAP.get(source_status.lower().strip(), "pending")


def normalize_category(source_category: Optional[str]) -> str:
    """
    Map source platform product category to ORYNT canonical category.

    Uses direct match first, then keyword matching. Returns 'other' if no
    match is found.
    """
    if not source_category:
        return "other"
    source_lower = source_category.lower().strip()

    # Direct match
    if source_lower in CANONICAL_CATEGORIES:
        return source_lower

    # Keyword matching
    if any(k in source_lower for k in ["fashion", "cloth", "wear", "apparel", "dress", "shirt"]):
        return "fashion-clothing"
    if any(k in source_lower for k in ["shoe", "boot", "sandal", "footwear", "sneaker"]):
        return "fashion-footwear"
    if any(k in source_lower for k in ["bag", "accessory", "accessories", "jewel", "watch"]):
        return "fashion-accessories"
    if any(k in source_lower for k in ["skin", "cream", "lotion", "serum", "moistur"]):
        return "beauty-skincare"
    if any(k in source_lower for k in ["hair", "shampoo", "conditioner", "wig"]):
        return "beauty-haircare"
    if any(k in source_lower for k in ["makeup", "lipstick", "foundation", "cosmetic"]):
        return "beauty-makeup"
    if any(k in source_lower for k in ["food", "drink", "beverage", "snack", "juice"]):
        return "food-beverages"
    if any(k in source_lower for k in ["electronic", "phone", "gadget", "tech", "device"]):
        return "electronics-gadgets"
    if any(k in source_lower for k in ["health", "wellness", "supplement", "vitamin"]):
        return "health-wellness"
    if any(k in source_lower for k in ["home", "kitchen", "furniture", "decor", "sofa", "couch"]):
        return "home-living"
    if any(k in source_lower for k in ["baby", "kid", "child", "toy"]):
        return "baby-kids"
    if any(k in source_lower for k in ["sport", "gym", "fitness", "exercise", "dumbbell", "weight"]):
        return "sports-fitness"
    # Check digital-products BEFORE books-education so "ebook" doesn't match "book"
    if any(k in source_lower for k in ["digital", "software", "ebook", "download"]):
        return "digital-products"
    if any(k in source_lower for k in ["book", "course", "education", "learn"]):
        return "books-education"
    if any(k in source_lower for k in ["service", "consulting", "repair", "cleaning"]):
        return "services"
    return "other"
