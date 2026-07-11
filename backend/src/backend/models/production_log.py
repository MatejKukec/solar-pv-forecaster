"""Persisted table for user-logged actual production, keyed by site."""

from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


class ProductionLog(SQLModel, table=True):
    """One day's actual logged production for a site.

    `site_id` is a client-generated identifier (e.g. a hash of location +
    array config) — there's no user auth in the demo scope, so this is what
    scopes logged production to "a site" instead of "a user".
    """

    id: int | None = Field(default=None, primary_key=True)
    site_id: str = Field(index=True)
    production_date: date = Field(index=True)
    actual_kwh: float
    logged_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
