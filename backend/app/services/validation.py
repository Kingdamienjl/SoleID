from __future__ import annotations

import asyncio
from typing import Optional
import numpy as np
from PIL import Image
import cv2

from app.services.embedding import get_embedding_service, preprocess_image_for_openclip
from app.schemas.validation import ValidationResult


class ImageValidationService:
    """Service for validating images before sneaker matching."""

    # CLIP text prompts for zero-shot classification
    POSITIVE_PROMPTS = [
        "a photo of a sneaker",
        "a photo of athletic shoes",
        "a close up photo of footwear",
        "a photo of running shoes",
        "a photo of basketball shoes",
    ]

    NEGATIVE_PROMPTS = [
        "a photo of a person",
        "a photo of a room",
        "a photo of a face",
        "a photo of food",
        "a photo of an animal",
        "a blurry unrecognizable photo",
    ]

    # Thresholds
    SHOE_CONFIDENCE_THRESHOLD = 0.25  # Minimum shoe confidence
    BLUR_THRESHOLD = 100.0  # Laplacian variance below this = blurry
    MIN_BRIGHTNESS = 30  # Minimum average brightness (0-255)
    MAX_BRIGHTNESS = 240  # Maximum average brightness
    MIN_RESOLUTION = 100  # Minimum dimension in pixels

    def __init__(self) -> None:
        self._text_embeddings: Optional[np.ndarray] = None
        self._embedding_service = get_embedding_service()

    async def _get_text_embeddings(self) -> tuple[np.ndarray, np.ndarray]:
        """Get or compute text embeddings for classification."""
        if self._text_embeddings is None:
            all_prompts = self.POSITIVE_PROMPTS + self.NEGATIVE_PROMPTS
            embeddings = await self._embedding_service.encode_text(all_prompts)
            self._text_embeddings = embeddings

        n_positive = len(self.POSITIVE_PROMPTS)
        positive_emb = self._text_embeddings[:n_positive]
        negative_emb = self._text_embeddings[n_positive:]
        return positive_emb, negative_emb

    def _check_image_quality(self, pil_image: Image.Image) -> tuple[list[str], list[str]]:
        """Check image quality (blur, brightness, resolution)."""
        errors = []
        suggestions = []

        # Check resolution
        width, height = pil_image.size
        if width < self.MIN_RESOLUTION or height < self.MIN_RESOLUTION:
            errors.append("Image resolution is too low")
            suggestions.append("Use a higher resolution image (at least 100x100 pixels)")

        # Convert to numpy for CV2 analysis
        img_array = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Check blur using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < self.BLUR_THRESHOLD:
            errors.append("Image appears blurry")
            suggestions.append("Hold the camera steady and tap to focus before capturing")

        # Check brightness
        avg_brightness = np.mean(gray)
        if avg_brightness < self.MIN_BRIGHTNESS:
            errors.append("Image is too dark")
            suggestions.append("Move to a brighter area or turn on the flash")
        elif avg_brightness > self.MAX_BRIGHTNESS:
            errors.append("Image is overexposed")
            suggestions.append("Reduce lighting or avoid direct flash")

        return errors, suggestions

    async def _classify_content(self, pil_image: Image.Image) -> tuple[float, bool]:
        """Use CLIP to classify if image contains a shoe."""
        # Get text embeddings
        positive_emb, negative_emb = await self._get_text_embeddings()

        # Encode image
        tensor = preprocess_image_for_openclip(pil_image)
        image_embedding = await self._embedding_service.embed_tensor(tensor)

        # Calculate similarities
        positive_sims = np.dot(positive_emb, image_embedding)
        negative_sims = np.dot(negative_emb, image_embedding)

        # Get best positive (shoe) score and best negative (non-shoe) score
        shoe_score = float(np.max(positive_sims))
        non_shoe_score = float(np.max(negative_sims))

        # Normalize to 0-1 range (CLIP similarities are typically -1 to 1)
        shoe_confidence = (shoe_score + 1) / 2

        # Valid if shoe score beats threshold AND beats non-shoe score
        is_shoe = shoe_score > self.SHOE_CONFIDENCE_THRESHOLD and shoe_score > non_shoe_score

        return shoe_confidence, is_shoe

    async def validate_image(self, pil_image: Image.Image) -> ValidationResult:
        """
        Validate an image for sneaker matching.

        Returns ValidationResult with:
        - is_valid: True if image passes all checks
        - confidence: CLIP shoe confidence score
        - validation_errors: List of issues found
        - suggestions: Helpful tips to fix issues
        """
        all_errors = []
        all_suggestions = []

        # 1. Check image quality
        quality_errors, quality_suggestions = self._check_image_quality(pil_image)
        all_errors.extend(quality_errors)
        all_suggestions.extend(quality_suggestions)

        # 2. CLIP content classification
        shoe_confidence, is_shoe = await self._classify_content(pil_image)

        if not is_shoe:
            all_errors.append("No shoe detected in image")
            all_suggestions.extend([
                "Make sure the shoe is clearly visible",
                "Center the shoe in the frame",
                "Avoid including other objects in the photo",
            ])

        # Image is valid if no errors
        is_valid = len(all_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            confidence=shoe_confidence,
            validation_errors=all_errors,
            suggestions=all_suggestions,
        )


# Singleton instance
_validation_service: Optional[ImageValidationService] = None


def get_validation_service() -> ImageValidationService:
    """Get or create the validation service singleton."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ImageValidationService()
    return _validation_service
