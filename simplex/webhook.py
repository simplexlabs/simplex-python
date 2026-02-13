"""
Webhook verification for the Simplex SDK.

This module provides utilities to verify incoming Simplex webhook requests
using HMAC-SHA256 signature verification.
"""

from __future__ import annotations

import hashlib
import hmac


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


def verify_simplex_webhook(
    body: str,
    headers: dict[str, str],
    webhook_secret: str,
) -> None:
    """
    Verify a Simplex webhook request using HMAC-SHA256 signature verification.

    This function ensures that webhook requests are authentic and haven't been
    tampered with in transit.

    Args:
        body: Raw request body as a string (must be the original unparsed body)
        headers: Request headers dict containing the X-Simplex-Signature header
        webhook_secret: Your webhook secret from the Simplex dashboard

    Raises:
        WebhookVerificationError: If the signature is missing, invalid,
            or verification fails

    Example:
        >>> # Flask example
        >>> from flask import Flask, request
        >>> from simplex import verify_simplex_webhook, WebhookPayload
        >>>
        >>> @app.route("/webhook", methods=["POST"])
        >>> def webhook():
        ...     body = request.get_data(as_text=True)
        ...     verify_simplex_webhook(body, dict(request.headers), WEBHOOK_SECRET)
        ...     payload: WebhookPayload = request.get_json()
        ...     print(f"Session: {payload['session_id']}")
        ...     return {"success": True}
    """
    # Normalize header lookup (case-insensitive)
    signature = None
    for key, value in headers.items():
        if key.lower() == "x-simplex-signature":
            signature = value
            break

    if not signature:
        raise WebhookVerificationError("Missing X-Simplex-Signature header")

    # Compute expected signature
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(signature, expected_signature):
        raise WebhookVerificationError("Invalid webhook signature")
