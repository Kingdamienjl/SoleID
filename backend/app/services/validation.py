"""
Image validation service for SoleID.
Uses CLIP zero-shot classification to detect if an image contains shoes/sneakers.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import cv2

from app.services.embedding import get_embedding_service, preprocess_image_for_openclip
from app.schemas.validation import ValidationResult


_validation_service_singleton: Optional["ImageValidationService"] = None


def get_validation_service() -> "ImageValidationService":
    global _validation_service_singleton
    if _validation_service_singleton is None:
        _validation_service_singleton = ImageValidationService()
    return _validation_service_singleton


# CLIP prompts for zero-shot classification
SHOE_PROMPTS = [
    "a photo of a sneaker",
    "a photo of athletic shoes",
    "a close up photo of footwear",
    "a photo of a shoe on a surface",
    "a product photo of sneakers",
]

NON_SHOE_PROMPTS = [
    "a photo of a person",
    "a photo of a room or interior",
    "a photo of random objects",
    "a blurry unfocused photo",
    "a photo of food",
    "a photo of nature or outdoors",
]


class ImageValidationService:
    """Service for validating images before sneaker matching."""

    def __init__(self) -> None:
        self.embedding_service = get_embedding_service()
        self._shoe_embeddings: Optional[np.ndarray] = None
        self._non_shoe_embeddings: Optional[np.ndarray] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of text embeddings."""
        if self._initialized:
            return

        # Pre-compute text embeddings for classification
        self._shoe_embeddings = await self.embedding_service.encode_text(SHOE_PROMPTS)
        self._non_shoe_embeddings = await self.embedding_service.encode_text(NON_SHOE_PROMPTS)
        self._initialized = True

    async def validate_image(self, pil_image: Image.Image) -> ValidationResult:
        """
        Validate an image for sneaker matching.

        Returns ValidationResult with:
        - is_valid: True if image appears to contain a shoe
        - shoe_confidence: CLIP confidence score
        - validation_errors: List of issues found
        - suggestions: Helpful tips for better images
        """
        await self._ensure_initialized()

        errors = []
        suggestions = []

        # 1. Basic image quality checks
        quality_score, quality_errors, quality_suggestions = self._check_image_quality(pil_image)
        errors.extend(quality_errors)
        suggestions.extend(quality_suggestions)

        # 2. CLIP zero-shot classification
        shoe_confidence = await self._classify_shoe_content(pil_image)

        # 3. Determine validity
        confidence_threshold = 0.25  # Tunable threshold
        is_shoe = shoe_confidence > confidence_threshold

        if not is_shoe:
            errors.append("No shoe or sneaker detected in the image")
            suggestions.extend([
                "Make sure the shoe is clearly visible in the frame",
                "Center the shoe in the image",
                "Avoid including too many other objects"
            ])

        # Valid if shoe detected and no critical quality issues
        is_valid = is_shoe and quality_score > 0.3

        return ValidationResult(
            is_valid=is_valid,
            shoe_confidence=float(shoe_confidence),
            validation_errors=errors,
            suggestions=suggestions,
            quality_score=quality_score
        )

    async def _classify_shoe_content(self, pil_image: Image.Image) -> float:
        """
        Use CLIP to classify if image contains a shoe.
        Returns confidence score between 0 and 1.
        """
        # Get image embedding
        tensor = preprocess_image_for_openclip(pil_image)
        image_embedding = await self.embedding_service.embed_tensor(tensor)

        # Calculate similarities
        shoe_similarities = np.dot(self._shoe_embeddings, image_embedding)
        non_shoe_similarities = np.dot(self._non_shoe_embeddings, image_embedding)

        # Use max similarity from each category
        max_shoe_sim = float(np.max(shoe_similarities))
        max_non_shoe_sim = float(np.max(non_shoe_similarities))

        # Convert to probability-like score using softmax
        exp_shoe = np.exp(max_shoe_sim * 5)  # Temperature scaling
        exp_non_shoe = np.exp(max_non_shoe_sim * 5)
        shoe_confidence = exp_shoe / (exp_shoe + exp_non_shoe)

        return shoe_confidence

    def _check_image_quality(self, pil_image: Image.Image) -> Tuple[float, list, list]:
        """
        Check image quality (blur, brightness, size).
        Returns (quality_score, errors, suggestions).
        """
        errors = []
        suggestions = []
        scores = []

        # Convert to numpy for analysis
        img_array = np.array(pil_image)

        # Check minimum size
        width, height = pil_image.size
        if width < 224 or height < 224:
            errors.append("Image resolution is too low")
            suggestions.append("Use a higher resolution image (at least 224x224)")
            scores.append(0.3)
        else:
            scores.append(1.0)

        # Check blur using Laplacian variance
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_threshold = 100  # Tunable

        if laplacian_var < blur_threshold:
            errors.append("Image appears blurry")
            suggestions.append("Hold the camera steady and ensure the shoe is in focus")
            scores.append(0.5)
        else:
            scores.append(1.0)

        # Check brightness
        brightness = np.mean(gray)

        if brightness < 40:
            errors.append("Image is too dark")
            suggestions.append("Move to a brighter area or turn on the flash")
            scores.append(0.5)
        elif brightness > 240:
            errors.append("Image is overexposed")
            suggestions.append("Avoid direct sunlight or bright lights")
            scores.append(0.5)
        else:
            scores.append(1.0)

        # Calculate overall quality score
        quality_score = float(np.mean(scores)) if scores else 1.0

        return quality_score, errors, suggestions
