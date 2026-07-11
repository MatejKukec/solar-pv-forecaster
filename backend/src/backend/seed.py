"""Auto-seed demo production data (Section 6.1 of the dev plan: "seeded demo
data" is a must-have — a recruiter won't manually log 7 days of production
before seeing anything work).

Seeds a fixed demo site (the same coordinates as the frontend's default
form) with ~10 days of synthetic-but-plausible actual production, so
calibration and the past-date overlay have something to show immediately.
Idempotent: only inserts if this site has no logged production yet.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from backend.models import ProductionLog
from backend.site_id import site_id_for

# Matches the frontend's DEFAULT_LOCATION / DEFAULT_ARRAY (constants.ts).
DEMO_LATITUDE = 45.815
DEMO_LONGITUDE = 15.9819
DEMO_CAPACITY_KW = 5.0
DEMO_DAYS = 10


def seed_demo_data(session: Session) -> None:
    """Insert synthetic production history for the demo site, if it has none yet."""
    site_id = site_id_for(DEMO_LATITUDE, DEMO_LONGITUDE)
    already_seeded = session.exec(select(ProductionLog).where(ProductionLog.site_id == site_id)).first()
    if already_seeded:
        return

    rng = random.Random(42)  # deterministic across restarts
    today = datetime.now(UTC).date()
    for days_ago in range(1, DEMO_DAYS + 1):
        production_date = today - timedelta(days=days_ago)
        # Plausible daily yield for a 5kW system: ~3.5 kWh/kW/day average,
        # with day-to-day weather variation.
        actual_kwh = round(DEMO_CAPACITY_KW * rng.uniform(2.5, 4.5), 2)
        session.add(ProductionLog(site_id=site_id, production_date=production_date, actual_kwh=actual_kwh))
    session.commit()


def demo_site_id() -> str:
    """The demo site's ID, for tests/tooling that need to reference it."""
    return site_id_for(DEMO_LATITUDE, DEMO_LONGITUDE)
