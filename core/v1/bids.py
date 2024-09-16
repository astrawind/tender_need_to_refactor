from __future__ import annotations

import logging
from typing import Annotated, Optional, Union
from uuid import UUID

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
    func,
    insert,
    select,
    update,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/bids", tags=["bids"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn_main")


@router.get(
    "/my",
    response_model=BidsMyGetResponse,
    responses={"401": {"model": ErrorResponse}},
)
def get_user_bids(
    username=Annotated[Username, ""],
    limit: Optional[conint(ge=0, le=50)] = 5,
    offset: Optional[conint(ge=0)] = 0,
) -> Union[BidsMyGetResponse, ErrorResponse]:
    if not username.root:
        return Response(
            status_code=401, content=ErrorResponse(reason="None username field").model_dump_json()
            )
    with Session(orm.engine) as session:
        try:
            results = (
                session.query(
                    orm.Bid.id,
                    orm.BidVersion.name,
                    orm.BidVersion.description,
                    orm.Bid.status,
                    orm.Bid.tender_id,
                    orm.Bid.creator_username,
                    orm.Bid.active_version,
                    orm.Bid.created_at,
                )
                .join(
                    orm.BidVersion,
                    (orm.Bid.id == orm.BidVersion.bid_id)
                    & (orm.BidVersion.version == orm.Bid.active_version),
                )
                .where(orm.Bid.creator_username == str(username))
                .limit(limit)
                .offset(offset)
                .all()
            )
            return BidsMyGetResponse(
                [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "description": row[2],
                        "status": row[3],
                        "tender_id": str(row[4]),
                        "creator_username": row[5],
                        "active_version": row[6],
                        "created_at": str(row[7]),
                    }
                    for row in results
                ]
            )
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=403, content=ErrorResponse(reason=str(e)).model_dump_json()
            )


