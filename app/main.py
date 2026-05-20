import logging
import os
from typing import Dict

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response

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


@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    headers = {name: value for name, value in request.headers.items()}

    logger.debug("Incoming request: %s %s", request.method, request.url)
    logger.debug("Client: %s", request.client.host if request.client else None)
    logger.debug("Query params: %s", dict(request.query_params))
    logger.debug("Headers: %s", headers)
    logger.debug("Body: %s", body.decode("utf-8", errors="replace") if body else "<empty>")

    response = await call_next(request)
    logger.debug("Response status: %s", response.status_code)
    logger.debug("Response headers: %s", dict(response.headers))
    return response

unsafe_headers = {
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


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ok", "backend": AUTOMX2_URL}


async def build_forward_headers(request: Request) -> Dict[str, str]:
    headers = {}
    for name, value in request.headers.items():
        if name.lower() not in unsafe_headers:
            headers[name] = value
    return headers


async def proxy_to_automx2(request: Request, target_path: str) -> Response:
    target_url = f"{AUTOMX2_URL}/{target_path.lstrip('/')}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = await build_forward_headers(request)
    body = await request.body()

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Errore di comunicazione con automx2: {exc}")

    filtered_headers = {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in {"content-encoding", "transfer-encoding", "connection", "keep-alive"}
    }
    return Response(content=response.content, status_code=response.status_code, headers=filtered_headers)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(full_path: str, request: Request) -> Response:
    return await proxy_to_automx2(request, full_path)
