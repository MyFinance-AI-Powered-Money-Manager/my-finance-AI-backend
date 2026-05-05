import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from veryfi import Client


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {var_name}. "
            "Set it in your environment or in a .env file."
        )
    return value


@lru_cache(maxsize=1)
def get_veryfi_client() -> Client:
    """Create and cache a Veryfi client.

    This must be import-safe (no network calls, no printing).
    """

    load_dotenv()

    return Client(
        client_id=_require_env("VERYFI_CLIENT_ID"),
        client_secret=_require_env("VERYFI_CLIENT_SECRET"),
        username=_require_env("VERYFI_USERNAME"),
        api_key=_require_env("VERYFI_API_KEY"),
    )


def process_document(file_path: str) -> dict[str, Any]:
    """Run OCR via Veryfi on a local file path and return the raw response."""

    client = get_veryfi_client()
    return client.process_document(file_path)


def parse_line_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Veryfi 'line_items' into a simplified schema."""

    items = response.get("line_items") or []
    parsed_items: list[dict[str, Any]] = []

    for item in items:
        parsed_items.append(
            {
                "name": item.get("description"),
                "qty": item.get("quantity"),
                "price": item.get("unit_price"),
                "total": item.get("total"),
            }
        )

    return parsed_items