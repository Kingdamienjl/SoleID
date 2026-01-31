from pydantic import BaseModel, Field
from typing import List, Optional


class ValidationResult(BaseModel):
    """Result of image validation before matching."""
    is_valid: bool
    shoe_confidence: float = Field(ge=0.0, le=1.0, description="CLIP confidence that image contains a shoe")
    validation_errors: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall image quality score")


class ValidationResponse(BaseModel):
    """Response from /validate endpoint."""
    validation: ValidationResult
