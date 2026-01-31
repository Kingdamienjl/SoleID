from __future__ import annotations

import asyncio
from typing import Optional

import os
import torch
from PIL import Image
import numpy as np
import open_clip
from torchvision import transforms


_embedding_service_singleton: Optional["EmbeddingService"] = None


def get_embedding_service() -> "EmbeddingService":
    global _embedding_service_singleton
    if _embedding_service_singleton is None:
        _embedding_service_singleton = EmbeddingService()
    return _embedding_service_singleton


def preprocess_image_for_openclip(image: Image.Image) -> torch.Tensor:
    # Resize longest side to 336, center-crop square, normalize per OpenCLIP mean/std
    image = image.copy()
    width, height = image.size
    scale = 336 / max(width, height)
    new_size = (int(round(width * scale)), int(round(height * scale)))
    image = image.resize(new_size, Image.BICUBIC)
    # Center crop to 336x336
    left = max(0, (image.width - 336) // 2)
    top = max(0, (image.height - 336) // 2)
    image = image.crop((left, top, left + 336, top + 336))

    preprocess = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.48145466, 0.4578275, 0.40821073), std=(0.26862954, 0.26130258, 0.27577711)),
        ]
    )
    tensor = preprocess(image).unsqueeze(0)
    return tensor


class EmbeddingService:
    def __init__(self) -> None:
        self.mock = os.getenv("MOCK_EMBEDDING", "false").lower() == "true"
        self.tokenizer = None
        if not self.mock:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            model_name = "ViT-B-16"
            pretrained = "openai"
            self.model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
            self.model.eval()
            self.model.to(self.device)
            self.tokenizer = open_clip.get_tokenizer(model_name)

    async def embed_tensor(self, tensor: torch.Tensor) -> np.ndarray:
        if self.mock:
            # Deterministic pseudo-vector based on tensor statistics
            arr = tensor.detach().cpu().numpy()
            seed = int(abs(float(arr.mean() + arr.std())) * 1e6) % (2**32 - 1)
            rng = np.random.default_rng(seed)
            vec = rng.normal(size=(512,)).astype(np.float32)
            # Normalize to unit length
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            return vec

        def _embed() -> np.ndarray:
            with torch.no_grad():
                t = tensor.to(self.device)
                image_features = self.model.encode_image(t)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                vec = image_features.detach().cpu().numpy().astype(np.float32)
                return vec[0]

        return await asyncio.to_thread(_embed)

    async def encode_text(self, texts: list[str]) -> np.ndarray:
        """Encode text prompts into embeddings for zero-shot classification."""
        if self.mock:
            # Return deterministic pseudo-vectors for testing
            vecs = []
            for i, text in enumerate(texts):
                seed = hash(text) % (2**32 - 1)
                rng = np.random.default_rng(seed)
                vec = rng.normal(size=(512,)).astype(np.float32)
                vec = vec / (np.linalg.norm(vec) + 1e-8)
                vecs.append(vec)
            return np.array(vecs)

        def _encode() -> np.ndarray:
            with torch.no_grad():
                tokens = self.tokenizer(texts).to(self.device)
                text_features = self.model.encode_text(tokens)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                return text_features.detach().cpu().numpy().astype(np.float32)

        return await asyncio.to_thread(_encode)
