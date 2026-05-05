from __future__ import annotations

from functools import lru_cache

import tiktoken

ENCODING_FALLBACK = "cl100k_base"

MODEL_ENCODING_MAP = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "claude": "cl100k_base",
}


@lru_cache(maxsize=4)
def _get_tiktoken_encoder(encoding_name: str = ENCODING_FALLBACK):
    return tiktoken.get_encoding(encoding_name)


class Tokenizer:
    def __init__(self, encoding_name: str = ENCODING_FALLBACK):
        self.encoding_name = encoding_name
        self._encoder = _get_tiktoken_encoder(encoding_name)

    @classmethod
    def for_model(cls, model_name: str) -> Tokenizer:
        encoding = MODEL_ENCODING_MAP.get(model_name, ENCODING_FALLBACK)
        return cls(encoding_name=encoding)

    def count(self, text: str) -> int:
        return len(self._encoder.encode(text))

    def truncate(self, text: str, max_tokens: int, suffix: str = "...") -> str:
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated = self._encoder.decode(tokens[: max_tokens - self.count(suffix)])
        return truncated + suffix


def count_tokens(text: str, model: str | None = None) -> int:
    if model:
        tokenizer = Tokenizer.for_model(model)
    else:
        tokenizer = Tokenizer()
    return tokenizer.count(text)


def token_budget_remaining(total: int, consumed: int, reserved: int = 0) -> int:
    return max(0, total - consumed - reserved)