@router.post(
    "/new",
    response_model=Bid,
    responses={
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def create_bid(body: BidsNewPostRequest) -> Union[Bid, ErrorResponse]:
    bid_dict = body.model_dump(mode="json", by_alias=True)
    dict_for_version = {
        item: bid_dict[item] for item in bid_dict if item in ["name", "description"]
    }
    dict_for_bid = {
        item: bid_dict[item]
        for item in bid_dict
        if item in ["organization_id", "creator_username", "status", "tender_id"]
    }
    stmt_tender = (
        insert(orm.Bid)
        .returning(orm.Bid.id, orm.Bid.created_at, orm.Bid.active_version)
        .values(**dict_for_bid)
    )
    with Session(orm.engine) as session:
        try:
            result = session.execute(stmt_tender)
            res = result.fetchone()
            res_id, res_time, res_vers = [str(item) for item in res]
            stmt_version = insert(orm.BidVersion).values(
                **dict_for_version, bid_id=res_id
            )
            session.execute(stmt_version)
            logger.debug(
                dict(
                    **dict_for_bid,
                    **dict_for_version,
                    **{
                        "id": res_id,
                        "created_at": res_time,
                        "active_version": res_vers,
                    },
                )
            )
            tender = Bid(
                **dict_for_bid,
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
    "/{bidId}/edit",
    response_model=Bid,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def edit_bid(
    bid_id: BidId = Path(..., alias="bidId"),
    username: Username = ...,
    body: BidsBidIdEditPatchRequest = ...,
) -> Union[Bid, ErrorResponse]:
    with Session(orm.engine) as session:
        try:
            if not username.root:
                    return Response(
                    status_code=401,
                    content=ErrorResponse(
                        reason="None username"
                    ).model_dump_json(),
                    )
            user_check = session.query(orm.Bid.creator_username).where(orm.Bid.id == bid_id.root).one()[0]
            if not user_check:
                return Response(
                    status_code=404,
                    content=ErrorResponse(
                        reason="page not found"
                    ).model_dump_json(),
                    )
            if user_check != username.root:
                return Response(
                    status_code=403,
                    content=ErrorResponse(
                        reason="invalid authentication"
                    ).model_dump_json(),
                    )
            old_bid = (
                    session.query(
                        orm.Bid.id,
                        orm.BidVersion.name,
                        orm.BidVersion.description,
                        orm.Bid.status,
                        orm.Bid.tender_id,
                        orm.Bid.creator_username,
                        orm.Bid.active_version,
                        orm.Bid.created_at,
                    )
                    .join(
                        orm.BidVersion,
                        (orm.Bid.id == orm.BidVersion.bid_id)
                        & (orm.BidVersion.version == orm.Bid.active_version),
                    )
                    .where(orm.Bid.id == bid_id.root)
                    .one()
                )
            if not body.name:
                body.name = old_bid[1] #плохо читаемый код, но быстрый в разработке тестового задания.
            if not body.description:
                body.description = old_bid[2]
            max_version = session.query(func.max(orm.BidVersion.version)).where(orm.BidVersion.bid_id == bid_id.root).one()[0]
            new_version = orm.BidVersion(bid_id = old_bid[0], 
                                        version = max_version + 1, 
                                        name = body.name.root,
                                        description = body.description.root
                                        )
            # max_version = session.query(func.max(orm.BidVersion.version)).where(orm.BidVersion.bid_id == bid_id.root)
            # stmnt_new_version = insert(orm.BidVersion).values(new_version)
            session.add(new_version)
            session.query(orm.Bid).filter(orm.Bid.id == bid_id.root).update({"active_version": max_version + 1})
            resp = Bid(**{
                        "id": str(old_bid[0]),
                        "name": body.name,
                        "description": body.description,
                        "status": old_bid[3],
                        "tender_id": str(old_bid[4]),
                        "creator_username": old_bid[5],
                        "active_version": max_version + 1,
                        "created_at": str(old_bid[7]),
                    })
            session.commit()
            return resp
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=500, content=ErrorResponse(reason='Server error').model_dump_json()
            )

        
    
        


# @router.put(
#     '/{bidId}/feedback',
#     response_model=Bid,
#     responses={
#         '400': {'model': ErrorResponse},
#         '401': {'model': ErrorResponse},
#         '403': {'model': ErrorResponse},
#         '404': {'model': ErrorResponse},
#     },
# )
# def submit_bid_feedback(
#     bid_id: BidId = Path(..., alias='bidId'),
#     bid_feedback: BidFeedback = Query(..., alias='bidFeedback'),
#     username: Username = ...,
# ) -> Union[Bid, ErrorResponse]:
#     """
#     Отправка отзыва по предложению
#     """
#     pass


@router.put(
    "/{bidId}/rollback/{version}",
    response_model=Bid,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def rollback_bid(
    bid_id: BidId = Path(..., alias="bidId"),
    version: conint(ge=1) = ...,
    username=Annotated[Username, None],
) -> Union[Bid, ErrorResponse]:
    with Session(orm.engine) as session:
        try:
            new_bid = (
                        session.query(
                            orm.Bid.id,
                            orm.BidVersion.name,
                            orm.BidVersion.description,
                            orm.Bid.status,
                            orm.Bid.tender_id,
                            orm.Bid.creator_username,
                            orm.Bid.active_version,
                            orm.Bid.created_at,
                        )
                        .join(
                            orm.BidVersion,
                            (orm.Bid.id == orm.BidVersion.bid_id)
                        )
                        .where(orm.Bid.id == bid_id.root and orm.BidVersion.version == version and orm.Bid.creator_username == username.root)
                        .first())
            if not new_bid:
                    return Response(status_code=401, content=ErrorResponse(reason='No Bid for query').model_dump_json())
            session.query(orm.Bid).filter(orm.Bid.id == bid_id.root).update({"active_version": version})
            resp = Bid(**{
                            "id": str(new_bid[0]),
                            "name": new_bid[1],
                            "description": new_bid[2],
                            "status": new_bid[3],
                            "tender_id": str(new_bid[4]),
                            "creator_username": new_bid[5],
                            "active_version": version,
                            "created_at": str(new_bid[7]),
                        })
            return resp
        except Exception as e:
            logger.error(str(e))
            session.rollback()
            return Response(
                status_code=500, content=ErrorResponse(reason='Server error').model_dump_json()
            )
        


        


@router.get(
    "/{bidId}/status",
    response_model=BidStatus,
    responses={
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def get_bid_status(
    username=Annotated[Username, ""],
    bid_id: BidId = Path(..., alias="bidId"),
) -> Union[BidStatus, ErrorResponse]:
    with Session(orm.engine) as session:
        try:
            if not username or (
                username
                != session.query(orm.Bid.creator_username)
                .where(orm.Bid.id == bid_id.root)
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
                    orm.Bid.status
                )
                .where(orm.Bid.id == bid_id.root)
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
    "/{bidId}/status",
    response_model=Bid,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def update_bid_status(
    bid_id: BidId = Path(..., alias="bidId"),
    status: BidStatus = ...,
    username: Username = ...,
) -> Union[Bid, ErrorResponse]:
    """
    Изменение статуса предложения
    """
    pass


@router.put(
    "/{bidId}/submit_decision",
    response_model=Bid,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def submit_bid_decision(
    bid_id: BidId = Path(..., alias="bidId"),
    decision: BidDecision = ...,
    username: Username = ...,
) -> Union[Bid, ErrorResponse]:
    """
    Отправка решения по предложению
    """
    pass


@router.get(
    "/{tenderId}/list",
    response_model=BidsTenderIdListGetResponse,
    responses={
        "400": {"model": ErrorResponse},
        "401": {"model": ErrorResponse},
        "403": {"model": ErrorResponse},
        "404": {"model": ErrorResponse},
    },
)
def get_bids_for_tender(
    tender_id: TenderId = Path(..., alias="tenderId"),
    username=Annotated[Username, ""],
    limit: Optional[conint(ge=0, le=50)] = 5,
    offset: Optional[conint(ge=0)] = 0,
) -> Union[BidsTenderIdListGetResponse, ErrorResponse]:
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
            results = (
                session.query(
                    orm.Bid.id,
                    orm.BidVersion.name,
                    orm.BidVersion.description,
                    orm.Bid.status,
                    orm.Bid.tender_id,
                    orm.Bid.creator_username,
                    orm.Bid.active_version,
                    orm.Bid.created_at,
                )
                .join(
                    orm.BidVersion,
                    (orm.Bid.id == orm.BidVersion.bid_id)
                    & (orm.BidVersion.version == orm.Bid.active_version),
                )
                .where(orm.Bid.tender_id == tender_id.root)
                .limit(limit)
                .offset(offset)
                .all()
            )
            return BidsTenderIdListGetResponse(
                [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "description": row[2],
                        "status": row[3],
                        "tender_id": str(row[4]),
                        "creator_username": row[5],
                        "active_version": row[6],
                        "created_at": str(row[7]),
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


# @router.get(
#     '/{tenderId}/reviews',
#     response_model=BidsTenderIdReviewsGetResponse,
#     responses={
#         '400': {'model': ErrorResponse},
#         '401': {'model': ErrorResponse},
#         '403': {'model': ErrorResponse},
#         '404': {'model': ErrorResponse},
#     },
# )
# def get_bid_reviews(
#     tender_id: TenderId = Path(..., alias='tenderId'),
#     author_username: Username = Query(..., alias='authorUsername'),
#     requester_username: Username = Query(..., alias='requesterUsername'),
#     limit: Optional[conint(ge=0, le=50)] = 5,
#     offset: Optional[conint(ge=0)] = 0,
# ) -> Union[BidsTenderIdReviewsGetResponse, ErrorResponse]:
#     """
#     Просмотр отзывов на прошлые предложения
#     """
#     pass
