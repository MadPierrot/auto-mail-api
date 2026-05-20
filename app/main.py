# app/main.py

import logging
from typing import Dict
from urllib.parse import unquote

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.proxy import proxy_to_automx2
from app.routers.autodiscoverJson import router as autodiscover_json_router
from app.routers.autodiscoverXml import router as autodiscover_xml_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.DEBUG),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("auto-mail-api")

app = FastAPI(
    title="Auto Mail API",
    description="Proxy FastAPI per inoltrare le richieste di autoconfigurazione verso un backend automx2.",
    version="0.1.0",
)


class DecodePathMiddleware(BaseHTTPMiddleware):
    """Decodifica %40 e altri caratteri encodati nel path prima del routing."""
    async def dispatch(self, request: Request, call_next):
        scope = request.scope
        raw_path = scope.get("path", "")
        decoded_path = unquote(raw_path)
        if decoded_path != raw_path:
            logger.debug("Path decoded: %s → %s", raw_path, decoded_path)
            scope["path"] = decoded_path
            scope["raw_path"] = decoded_path.encode("utf-8")
        return await call_next(request)


# ⚠️ DecodePathMiddleware PRIMA del log middleware (i middleware si eseguono in ordine inverso)
app.add_middleware(DecodePathMiddleware)


@app.middleware("http")
async def log_request(request: Request, call_next):
    body = await request.body()
    logger.debug("→ %s %s", request.method, request.url)
    logger.debug("  Client:  %s", request.client.host if request.client else "unknown")
    logger.debug("  Params:  %s", dict(request.query_params))
    logger.debug("  Headers: %s", dict(request.headers))
    logger.debug(
        "  Body:    %s", body.decode("utf-8", errors="replace") if body else "<empty>"
    )
    response = await call_next(request)
    logger.debug("← %s %s", response.status_code, request.url)
    logger.debug("  Headers: %s", dict(response.headers))
    return response


# ⚠️ Router specializzati PRIMA del catch-all
app.include_router(autodiscover_json_router)
app.include_router(autodiscover_xml_router)


@app.get("/", response_model=Dict[str, str])
async def root():
    return {"status": "ok", "backend": settings.automx2_url}


# @app.api_route(
#     "/{full_path:path}",
#     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
# )
async def proxy(full_path: str, request: Request) -> Response:
    return await proxy_to_automx2(request, full_path)
