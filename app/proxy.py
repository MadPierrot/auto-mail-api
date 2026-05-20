# app/proxy.py

import logging

import httpx
from fastapi import HTTPException, Request, Response

from app.config import settings

logger = logging.getLogger("auto-mail-api")

UNSAFE_HEADERS = frozenset(
    {
        "host",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

UNSAFE_RESPONSE_HEADERS = frozenset(
    {
        "content-encoding",
        "transfer-encoding",
        "connection",
        "keep-alive",
    }
)


def build_forward_headers(request: Request) -> dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in UNSAFE_HEADERS
    }


async def proxy_to_automx2(request: Request, target_path: str) -> Response:
    automx2_url = settings.automx2_url.rstrip("/")
    target_url = f"{automx2_url}/{target_path.lstrip('/')}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = build_forward_headers(request)
    body = await request.body()
    logger.debug("Proxying to: %s", target_url)

    async with httpx.AsyncClient(timeout=settings.automx2_timeout) as client:
        try:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True,
            )
        except httpx.TimeoutException as exc:
            logger.error("Timeout contacting automx2: %s", exc)
            raise HTTPException(
                status_code=504, detail=f"Timeout comunicazione con automx2: {exc}"
            )
        except httpx.RequestError as exc:
            logger.error("Error contacting automx2: %s", exc)
            raise HTTPException(
                status_code=502, detail=f"Errore di comunicazione con automx2: {exc}"
            )

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() not in UNSAFE_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
