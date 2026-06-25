"""Outbound links shown in the app, kept in one place.

The donate link is a Lemon Squeezy "Pay What You Want" checkout. Lemon Squeezy's
API is read-only for products/variants, so the product is created once in the LS
dashboard (store: marcriera) and its public "Buy now" URL is pasted below.

Until ``DONATE_URL`` is set, every Support affordance (menu item, settings link,
README badge) is hidden — the app never shows a dead link.
"""

from __future__ import annotations

# Paste the Lemon Squeezy "Buy now" URL for the Scribed donations product here,
# e.g. "https://marcriera.lemonsqueezy.com/buy/<variant-uuid>".
DONATE_URL: str = ""

PROJECT_URL: str = "https://github.com/Joanmarcriera/scribed"


def donate_url() -> str:
    """Return the configured donate URL (stripped), or "" if none is set."""
    return DONATE_URL.strip()
