import datetime
import uuid
from typing import List, Optional

from config import setings
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employee"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="employee_pkey"),
        UniqueConstraint("username", name="employee_username_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    username: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    organization_responsible: Mapped[List["OrganizationResponsible"]] = relationship(
        "OrganizationResponsible", back_populates="user"
    )
    tender: Mapped[List["Tender"]] = relationship("Tender", back_populates="employee")
    bid: Mapped[List["Bid"]] = relationship("Bid", back_populates="employee")


class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = (PrimaryKeyConstraint("id", name="organization_pkey"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[Optional[str]] = mapped_column(
        Enum("IE", "LLC", "JSC", name="organization_type")
    )
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    organization_responsible: Mapped[List["OrganizationResponsible"]] = relationship(
        "OrganizationResponsible", back_populates="organization"
    )
    tender: Mapped[List["Tender"]] = relationship(
        "Tender", back_populates="organization"
    )
    bid: Mapped[List["Bid"]] = relationship("Bid", back_populates="organization")


class OrganizationResponsible(Base):
    __tablename__ = "organization_responsible"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
            ondelete="CASCADE",
            name="organization_responsible_organization_id_fkey",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["employee.id"],
            ondelete="CASCADE",
            name="organization_responsible_user_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="organization_responsible_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="organization_responsible"
    )
    user: Mapped["Employee"] = relationship(
        "Employee", back_populates="organization_responsible"
    )


class Tender(Base):
    __tablename__ = "tender"
    __table_args__ = (
        CheckConstraint("active_version >= 1", name="tender_active_version_check"),
        ForeignKeyConstraint(
            ["creator_username"],
            ["employee.username"],
            name="tender_creator_username_fkey",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
            ondelete="CASCADE",
            name="tender_organization_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="tender_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    status: Mapped[str] = mapped_column(
        Enum("Created", "Published", "Closed", name="tender_status")
    )
    active_version: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    creator_username: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    employee: Mapped["Employee"] = relationship("Employee", back_populates="tender")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="tender"
    )
    bid: Mapped[List["Bid"]] = relationship("Bid", back_populates="tender")


class TenderVersion(Base):
    __tablename__ = "tender_version"

    tender_id = Column(
        Uuid, ForeignKey("tender.id", ondelete="CASCADE"), primary_key=True
    )
    version = Column(Integer, server_default=text("1"), primary_key=True)
    name = Column(String(100))
    description = Column(String(500))
    service_type = Column(String(20), nullable=False)

    __table_args__ = (
        CheckConstraint("version >= 1", name="tender_version_version_check"),
        UniqueConstraint(
            "tender_id", "version", name="tender_version_tender_id_version_key"
        ),
    )


class Bid(Base):
    __tablename__ = "bid"
    __table_args__ = (
        ForeignKeyConstraint(
            ["creator_username"],
            ["employee.username"],
            name="bid_creator_username_fkey",
        ),
        ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], name="bid_organization_id_fkey"
        ),
        ForeignKeyConstraint(
            ["tender_id"], ["tender.id"], ondelete="CASCADE", name="bid_tender_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="bid_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    status: Mapped[Optional[str]] = mapped_column(
        Enum("Created", "Published", "Canceled", name="bid_status"),
        server_default=text("'Created'::bid_status"),
    )
    desision: Mapped[Optional[str]] = mapped_column(
        Enum("Approved", "Rejected", name="bid_desision")
    )
    tender_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    active_version: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("1")
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    creator_username: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    employee: Mapped["Employee"] = relationship("Employee", back_populates="bid")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="bid"
    )
    tender: Mapped["Tender"] = relationship("Tender", back_populates="bid")


class BidVersion(Base):
    __tablename__ = "bid_version"

    bid_id = Column(Uuid, ForeignKey("bid.id", ondelete="CASCADE"), primary_key=True)
    version = Column(Integer, server_default=text("1"), primary_key=True)
    name = Column(String(100))
    description = Column(String(500))

    __table_args__ = (
        CheckConstraint("version >= 1", name="bid_version_version_check"),
        UniqueConstraint("bid_id", "version", name="bid_version_bid_id_version_key"),
    )


# t_tender_version = Table(
#     'tender_version', Base.metadata,
#     Column('tender_id', Uuid),
#     Column('version', Integer, server_default=text('1')),
#     Column('name', String(100)),
#     Column('description', String(500)),
#     Column('service_type', String(20), nullable=False),
#     CheckConstraint('version >= 1', name='tender_version_version_check'),
#     ForeignKeyConstraint(['tender_id'], ['tender.id'], ondelete='CASCADE', name='tender_version_tender_id_fkey'),
#     UniqueConstraint('tender_id', 'version', name='tender_version_tender_id_version_key')
# )


# t_bid_version = Table(
#     'bid_version', Base.metadata,
#     Column('bid_id', Uuid),
#     Column('version', Integer, server_default=text('1')),
#     Column('name', String(100)),
#     Column('description', String(500)),
#     CheckConstraint('version >= 1', name='bid_version_version_check'),
#     ForeignKeyConstraint(['bid_id'], ['bid.id'], ondelete='CASCADE', name='bid_version_bid_id_fkey'),
#     UniqueConstraint('bid_id', 'version', name='bid_version_bid_id_version_key')
# )


engine = create_engine(setings.postgress_conn)
