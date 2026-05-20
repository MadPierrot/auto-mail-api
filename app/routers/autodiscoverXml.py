import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.proxy import proxy_to_automx2

logger = logging.getLogger("auto-mail-api")

router = APIRouter(
    prefix="/autodiscover",
    tags=["autodiscover-xml"],
)

@router.get("/autodiscover.xml")
async def autodiscover_xml_get(request: Request) -> Response:
    logger.debug("Autodiscover XML GET request: %s %s", request.method, request.url)
    return PlainTextResponse(content="Must be a POST request", status_code=400)

@router.post("/autodiscover.xml")
async def autodiscover_xml_post(request: Request) -> Response:
    logger.debug("Autodiscover XML POST request: %s %s", request.method, request.url)
    return await proxy_to_automx2(request, "/autodiscover/autodiscover.xml")
