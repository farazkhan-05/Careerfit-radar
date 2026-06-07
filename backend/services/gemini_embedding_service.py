from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, cast

from backend.config import Settings, get_settings
from backend.utils.hash_utils import sha256_text
from backend.utils.text_utils import normalize_text


class EmbeddingStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class GeminiEmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    model_name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass


@dataclass(frozen=True)
class TextEmbedding:
    text_hash: str
    text: str
    vector: tuple[float, ...]
    model_name: str


@dataclass(frozen=True)
class EmbeddingBatchResult:
    status: EmbeddingStatus
    model_name: str
    embeddings: tuple[TextEmbedding, ...] = ()
    error_message: str | None = None


class GoogleGeminiEmbeddingClient:
    def __init__(self, *, api_key: str, model_name: str) -> None:
        self._api_key = api_key
        self.model_name = model_name

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
    ) -> GoogleGeminiEmbeddingClient:
        resolved = settings or get_settings()
        return cls(
            api_key=resolved.gemini_api_key,
            model_name=resolved.gemini_embedding_model,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise GeminiEmbeddingError("google-genai is not installed.") from exc

        client = genai.Client(api_key=self._api_key)
        response = client.models.embed_content(
            model=self.model_name,
            contents=cast(Any, texts),
        )
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None:
            raise GeminiEmbeddingError("Gemini returned no embeddings.")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            values = getattr(embedding, "values", None)
            if not values:
                raise GeminiEmbeddingError("Gemini returned an empty embedding vector.")
            vectors.append([float(value) for value in values])
        return vectors


class GeminiEmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> GeminiEmbeddingService:
        return cls(GoogleGeminiEmbeddingClient.from_settings(settings))

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        normalized_texts = [normalize_text(text) for text in texts if normalize_text(text)]
        if not normalized_texts:
            return EmbeddingBatchResult(
                status=EmbeddingStatus.FAILED,
                model_name=self._provider.model_name,
                error_message="At least one non-empty text is required.",
            )

        try:
            vectors = self._provider.embed_texts(normalized_texts)
        except GeminiEmbeddingError as exc:
            return EmbeddingBatchResult(
                status=EmbeddingStatus.FAILED,
                model_name=self._provider.model_name,
                error_message=str(exc),
            )

        if len(vectors) != len(normalized_texts):
            return EmbeddingBatchResult(
                status=EmbeddingStatus.FAILED,
                model_name=self._provider.model_name,
                error_message="Embedding count did not match input text count.",
            )

        return EmbeddingBatchResult(
            status=EmbeddingStatus.SUCCESS,
            model_name=self._provider.model_name,
            embeddings=tuple(
                TextEmbedding(
                    text_hash=sha256_text(text),
                    text=text,
                    vector=tuple(vector),
                    model_name=self._provider.model_name,
                )
                for text, vector in zip(normalized_texts, vectors, strict=True)
            ),
        )
