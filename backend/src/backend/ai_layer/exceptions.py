"""Exceptions raised by AIProvider implementations."""


class AIProviderError(RuntimeError):
    """Raised when an AI provider fails or returns unusable output."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"{provider}: {message}")
