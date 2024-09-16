import logging

from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/api", tags=["ping"])


@router.get("/ping", response_model=str)
def check_server() -> str:
    return Response(content="ok", status_code=200)
