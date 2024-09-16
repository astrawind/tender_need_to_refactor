from __future__ import annotations

import logging
from typing import Optional, Union, Annotated

import database.orm as orm
from fastapi import APIRouter, FastAPI, Path, Query, Response, status
from models import (
    Bid,
    BidDecision,
    BidFeedback,
    BidId,
    BidsBidIdEditPatchRequest,
    BidsMyGetResponse,
    BidsNewPostRequest,
    BidStatus,
    BidsTenderIdListGetResponse,
    BidsTenderIdReviewsGetResponse,
    ErrorResponse,
    ServiceType,
    Tender,
    TenderId,
    TendersGetResponse,
    TendersMyGetResponse,
    TendersNewPostRequest,
    TenderStatus,
    TendersTenderIdEditPatchRequest,
    Username,
)
from pydantic import conint
from sqlalchemy import (  # с точки зрения инъекций, этого здесь быть не должно, но было мало времени...
    insert,
    select,
    update,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/tenders", tags=["tenders"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn_main")


@router.get(
    "/",
    response_model=TendersGetResponse,
    responses={"400": {"model": ErrorResponse}},
)
def get_tenders(
    service_type=Annotated[Optional[ServiceType], None],
    limit: Optional[conint(ge=0, le=50)] = 5,
    offset: Optional[conint(ge=0)] = 0,
) -> Union[TendersGetResponse, ErrorResponse]:
    with Session(orm.engine) as session:
        try:
            if str(service_type):
                results = (
                    session.query(
                        orm.Tender.id,
                        orm.TenderVersion.name,
                        orm.TenderVersion.description,
                        orm.Tender.status,
                        orm.TenderVersion.service_type,
                        orm.Tender.organization_id,
                        orm.Tender.creator_username,
                        orm.Tender.active_version,
                        orm.Tender.created_at,
                    )
                    .join(
                        orm.TenderVersion,
                        (orm.Tender.id == orm.TenderVersion.tender_id)
                        & (orm.TenderVersion.version == orm.Tender.active_version),
                    )
                    .where(orm.TenderVersion.service_type == str(service_type))
                    .limit(limit)
                    .offset(offset)
                    .all()
                    )
            else:
                results = (
                    session.query(
                        orm.Tender.id,
                        orm.TenderVersion.name,
                        orm.TenderVersion.description,
                        orm.Tender.status,
                        orm.TenderVersion.service_type,
                        orm.Tender.organization_id,
                        orm.Tender.creator_username,
                        orm.Tender.active_version,
                        orm.Tender.created_at,
                    )
                    .join(
                        orm.TenderVersion,
                        (orm.Tender.id == orm.TenderVersion.tender_id)
                        & (orm.TenderVersion.version == orm.Tender.active_version),
                    )
                    .limit(limit)
                    .offset(offset)
                    .all()
                    )
            return TendersGetResponse(
                [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "description": row[2],
                        "status": str(row[3]),
                        "service_type": str(row[4]),
                        "organization_id": str(row[5]),
                        "creator_username": row[6],
                        "active_version": row[7],
                        "created_at": str(row[8]),
                    }
                    for row in results
                ]
            )
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=401, content=ErrorResponse(reason=str(e)).model_dump_json()
            )


@router.get(
    "/my",
    response_model=TendersMyGetResponse,
    responses={"401": {"model": ErrorResponse}},
)
def get_user_tenders(
    username=Annotated[Username, ""],
    limit: Optional[conint(ge=0, le=50)] = 5,
    offset: Optional[conint(ge=0)] = 0,
) -> Union[TendersMyGetResponse, ErrorResponse]:
    if not username:
            return Response(
                status_code=401, content=ErrorResponse(reason="None username field").model_dump_json()
            )
    with Session(orm.engine) as session:
        try:
            results = (
                session.query(
                    orm.Tender.id,
                    orm.TenderVersion.name,
                    orm.TenderVersion.description,
                    orm.Tender.status,
                    orm.TenderVersion.service_type,
                    orm.Tender.organization_id,
                    orm.Tender.creator_username,
                    orm.Tender.active_version,
                    orm.Tender.created_at,
                )
                .join(
                    orm.TenderVersion,
                    (orm.Tender.id == orm.TenderVersion.tender_id)
                    & (orm.TenderVersion.version == orm.Tender.active_version),
                )
                .where(orm.Tender.creator_username == str(username))
                .limit(limit)
                .offset(offset)
                .all()
            )
            return TendersMyGetResponse(
                [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "description": row[2],
                        "status": row[3],
                        "service_type": row[4],
                        "organization_id": str(row[5]),
                        "creator_username": row[6],
                        "active_version": row[7],
                        "created_at": str(row[8]),
                    }
                    for row in results
                ]
            )
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=401, content=ErrorResponse(reason=str(e)).model_dump_json()
            )

