"""
Seed script — loads data/hospital_data.json into the `doctors` table.

Idempotent by design: re-running this script (e.g. after the hospital
updates a doctor's slots) UPDATES existing doctors matched by
(name, department) instead of creating duplicates. This matters because
in real operation, the hospital data file gets re-synced periodically.

Run from the project root:
    python -m scripts.seed
"""

import asyncio
import json
import sys
from datetime import time
from pathlib import Path
from typing import List, Optional

# Allow running this script directly (`python scripts/seed.py`) by putting
# the project root on sys.path so `app.*` imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, get_db_context  # noqa: E402
from app.logger import get_logger  # noqa: E402
from app.models import Doctor  # noqa: E402

logger = get_logger(__name__)

REQUIRED_DOCTOR_FIELDS = {"name", "department", "available_slots", "working_days"}

# Day name to integer mapping (0 = Monday)
DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def parse_working_days(working_days_raw) -> List[int]:
    """
    Normalize working days from various formats to integer array.
    
    Handles:
    - List of strings: ["Monday", "Tuesday"] -> [0, 1]
    - Comma-separated string: "Monday, Tuesday" -> [0, 1]
    - Empty list: [] -> []
    - "By Appointment Only" -> [] (empty)
    """
    if not working_days_raw:
        return []
    
    if isinstance(working_days_raw, list):
        # Already a list, convert strings to integers
        if all(isinstance(d, int) for d in working_days_raw):
            return working_days_raw  # Already normalized
        return [DAY_MAP.get(day.strip(), -1) for day in working_days_raw if day.strip() in DAY_MAP]
    
    if isinstance(working_days_raw, str):
        # Parse comma-separated string
        if working_days_raw.lower() == "by appointment only":
            return []
        days = [day.strip() for day in working_days_raw.split(",")]
        return [DAY_MAP.get(day, -1) for day in days if day in DAY_MAP]
    
    # Fallback: return empty list
    logger.warning(f"Unexpected working_days format: {working_days_raw}")
    return []


def parse_time_slot(time_str: str) -> Optional[time]:
    """
    Parse time string to Python time object.
    
    Handles:
    - "10:00 AM" -> time(10, 0)
    - "10:00" -> time(10, 0)
    - "4:30 PM" -> time(16, 30)
    """
    time_str = time_str.strip()
    
    # Try 24-hour format first
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1][:2]) if len(parts) > 1 else 0
            # Check for AM/PM
            if "PM" in time_str and hour < 12:
                hour += 12
            elif "AM" in time_str and hour == 12:
                hour = 0
            return time(hour, minute)
    except (ValueError, IndexError):
        pass
    
    logger.warning(f"Could not parse time string: {time_str}")
    return None


def parse_available_slots(slots_raw: List[str]) -> List[time]:
    """Convert string slots to time objects."""
    parsed = []
    for slot_str in slots_raw:
        parsed_time = parse_time_slot(slot_str)
        if parsed_time:
            parsed.append(parsed_time)
        else:
            logger.warning(f"Skipping invalid slot: {slot_str}")
    return sorted(parsed)  # Sort for consistent ordering


def load_hospital_data() -> dict:
    """Reads and validates the JSON file. Fails loudly with a clear message,
    not a stack trace, if the file is missing or malformed — this script
    can be run by anyone deploying the system, not just the original author."""
    data_path = PROJECT_ROOT / settings.HOSPITAL_DATA_PATH

    if not data_path.exists():
        raise FileNotFoundError(
            f"Hospital data file not found at '{data_path}'. "
            f"Check HOSPITAL_DATA_PATH in your .env."
        )

    with open(data_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in '{data_path}': {exc}") from exc

    if "doctors" not in data or not isinstance(data["doctors"], list):
        raise ValueError("hospital_data.json must contain a top-level 'doctors' list")

    return data


def validate_doctor_entry(entry: dict, index: int) -> None:
    """Catches bad data (e.g. a missing field in one doctor record) before
    it reaches the database, with the exact index so it's easy to fix."""
    missing = REQUIRED_DOCTOR_FIELDS - entry.keys()
    if missing:
        raise ValueError(f"doctors[{index}] is missing required fields: {missing}")
    
    # Warn about empty slots but don't fail
    if not entry.get("available_slots"):
        logger.warning(f"doctors[{index}] ('{entry.get('name')}') has no available_slots")


async def ensure_schema() -> None:
    """
    Ensures the database schema matches our models.
    In dev mode, we drop and recreate tables.
    In production, we assume migrations handle this.
    """
    if not settings.is_production:
        logger.warning("Development mode: Dropping and recreating tables...")
        async with engine.begin() as conn:
            # Drop all tables and recreate with the latest schema
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables recreated with latest schema")
    else:
        logger.info("Production mode: Assuming migrations have been run")
        # Check if tables exist
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'doctors')")
            )
            exists = result.scalar()
            if not exists:
                raise RuntimeError(
                    "Tables don't exist! Please run: alembic upgrade head"
                )


async def seed_doctors() -> None:
    data = load_hospital_data()
    doctors_data = data["doctors"]

    logger.info(f"Loaded {len(doctors_data)} doctor records from hospital_data.json")

    # Ensure schema is up to date
    await ensure_schema()

    inserted, updated = 0, 0

    async with get_db_context() as db:
        for index, entry in enumerate(doctors_data):
            validate_doctor_entry(entry, index)

            # Parse and normalize data
            working_days = parse_working_days(entry.get("working_days", []))
            available_slots = parse_available_slots(entry.get("available_slots", []))

            # Check if doctor exists
            result = await db.execute(
                select(Doctor).where(
                    Doctor.name == entry["name"],
                    Doctor.department == entry["department"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing doctor
                existing.specialization = entry.get("specialization")
                existing.location = entry.get("location")
                existing.available_slots = available_slots
                existing.working_days = working_days
                existing.consultation_type = entry.get("consultation_type", "in-person")
                existing.is_active = True
                updated += 1
                logger.debug(f"Updated doctor: {entry['name']}")
            else:
                # Create new doctor
                db.add(
                    Doctor(
                        name=entry["name"],
                        department=entry["department"],
                        specialization=entry.get("specialization"),
                        location=entry.get("location"),
                        available_slots=available_slots,
                        working_days=working_days,
                        consultation_type=entry.get("consultation_type", "in-person"),
                    )
                )
                inserted += 1
                logger.debug(f"Inserted doctor: {entry['name']}")

        await db.commit()

    logger.info(f"Seed complete — inserted: {inserted}, updated: {updated}")
    print(f"\n✅ Seed complete — {inserted} doctors inserted, {updated} updated.\n")
    print(f"   Working days format: 0=Monday, 1=Tuesday, ... 5=Saturday")
    print(f"   Slots stored as TIME objects (24-hour format)")


if __name__ == "__main__":
    try:
        asyncio.run(seed_doctors())
    except Exception as exc:
        print(f"\n❌ Seed failed: {exc}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)