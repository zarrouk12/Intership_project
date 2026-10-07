"""Schemas M1 : organisation, sites, departements."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import ORMModel


class OrganizationOut(ORMModel):
    id: int
    name: str
    code: str
    industry: str | None = None
    country: str | None = None
    description: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    country: str | None = None
    description: str | None = None


class SiteBase(BaseModel):
    name: str
    code: str
    city: str | None = None
    country: str | None = None
    site_type: str | None = None


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    country: str | None = None
    site_type: str | None = None


class SiteOut(ORMModel, SiteBase):
    id: int
    organization_id: int


class DepartmentBase(BaseModel):
    name: str
    code: str
    family: str | None = None
    head_name: str | None = None
    description: str | None = None
    site_id: int | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    family: str | None = None
    head_name: str | None = None
    description: str | None = None
    site_id: int | None = None


class DepartmentOut(ORMModel, DepartmentBase):
    id: int
    organization_id: int
