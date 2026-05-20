import hashlib
import hmac
import json
import time
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode


class BinanceSpotTestnetClient:
    def __init__(
        self,
        base_url: str = "https://testnet.binance.vision",
        api_key: str = "",
        api_secret: str = "",
        urlopen=urllib.request.urlopen,
        time_ms: Callable[[], int] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.urlopen = urlopen
        self.time_ms = time_ms or (lambda: int(time.time() * 1000))

    def account(self) -> dict:
        return self._signed_request("GET", "/api/v3/account")

    def test_order(
        self,
        symbol,
        side,
        order_type,
        quantity=None,
        quote_order_qty=None,
        price=None,
        time_in_force=None,
    ) -> dict:
        params = self._order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            quote_order_qty=quote_order_qty,
            price=price,
            time_in_force=time_in_force,
        )
        return self._signed_request("POST", "/api/v3/order/test", params)

    def create_order(
        self,
        symbol,
        side,
        order_type,
        quantity=None,
        quote_order_qty=None,
        price=None,
        time_in_force=None,
    ) -> dict:
        params = self._order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            quote_order_qty=quote_order_qty,
            price=price,
            time_in_force=time_in_force,
        )
        return self._signed_request("POST", "/api/v3/order", params)

    def cancel_order(
        self, symbol, order_id=None, orig_client_order_id=None
    ) -> dict:
        params = self._order_lookup_params(
            symbol=symbol,
            order_id=order_id,
            orig_client_order_id=orig_client_order_id,
        )
        return self._signed_request("DELETE", "/api/v3/order", params)

    def get_order(self, symbol, order_id=None, orig_client_order_id=None) -> dict:
        params = self._order_lookup_params(
            symbol=symbol,
            order_id=order_id,
            orig_client_order_id=orig_client_order_id,
        )
        return self._signed_request("GET", "/api/v3/order", params)

    def _order_params(
        self,
        *,
        symbol,
        side,
        order_type,
        quantity=None,
        quote_order_qty=None,
        price=None,
        time_in_force=None,
    ) -> dict[str, Any]:
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if order_type not in {"MARKET", "LIMIT"}:
            raise ValueError("order_type must be MARKET or LIMIT")
        if quantity is None and quote_order_qty is None:
            raise ValueError("quantity or quote_order_qty is required")
        if order_type == "LIMIT":
            if quantity is None:
                raise ValueError("quantity is required for LIMIT orders")
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            if time_in_force is None:
                raise ValueError("time_in_force is required for LIMIT orders")

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "quoteOrderQty": quote_order_qty,
            "price": price,
            "timeInForce": time_in_force,
        }
        return self._without_none(params)

    def _order_lookup_params(
        self, *, symbol, order_id=None, orig_client_order_id=None
    ) -> dict[str, Any]:
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "origClientOrderId": orig_client_order_id,
        }
        return self._without_none(params)

    def _signed_request(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> dict:
        signed_params = dict(params or {})
        signed_params["timestamp"] = self.time_ms()
        signed_params["signature"] = self._signature(signed_params)
        query = urlencode(signed_params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={"X-MBX-APIKEY": self.api_key},
            method=method,
        )
        with self.urlopen(request, timeout=30) as response:
            body = response.read()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _signature(self, params: dict[str, Any]) -> str:
        payload = urlencode(params).encode("utf-8")
        return hmac.new(
            self.api_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

    def _without_none(self, params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in params.items() if value is not None}
