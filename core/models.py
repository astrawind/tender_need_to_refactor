from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, RootModel, conint, constr


class Username(RootModel[str]):
    root: str = Field(
        ..., description="Уникальный slug пользователя.", examples=["test_user"]
    )


class TenderStatus(str, Enum):
    Created = "Created"
    Published = "Published"
    Closed = "Closed"


class TenderServiceType(Enum):
    Construction = "Construction"
    Delivery = "Delivery"
    Manufacture = "Manufacture"


class TenderId(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(
        ...,
        description="Уникальный идентификатор тендера, присвоенный сервером.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class TenderName(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(..., description="Полное название тендера")


class TenderDescription(RootModel[constr(max_length=500)]):
    root: constr(max_length=500) = Field(..., description="Описание тендера")


class TenderVersion(RootModel[conint(ge=1)]):
    root: conint(ge=1) = Field(..., description="Номер версии посел правок")


class OrganizationId(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(
        ...,
        description="Уникальный идентификатор организации, присвоенный сервером.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class Tender(BaseModel):
    id: TenderId
    name: TenderName = Field(..., alias="creator_username")
    description: TenderDescription
    serviceType: TenderServiceType = Field(..., alias="service_type")
    status: TenderStatus
    organizationId: OrganizationId = Field(..., alias="organization_id")
    version: TenderVersion = Field(..., alias="active_version")
    createdAt: str = Field(
        ...,
        description="Серверная дата и время в момент, когда пользователь отправил тендер на создание.\nПередается в формате RFC3339.\n",
        examples=["2006-01-02T15:04:05Z07:00"],
        alias="created_at",
    )


class BidStatus(Enum):
    Created = "Created"
    Published = "Published"
    Canceled = "Canceled"


class BidDecision(Enum):
    Approved = "Approved"
    Rejected = "Rejected"


class BidId(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(
        ...,
        description="Уникальный идентификатор предложения, присвоенный сервером.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class BidName(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(..., description="Полное название предложения")


class BidDescription(RootModel[constr(max_length=500)]):
    root: constr(max_length=500) = Field(..., description="Описание предложения")


class BidFeedback(RootModel[constr(max_length=1000)]):
    root: constr(max_length=1000) = Field(..., description="Отзыв на предложение")


class BidAuthorType(Enum):
    Organization = "Organization"
    User = "User"


class BidAuthorId(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(
        ...,
        description="Уникальный идентификатор автора предложения, присвоенный сервером.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class BidVersion(RootModel[conint(ge=1)]):
    root: conint(ge=1) = Field(..., description="Номер версии посел правок")


class BidReviewId(RootModel[constr(max_length=100)]):
    root: constr(max_length=100) = Field(
        ...,
        description="Уникальный идентификатор отзыва, присвоенный сервером.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class BidReviewDescription(RootModel[constr(max_length=1000)]):
    root: constr(max_length=1000) = Field(..., description="Описание предложения")


class BidReview(BaseModel):
    id: BidReviewId
    description: BidReviewDescription
    createdAt: str = Field(
        ...,
        description="Серверная дата и время в момент, когда пользователь отправил отзыв на предложение.\nПередается в формате RFC3339.\n",
        examples=["2006-01-02T15:04:05Z07:00"],
    )


class Bid(BaseModel):
    id: BidId
    name: BidName = Field(..., alias="creator_username")
    description: BidDescription
    status: BidStatus
    tenderId: TenderId = Field(..., alias="tender_id")
    authorId: BidAuthorId = Field(..., alias="creator_username")
    version: BidVersion = Field(..., alias="active_version")
    createdAt: str = Field(
        ...,
        description="Серверная дата и время в момент, когда пользователь отправил предложение на создание.\nПередается в формате RFC3339.\n",
        examples=["2006-01-02T15:04:05Z07:00"],
        alias="created_at",
    )

    class Config:
        orm_mode = True


class ErrorResponse(BaseModel):
    reason: constr(min_length=5) = Field(
        ..., description="Описание ошибки в свободной форме"
    )


class TendersGetResponse(RootModel[List[Tender]]):
    root: List[Tender]


class ServiceType(RootModel[List[TenderServiceType]]):
    root: List[TenderServiceType] = Field(..., examples=[["Construction", "Delivery"]])


class TendersNewPostRequest(BaseModel):
    name: TenderName
    description: TenderDescription
    serviceType: TenderServiceType = Field(..., serialization_alias="service_type")
    status: TenderStatus
    organizationId: OrganizationId = Field(..., serialization_alias="organization_id")
    creatorUsername: Username = Field(..., serialization_alias="creator_username")


class TendersMyGetResponse(RootModel[List[Tender]]):
    root: List[Tender]


class TendersTenderIdEditPatchRequest(BaseModel):
    name: Optional[TenderName] = None
    description: Optional[TenderDescription] = None
    serviceType: Optional[TenderServiceType] = Field(..., alias="service_type")


class BidsNewPostRequest(BaseModel):
    name: BidName
    description: BidDescription
    status: BidStatus
    tenderId: TenderId = Field(..., serialization_alias="tender_id")
    organizationId: OrganizationId = Field(..., serialization_alias="organization_id")
    creatorUsername: Username = Field(..., serialization_alias="creator_username")


class BidsMyGetResponse(RootModel[List[Bid]]):
    root: List[Bid]


class BidsTenderIdListGetResponse(RootModel[List[Bid]]):
    root: List[Bid]


class BidsBidIdEditPatchRequest(BaseModel):
    name: Optional[BidName] = None
    description: Optional[BidDescription] = None


class BidsTenderIdReviewsGetResponse(RootModel[List[BidReview]]):
    root: List[BidReview]
