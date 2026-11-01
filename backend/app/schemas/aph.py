"""
Pydantic schemas for APH versions, extraction, and rules.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AphRuleDraft(BaseModel):
    """Schema for individual extracted rules validated against Gemini structured output."""

    parameter: str = Field(description="Human-readable parameter name, e.g. 'Classrooms'")
    parameter_key: str = Field(description="Normalized snake_case key, e.g. 'classroom_count'")
    programme: str = Field(description="Programme name, e.g. 'Engineering and Technology'")
    programme_key: str = Field(description="Normalized snake_case programme key, e.g. 'engineering_technology'")
    category: str = Field(description="Category, e.g. 'Instructional Area', 'Faculty', etc.")
    operator: str = Field(description="Comparison operator: >=, <=, ==, >, <, in")
    string_value: Optional[str] = Field(default=None, description="Non-numeric expected value")
    numeric_value: Optional[float] = Field(default=None, description="Numeric expected value")
    unit: Optional[str] = Field(default=None, description="Measurement unit, e.g. 'sq_m', 'count', 'ratio'")
    source_page: int = Field(description="1-based page number where the rule appears in the PDF")
    source_quote: str = Field(description="Verbatim excerpt from the source page confirming the rule")


class AphRuleExtractionResult(BaseModel):
    """Wrapper schema for Gemini array response."""

    rules: list[AphRuleDraft] = Field(default_factory=list)


class AphRuleResponse(BaseModel):
    id: uuid.UUID
    aph_version_id: uuid.UUID
    programme: str
    programme_key: str
    category: str
    parameter: str
    parameter_key: str
    operator: str
    string_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None
    needs_review: bool
    is_ai_suggested: bool
    edited_by: Optional[uuid.UUID] = None
    edited_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AphRuleCreateRequest(BaseModel):
    programme: str
    programme_key: str
    category: str
    parameter: str
    parameter_key: str
    operator: str
    string_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None


class AphRuleUpdateRequest(BaseModel):
    programme: Optional[str] = None
    programme_key: Optional[str] = None
    category: Optional[str] = None
    parameter: Optional[str] = None
    parameter_key: Optional[str] = None
    operator: Optional[str] = None
    string_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    source_page: Optional[int] = None
    source_quote: Optional[str] = None
    needs_review: Optional[bool] = None


class AphVersionResponse(BaseModel):
    id: uuid.UUID
    version_label: str
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    status: str
    extraction_status: str
    content_hash: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[uuid.UUID] = None
    effective_date: Optional[date] = None
    extraction_log: Optional[dict] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AphPublishRequest(BaseModel):
    effective_date: date

