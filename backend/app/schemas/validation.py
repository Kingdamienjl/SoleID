from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of image validation."""

    is_valid: bool
    confidence: float  # CLIP shoe confidence score (0-1)
    validation_errors: list[str] = []
    suggestions: list[str] = []


class ValidationResponse(BaseModel):
    """Response that includes validation result and optional match candidates."""

    validation: ValidationResult
    # If valid and matching was performed, include candidates
    candidates: Optional[list] = None
