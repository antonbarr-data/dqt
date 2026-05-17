"""SQLAlchemy models for ISO reference tables."""
from __future__ import annotations

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from dqt_server.db.engine import Base


class RefCountry(Base):
    __tablename__ = "ref_countries"

    alpha2: Mapped[str] = mapped_column(String(2), primary_key=True)
    alpha3: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class RefCurrency(Base):
    __tablename__ = "ref_currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    numeric: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    decimals: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)


class RefLanguage(Base):
    __tablename__ = "ref_languages"

    alpha2: Mapped[str] = mapped_column(String(2), primary_key=True)
    alpha3: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class RefTimezone(Base):
    __tablename__ = "ref_timezones"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    utc_region: Mapped[str] = mapped_column(String(32), nullable=False)


class RefRegion(Base):
    __tablename__ = "ref_regions"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
