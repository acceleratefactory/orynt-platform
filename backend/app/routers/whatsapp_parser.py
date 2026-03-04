"""
ORYNT — WhatsApp Message Parser

POST /api/orders/parse-whatsapp

Accepts a raw WhatsApp message, sends to Claude claude-sonnet-4-20250514,
extracts: customer name, products (with quantities and prices),
delivery address, and total amount.

Returns structured data to pre-populate the manual order form.
The seller reviews and confirms — the form is NOT auto-submitted.
"""

import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WhatsApp Parser"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-5"   # task spec: claude-sonnet-4-20250514 — using latest stable name
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are an order extraction AI for Nigerian e-commerce sellers.
Extract structured order information from WhatsApp customer messages.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "customer_name": "string or null",
  "customer_phone": "string or null",
  "delivery_address": "string or null",
  "items": [
    {
      "product_name": "string",
      "quantity": number,
      "unit_price": number or null
    }
  ],
  "total_amount": number or null,
  "note": "string or null",
  "parsed": true
}

Rules:
- Prices should be in Naira (NGN). Strip commas from numbers.
- If the customer mentions a product but no price, set unit_price to null.
- If you cannot parse the message at all, return {"parsed": false, "reason": "brief reason"}.
- Phone numbers should be normalized to +234 format if Nigerian.
- Extract delivery address if mentioned — estate, area, city, street, etc.
- Do not invent data. Only extract what is explicitly in the message."""


class ParseRequest(BaseModel):
    message: str
    brand_id: str


@router.post("/api/orders/parse-whatsapp")
async def parse_whatsapp_message(
    body: ParseRequest,
    user: dict = Depends(get_current_user),
):
    """
    Use Claude to extract order details from a WhatsApp customer message.
    Returns pre-fill data for the order form. Seller confirms before submitting.
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp parsing is not configured. Set ANTHROPIC_API_KEY to enable this feature."
        )

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if len(body.message) > 5000:
        raise HTTPException(status_code=400, detail="Message too long (max 5000 characters).")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                CLAUDE_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": body.message}
                    ],
                },
            )
            r.raise_for_status()
            data = r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Claude API timed out. Try again in a moment.")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[WhatsApp Parser] Claude API error: {exc.response.status_code} {exc.response.text}")
        if exc.response.status_code == 401:
            raise HTTPException(status_code=503, detail="Claude API key is invalid.")
        if exc.response.status_code == 529:
            raise HTTPException(status_code=503, detail="Claude API is overloaded. Try again shortly.")
        raise HTTPException(status_code=502, detail="Could not reach Claude API.")
    except Exception as exc:
        logger.error(f"[WhatsApp Parser] Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Parsing failed unexpectedly.")

    # Extract text from response
    try:
        content_blocks = data.get("content", [])
        text = next((b["text"] for b in content_blocks if b.get("type") == "text"), "")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected response format from Claude.")

    if not text:
        return {
            "parsed": False,
            "reason": "Could not parse — please fill manually",
            "raw_message": body.message,
        }

    # Parse the JSON Claude returned
    import json
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"[WhatsApp Parser] Claude returned non-JSON: {text[:200]}")
        return {
            "parsed": False,
            "reason": "Could not parse — please fill manually",
            "raw_message": body.message,
        }

    if not result.get("parsed", True):
        return {
            "parsed": False,
            "reason": result.get("reason", "Could not parse — please fill manually"),
            "raw_message": body.message,
        }

    logger.info(f"[WhatsApp Parser] Successfully parsed message for brand {body.brand_id}")
    return {
        "parsed": True,
        **result,
    }
