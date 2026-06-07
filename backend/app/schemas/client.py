"""Tally client request/response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    tally_host: str = Field(default="localhost", max_length=255)
    tally_port: int = Field(default=9000, ge=1, le=65535)
    financial_year: str = Field(
        ..., pattern=r"^\d{4}-\d{4}$", description="e.g. 2025-2026"
    )
    company_number: str | None = Field(None, max_length=50)
    gstin: str | None = Field(None, max_length=15)
    pan: str | None = Field(None, max_length=10)
    notes: str | None = None


class ClientUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=255)
    tally_host: str | None = Field(None, max_length=255)
    tally_port: int | None = Field(None, ge=1, le=65535)
    financial_year: str | None = Field(None, pattern=r"^\d{4}-\d{4}$")
    company_number: str | None = None
    gstin: str | None = None
    pan: str | None = None
    notes: str | None = None


class ClientResponse(BaseModel):
    id: str
    company_name: str
    tally_host: str
    tally_port: int
    financial_year: str
    company_number: str | None
    gstin: str | None
    pan: str | None
    notes: str | None
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    clients: list[ClientResponse]
    total: int


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    company_name: str | None = None
