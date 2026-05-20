import logging
import os
from typing import Dict

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response

from app.routers.autodiscoverJson import router as autodiscover_json_router

load_dotenv()

AUTOMX2_URL = os.getenv("AUTOMX2_URL", "http://localhost:9999").rstrip("/")
TIMEOUT_SECONDS = int(os.getenv("AUTOMX2_TIMEOUT", "15"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("auto-mail-api")

app = FastAPI(
    title="Auto Mail API",
    description="Proxy FastAPI per inoltrare le richieste di autoconfigurazione verso un backend automx2.",
    version="0.1.0",
)

# Headers that must not be forwarded upstream
UNSAFE_HEADERS = frozenset({
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
})

# Headers that must not be forwarded downstream
UNSAFE_RESPONSE_HEADERS = frozenset({
    "content-encoding",
    "transfer-encoding",
    "connection",
    "keep-alive",
})


@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    logger.debug("→ %s %s", request.method, request.url)
    logger.debug("  Client:  %s", request.client.host if request.client else "unknown")
    logger.debug("  Params:  %s", dict(request.query_params))
    logger.debug("  Headers: %s", dict(request.headers))
    logger.debug("  Body:    %s", body.decode("utf-8", errors="replace") if body else "<empty>")

    response = await call_next(request)

    logger.debug("← %s %s", response.status_code, request.url)
    logger.debug("  Headers: %s", dict(response.headers))
    return response


@app.get("/", response_model=Dict[str, str])
async def root():
    return {"status": "ok", "backend": AUTOMX2_URL}


def build_forward_headers(request: Request) -> Dict[str, str]:
    return {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in UNSAFE_HEADERS
    }


async def proxy_to_automx2(request: Request, target_path: str) -> Response:
    path = target_path.lstrip("/")
    target_url = f"{AUTOMX2_URL}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = build_forward_headers(request)
    body = await request.body()

    logger.debug("Proxying to: %s", target_url)

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
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
            raise HTTPException(status_code=504, detail=f"Timeout comunicazione con automx2: {exc}")
        except httpx.RequestError as exc:
            logger.error("Error contacting automx2: %s", exc)
            raise HTTPException(status_code=502, detail=f"Errore di comunicazione con automx2: {exc}")

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() not in UNSAFE_RESPONSE_HEADERS
    }

    logger.debug("Upstream response: %s, headers: %s", upstream.status_code, response_headers)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )

app.include_router(autodiscover_json_router)

@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(full_path: str, request: Request) -> Response:
    return await proxy_to_automx2(request, full_path)
