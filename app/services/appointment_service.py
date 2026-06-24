"""
Appointment service - handles appointment lifecycle.

Responsible for:
- Booking appointments with conflict detection
- Canceling appointments
- Rescheduling appointments
- Generating alternative slot suggestions
- Patient deduplication
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Appointment, 
    Patient, 
    Doctor,
    AppointmentStatus,
    ACTIVE_STATUSES,
    generate_appointment_id
)
from app.services.doctor_service import DoctorService
from app.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class AppointmentService:
    """Service for appointment operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doctor_service = DoctorService(db)

    async def book_appointment(
        self,
        patient_name: str,
        phone_number: str,
        doctor_id: UUID,
        appointment_datetime: datetime,
        appointment_type: str = "New Consultation",
        email: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[Appointment, bool]:
        """
        Book an appointment with conflict detection.
        
        Returns:
            Tuple of (Appointment, is_new_patient)
        
        Raises:
            ValueError: If slot is already booked or doctor unavailable
            IntegrityError: If concurrent booking occurs
        """
        # Check doctor exists and is active
        doctor = await self.doctor_service.get_doctor_by_id(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor with ID {doctor_id} not found or inactive")

        # Check if doctor works on this day
        day_of_week = appointment_datetime.weekday()
        if day_of_week not in doctor.working_days:
            raise ValueError(f"Dr. {doctor.name} does not work on {appointment_datetime.strftime('%A')}")

        # Check if slot is in doctor's available slots
        slot_time = appointment_datetime.time()
        if slot_time not in doctor.available_slots:
            raise ValueError(f"Time {slot_time.strftime('%I:%M %p')} is not available for Dr. {doctor.name}")

        # Check for existing booking at this slot (double-booking prevention)
        existing = await self.db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime == appointment_datetime,
                Appointment.status.in_(ACTIVE_STATUSES)
            )
        )
        if existing.scalar_one_or_none():
            # Generate alternative suggestions
            alternatives = await self.doctor_service.find_alternative_slots(
                doctor_id, 
                appointment_datetime,
                settings.MAX_ALTERNATIVE_SLOTS
            )
            error_msg = f"Slot already booked for Dr. {doctor.name} at {appointment_datetime}"
            raise ValueError({
                "message": error_msg,
                "alternatives": alternatives
            })

        # Get or create patient (deduplication by phone number)
        patient = await self._get_or_create_patient(
            name=patient_name,
            phone=phone_number,
            email=email
        )

        # Create appointment
        appointment = Appointment(
            appointment_id=generate_appointment_id(),
            patient_id=patient.id,
            doctor_id=doctor_id,
            appointment_datetime=appointment_datetime,
            status=AppointmentStatus.CONFIRMED.value,
            appointment_type=appointment_type,
            notes=notes
        )

        self.db.add(appointment)
        
        try:
            await self.db.commit()
            await self.db.refresh(appointment)
            logger.info(
                f"Booked appointment {appointment.appointment_id} for {patient.name} "
                f"with Dr. {doctor.name} at {appointment_datetime}"
            )
            return appointment, True  # True = new patient
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"IntegrityError while booking: {e}")
            # Check if it's a duplicate booking error
            if "uq_active_doctor_slot" in str(e):
                alternatives = await self.doctor_service.find_alternative_slots(
                    doctor_id, 
                    appointment_datetime,
                    settings.MAX_ALTERNATIVE_SLOTS
                )
                raise ValueError({
                    "message": "Slot was just booked by another patient",
                    "alternatives": alternatives
                })
            raise

    async def cancel_appointment(
        self,
        appointment_id: str
    ) -> Appointment:
        """
        Cancel an appointment.
        
        Sets status to CANCELLED, freeing the slot.
        
        Raises:
            ValueError: If appointment not found or already cancelled
        """
        appointment = await self._get_appointment_by_id(appointment_id)
        
        if appointment.status == AppointmentStatus.CANCELLED.value:
            raise ValueError(f"Appointment {appointment_id} is already cancelled")
        
        if appointment.status == AppointmentStatus.COMPLETED.value:
            raise ValueError(f"Appointment {appointment_id} is already completed and cannot be cancelled")
        
        # Store old status for logging
        old_status = appointment.status
        appointment.status = AppointmentStatus.CANCELLED.value
        appointment.updated_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        logger.info(
            f"Cancelled appointment {appointment_id} "
            f"(was {old_status}) for patient {appointment.patient.name}"
        )
        
        return appointment

    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_datetime: datetime
    ) -> Tuple[Appointment, datetime]:
        """
        Reschedule an appointment to a new slot.
        
        Returns:
            Tuple of (updated_appointment, old_datetime)
        
        Raises:
            ValueError: If new slot is unavailable or appointment not found
        """
        # Get existing appointment
        appointment = await self._get_appointment_by_id(appointment_id)
        old_datetime = appointment.appointment_datetime
        
        if appointment.status == AppointmentStatus.CANCELLED.value:
            raise ValueError(f"Cannot reschedule a cancelled appointment")
        
        if appointment.status == AppointmentStatus.COMPLETED.value:
            raise ValueError(f"Cannot reschedule a completed appointment")
        
        # Check if new slot is available
        doctor_id = appointment.doctor_id
        doctor = await self.doctor_service.get_doctor_by_id(doctor_id)
        if not doctor:
            raise ValueError(f"Doctor not found")

        # Check if new slot conflicts
        existing = await self.db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime == new_datetime,
                Appointment.appointment_id != appointment_id,  # Exclude self
                Appointment.status.in_(ACTIVE_STATUSES)
            )
        )
        if existing.scalar_one_or_none():
            alternatives = await self.doctor_service.find_alternative_slots(
                doctor_id, 
                new_datetime,
                settings.MAX_ALTERNATIVE_SLOTS
            )
            raise ValueError({
                "message": f"New slot at {new_datetime} is already booked",
                "alternatives": alternatives
            })

        # Update appointment
        old_status = appointment.status
        appointment.appointment_datetime = new_datetime
        appointment.status = AppointmentStatus.RESCHEDULED.value
        appointment.updated_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        logger.info(
            f"Rescheduled appointment {appointment_id} "
            f"from {old_datetime} to {new_datetime} "
            f"(was {old_status})"
        )
        
        return appointment, old_datetime

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Fetch appointment by ID with patient and doctor loaded"""
        return await self._get_appointment_by_id(appointment_id)

    async def _get_appointment_by_id(self, appointment_id: str) -> Appointment:
        """Internal method to get appointment with relationships"""
        result = await self.db.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
        )
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        return appointment

    async def _get_or_create_patient(
        self,
        name: str,
        phone: str,
        email: Optional[str] = None
    ) -> Patient:
        """Get existing patient by phone or create new one"""
        # Check if patient exists
        result = await self.db.execute(
            select(Patient).where(Patient.phone_number == phone)
        )
        patient = result.scalar_one_or_none()
        
        if patient:
            # Update name if different (patient might have changed name)
            if patient.name != name:
                patient.name = name
                logger.info(f"Updated patient name from {patient.name} to {name}")
            return patient
        
        # Create new patient
        patient = Patient(
            name=name,
            phone_number=phone,
            email=email
        )
        self.db.add(patient)
        await self.db.flush()  # Get ID without committing
        logger.info(f"Created new patient: {name} ({phone})")
        return patient

    async def get_patient_appointments(
        self,
        phone_number: str,
        status: Optional[str] = None
    ) -> List[Appointment]:
        """Get all appointments for a patient by phone number"""
        result = await self.db.execute(
            select(Patient).where(Patient.phone_number == phone_number)
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return []
        
        query = select(Appointment).where(Appointment.patient_id == patient.id)
        
        if status:
            query = query.where(Appointment.status == status)
        
        query = query.order_by(Appointment.appointment_datetime.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()