"""Exceptions raised by weather/solar-resource data clients."""


class DataSourceError(RuntimeError):
    """Raised when an upstream data provider fails or returns unusable data."""

    def __init__(self, source: str, message: str) -> None:
        self.source = source
        super().__init__(f"{source}: {message}")
