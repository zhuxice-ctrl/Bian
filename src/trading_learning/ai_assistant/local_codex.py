from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class LocalCodexClient:
    base_url: str
    api_key: str
    model: str

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self._validate_loopback_base_url()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1200,
        }
        request = urllib.request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def health(self) -> dict[str, Any]:
        try:
            self._validate_loopback_base_url()
            self.chat("Return JSON only.", '{"ping":"ok"}')
        except Exception as exc:
            return {
                "mode": "unavailable",
                "configured": True,
                "reachable": False,
                "base_url": self.base_url,
                "model": self.model,
                "message": str(exc),
            }
        return {
            "mode": "connected",
            "configured": True,
            "reachable": True,
            "base_url": self.base_url,
            "model": self.model,
            "message": "local Codex-compatible API is reachable",
        }

    def _validate_loopback_base_url(self) -> None:
        hostname = urlparse(self.base_url).hostname
        if hostname not in _LOOPBACK_HOSTS:
            raise ValueError("Local Codex base_url must use a loopback host")