@router.post(
    "/new",
    response_model=Tender,
    responses={"401": {"model": ErrorResponse}, "403": {"model": ErrorResponse}},
)
def create_tender(
    response: Response, body: TendersNewPostRequest
) -> Union[Tender, ErrorResponse]:
    tender_dict = body.model_dump(mode="json", by_alias=True)
    dict_for_version = {
        item: tender_dict[item]
        for item in tender_dict
        if item in ["name", "description", "service_type"]
    }
    dict_for_tender = {
        item: tender_dict[item]
        for item in tender_dict
        if item in ["organization_id", "creator_username", "status"]
    }
    stmt_tender = (
        insert(orm.Tender)
        .returning(orm.Tender.id, orm.Tender.created_at, orm.Tender.active_version)
        .values(**dict_for_tender)
    )
    with Session(orm.engine) as session:
        try:
            result = session.execute(stmt_tender)
            res = result.fetchone()
            res_id, res_time, res_vers = [str(item) for item in res]
            stmt_version = insert(orm.TenderVersion).values(
                **dict_for_version, tender_id=res_id
            )
            session.execute(stmt_version)
            tender = Tender(
                **dict_for_tender,
                **dict_for_version,
                **{"id": res_id, "created_at": res_time, "active_version": res_vers},
            )
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=403, content=ErrorResponse(reason=str(e)).model_dump_json()
            )
        session.commit()
    return tender


@router.patch(
    "/{tenderId}/edit",
    response_model=Tender,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def edit_tender(
    tender_id: TenderId = Path(..., alias="tenderId"),
    username: Username = ...,
    body: TendersTenderIdEditPatchRequest = ...,
) -> Union[Tender, ErrorResponse]:
    """
    Редактирование тендера
    """
    pass


@router.put(
    "/{tenderId}/rollback/{version}",
    response_model=Tender,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def rollback_tender(
    tender_id: TenderId = Path(..., alias="tenderId"),
    version: conint(ge=1) = ...,
    username: Username = ...,
) -> Union[Tender, ErrorResponse]:
    """
    Откат версии тендера
    """
    pass


@router.get(
    "/{tenderId}/status",
    response_model=TenderStatus,
    responses={
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def get_tender_status(
    tender_id: TenderId = Path(..., alias="tenderId"),
    username = Annotated[Optional[Username], None]
) -> Union[TenderStatus, ErrorResponse]:
       with Session(orm.engine) as session:
        try:
            if not username or (
                username
                != session.query(orm.Tender.creator_username)
                .where(orm.Tender.id == tender_id.root)
                .one()[0]
            ):
                return Response(
                status_code=403,
                content=ErrorResponse(
                    reason="invalid authentication"
                ).model_dump_json(),
                )
            result = (
                session.query(
                    orm.Tender.status
                )
                .where(orm.Tender.id == tender_id.root)
                .one()[0]
            )
            return result
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=401, content=ErrorResponse(reason=str(e)).model_dump_json()
            )



@router.put(
    "/{tenderId}/status",
    response_model=Tender,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def update_tender_status(
    tender_id: TenderId = Path(..., alias="tenderId"),
    status: TenderStatus = ...,
    username: Username = ...,
) -> Union[Tender, ErrorResponse]:
    """
    Изменение статуса тендера
    """
    pass
