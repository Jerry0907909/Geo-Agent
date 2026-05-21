"""HTTP client factory for OpenAI-compatible providers."""

from __future__ import annotations

from typing import Optional, Tuple

import httpx


def create_http_clients(
    *,
    timeout: float,
    use_env_proxy: bool = False,
    proxy_url: Optional[str] = None,
) -> Tuple[httpx.Client, httpx.AsyncClient]:
    """Create sync and async httpx clients with explicit proxy behavior."""

    client_kwargs = {
        "timeout": timeout,
        "trust_env": use_env_proxy,
    }

    if proxy_url:
        client_kwargs["proxy"] = proxy_url
        client_kwargs["trust_env"] = False

    return httpx.Client(**client_kwargs), httpx.AsyncClient(**client_kwargs)
