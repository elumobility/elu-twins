from __future__ import annotations

from datetime import datetime, UTC


def get_token_price() -> int:
    return 1


def get_now(as_string: bool = True) -> datetime | str:
    now = datetime.now(UTC)
    if as_string:
        return now.isoformat()
    return now
