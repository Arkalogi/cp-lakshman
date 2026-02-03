from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class ApiClient:
    def __init__(self, base_url: str, verify_tls: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.verify_tls = verify_tls

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = requests.get(self._url(path), params=params, verify=self.verify_tls)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(self._url(path), json=payload, verify=self.verify_tls)
        response.raise_for_status()
        return response.json()

    def put(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.put(self._url(path), json=payload, verify=self.verify_tls)
        response.raise_for_status()
        return response.json()
