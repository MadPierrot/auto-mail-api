import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, EmailStr

from app.config import settings

logger = logging.getLogger("auto-mail-api")

router = APIRouter(
    prefix="/autodiscover/autodiscover.json",
    tags=["autodiscover-json"],
)

GET_PROTOCOLS = {"AutodiscoverV1"}


def get_protocol_urls() -> dict[str, str]:
    return {
        "ActiveSync": settings.activesync_url,
        "AutodiscoverV1": settings.autodiscover_v1_url,
        "Ews": settings.ews_url,
    }


class AutodiscoverRequest(BaseModel):
    EMailAddress: EmailStr


class AutodiscoverResponse(BaseModel):
    Protocol: str
    Url: str


@router.get("/v1.0/{email:path}")
async def autodiscover_v1_get(
    email: str,
    Protocol: Optional[str] = Query(None),
    RedirectCount: Optional[int] = Query(0),
):
    """
    GET è valido solo per AutodiscoverV1.
    Tutti gli altri protocolli richiedono POST.
    """
    if Protocol not in GET_PROTOCOLS:
        return PlainTextResponse(content="Must be a POST request", status_code=400)

    if RedirectCount and RedirectCount > 2:
        return PlainTextResponse(
            content="Loop detected: troppi redirect", status_code=508
        )

    url = get_protocol_urls().get(Protocol)
    if url is None:
        return PlainTextResponse(
            content=f"Protocollo non supportato: '{Protocol}'", status_code=400
        )

    logger.debug("Autodiscover GET: email=%s protocol=%s url=%s", email, Protocol, url)
    return JSONResponse(content={"Protocol": Protocol, "Url": url})


@router.post("/v1.0/{email:path}")
async def autodiscover_v1_post(
    email: str,
    body: AutodiscoverRequest,
    Protocol: str = Query(...),
    RedirectCount: Optional[int] = Query(0),
):
    """Microsoft Autodiscover JSON v1.0 — POST per ActiveSync, EWS, ecc."""
    logger.debug(
        "Autodiscover POST: email=%s protocol=%s redirect_count=%s",
        body.EMailAddress,
        Protocol,
        RedirectCount,
    )

    if RedirectCount and RedirectCount > 2:
        return PlainTextResponse(
            content="Loop detected: troppi redirect", status_code=508
        )

    protocol_urls = get_protocol_urls()
    url = protocol_urls.get(Protocol)
    if url is None:
        return PlainTextResponse(
            content=f"Protocollo non supportato: '{Protocol}'. Supportati: {list(protocol_urls.keys())}",
            status_code=400,
        )

    logger.debug(
        "Autodiscover POST: email=%s protocol=%s url=%s",
        body.EMailAddress,
        Protocol,
        url,
    )
    return AutodiscoverResponse(Protocol=Protocol, Url=url)
