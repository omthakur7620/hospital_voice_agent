"""
ORM models.

Key production decision: double-booking is prevented with a PARTIAL UNIQUE
INDEX on (doctor_id, appointment_date, appointment_time), not just an
app-level "check then insert" — because under concurrent requests (two
Vapi calls booking the same slot at the same millisecond), an app-level
check has a race condition. The DB constraint is the real guarantee;
the app-level check is just there to return a friendly error instead of
a raw IntegrityError.

It's a PARTIAL index (only enforced where status IN ('confirmed',
'rescheduled')) because a cancelled appointment must free the slot for
reuse — a plain unique constraint would block rebooking that slot forever.
"""

import enum
import uuid
from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Time, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppointmentStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"   # active appointment whose slot has changed at least once
    COMPLETED = "completed"


# Statuses that count as "occupying a slot" for conflict-checking purposes.
ACTIVE_STATUSES = (AppointmentStatus.CONFIRMED.value, AppointmentStatus.RESCHEDULED.value)


def generate_appointment_id() -> str:
    """
    Human-readable unique ID like 'APT-20250115-A7F3B2'.
    Includes date for quick identification, UUID suffix for uniqueness.
    """
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"APT-{today}-{suffix}"


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Store slots as TIME arrays for efficient querying
    # Example: [time(10,0), time(10,30), time(11,0)]
    available_slots: Mapped[List[time]] = mapped_column(
        postgresql.ARRAY(Time), 
        nullable=False, 
        default=list
    )

    consultation_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="in-person"
    )

    # Store working days as integer array: 0=Monday, 1=Tuesday, ..., 5=Saturday
    # Example: [0,1,2,3,4,5] for Monday-Saturday
    working_days: Mapped[List[int]] = mapped_column(
        postgresql.ARRAY(Integer), 
        nullable=False, 
        default=list
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)  # soft-disable without deleting history

    appointments: Mapped[List["Appointment"]] = relationship(
        back_populates="doctor", 
        lazy="selectin"  # Prevents N+1 queries when loading doctor with appointments
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.name!r} dept={self.department!r}>"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Unique: repeat callers (same phone number) resolve to the same patient
    # record instead of creating duplicates — important since this is a
    # voice agent and patients call back to cancel/reschedule.
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    appointments: Mapped[List["Appointment"]] = relationship(
        back_populates="patient",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} phone={self.phone_number!r}>"


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[str] = mapped_column(
        String(30),  # APT-20250115-A7F3B2 = 19 chars
        primary_key=True, 
        default=generate_appointment_id
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"), 
        nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="RESTRICT"), 
        nullable=False
    )

    appointment_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Store as TIMESTAMP WITH TIME ZONE
        nullable=False, 
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=AppointmentStatus.CONFIRMED.value
    )

    appointment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    patient: Mapped["Patient"] = relationship(back_populates="appointments")

    __table_args__ = (
        # The actual double-booking guard. postgresql_where restricts the
        # uniqueness check to "live" appointments only, so a cancelled or
        # completed appointment doesn't permanently lock that slot.
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "appointment_datetime",
            unique=True,
            postgresql_where=text(
                f"status IN ('{AppointmentStatus.CONFIRMED.value}', '{AppointmentStatus.RESCHEDULED.value}')"
            ),
        ),
        # Index for fast slot availability queries
        Index("idx_appointments_doctor_datetime_status", "doctor_id", "appointment_datetime", "status"),
        # Index for patient history queries
        Index("idx_appointments_patient_status", "patient_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment {self.appointment_id} doctor={self.doctor_id} "
            f"datetime={self.appointment_datetime} status={self.status!r}>"
        )