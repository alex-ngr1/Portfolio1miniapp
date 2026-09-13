import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.auth import TelegramAuthError, verify_telegram_init_data


def _signed(payload: dict, token: str) -> str:
    check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**payload, "hash": digest})


def test_telegram_init_data_ok():
    user = json.dumps({"id": 4242, "first_name": "Олена"}, ensure_ascii=False)
    init = _signed({"auth_date": "1710000000", "query_id": "AA", "user": user}, "secret-token")
    parsed = verify_telegram_init_data(init, "secret-token")
    assert parsed["id"] == 4242
    assert parsed["first_name"] == "Олена"


def test_telegram_init_data_rejects_bad_hash():
    with pytest.raises(TelegramAuthError):
        verify_telegram_init_data("user=%7B%7D&hash=deadbeef", "secret-token")
