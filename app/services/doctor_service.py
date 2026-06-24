"""
Doctor service - handles doctor-related business logic.

Responsible for:
- Fetching doctors by department
- Checking doctor availability on specific dates
- Computing available slots (base slots - booked slots)
- Providing alternative slot suggestions
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Doctor, Appointment, AppointmentStatus, ACTIVE_STATUSES
from app.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class DoctorService:
    """Service for doctor-related operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_doctors_by_department(
        self, 
        department: Optional[str] = None,
        name: Optional[str] = None
    ) -> List[Doctor]:
        """
        Fetch doctors with optional filters.
        
        Args:
            department: Filter by department name (case-insensitive)
            name: Filter by doctor name (partial match, case-insensitive)
        
        Returns:
            List of Doctor objects
        """
        query = select(Doctor).where(Doctor.is_active == True)
        
        if department:
            query = query.where(Doctor.department.ilike(f"%{department}%"))
        
        if name:
            query = query.where(Doctor.name.ilike(f"%{name}%"))
        
        query = query.order_by(Doctor.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_doctor_by_id(self, doctor_id: UUID) -> Optional[Doctor]:
        """Fetch a single doctor by UUID"""
        result = await self.db.execute(
            select(Doctor).where(
                Doctor.id == doctor_id,
                Doctor.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_available_slots(
        self, 
        doctor_id: UUID, 
        check_date: date
    ) -> Tuple[List[time], List[time]]:
        """
        Get available slots for a doctor on a specific date.
        
        Returns:
            Tuple of (available_slots, booked_slots)
        """
        doctor = await self.get_doctor_by_id(doctor_id)
        if not doctor:
            return [], []

        # Check if doctor works on this day
        day_of_week = check_date.weekday()  # 0=Monday, 6=Sunday
        if day_of_week not in doctor.working_days:
            logger.info(f"Doctor {doctor.name} doesn't work on {check_date}")
            return [], []

        # Get all slots for this doctor
        base_slots = doctor.available_slots
        if not base_slots:
            return [], []

        # Get booked appointments for this doctor on this date
        start_datetime = datetime.combine(check_date, time.min)
        end_datetime = datetime.combine(check_date, time.max)
        
        booked_result = await self.db.execute(
            select(Appointment.appointment_time)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == check_date,
                Appointment.status.in_(ACTIVE_STATUSES)
            )
        )
        booked_times = [row[0] for row in booked_result.all()]
        
        # Compute available slots (base slots - booked slots)
        available = [slot for slot in base_slots if slot not in booked_times]
        
        logger.info(
            f"Doctor {doctor.name} on {check_date}: "
            f"{len(available)} available, {len(booked_times)} booked"
        )
        
        return available, booked_times

    async def find_alternative_slots(
        self,
        doctor_id: UUID,
        requested_datetime: datetime,
        max_alternatives: int = 3
    ) -> List[dict]:
        """
        Find alternative slots when requested slot is unavailable.
        
        Strategy:
        1. Same doctor, same day: ±1 slot from requested time
        2. Same doctor, next working day: same slot time
        3. Same department, other doctor: first available slot
        """
        alternatives = []
        doctor = await self.get_doctor_by_id(doctor_id)
        if not doctor:
            return alternatives

        requested_date = requested_datetime.date()
        requested_time = requested_datetime.time()
        
        # Strategy 1: Same doctor, same day, nearby slots
        available_slots, _ = await self.get_available_slots(
            doctor_id, requested_date
        )
        
        if available_slots:
            # Find slots near requested time
            nearby = self._find_nearby_slots(
                available_slots, 
                requested_time,
                max_alternatives // 2
            )
            for slot_time in nearby:
                alt_datetime = datetime.combine(requested_date, slot_time)
                alternatives.append({
                    "doctor_id": str(doctor.id),
                    "doctor_name": doctor.name,
                    "datetime": alt_datetime,
                    "reason": f"Same day, nearby time with {doctor.name}"
                })
        
        # Strategy 2: Same doctor, next working day
        if len(alternatives) < max_alternatives:
            next_date = requested_date + timedelta(days=1)
            attempts = 0
            while attempts < 7 and len(alternatives) < max_alternatives:
                day_of_week = next_date.weekday()
                if day_of_week in doctor.working_days:
                    # Check if requested time is available on this day
                    avail, _ = await self.get_available_slots(doctor.id, next_date)
                    if requested_time in avail:
                        alt_datetime = datetime.combine(next_date, requested_time)
                        alternatives.append({
                            "doctor_id": str(doctor.id),
                            "doctor_name": doctor.name,
                            "datetime": alt_datetime,
                            "reason": f"Next working day with {doctor.name}"
                        })
                        break
                next_date += timedelta(days=1)
                attempts += 1
        
        # Strategy 3: Same department, other doctors
        if len(alternatives) < max_alternatives:
            other_doctors = await self.get_doctors_by_department(
                department=doctor.department
            )
            for other in other_doctors:
                if other.id == doctor.id:
                    continue
                if len(alternatives) >= max_alternatives:
                    break
                
                # Check if this doctor has any slot on requested date
                avail, _ = await self.get_available_slots(other.id, requested_date)
                if avail:
                    alt_datetime = datetime.combine(requested_date, avail[0])
                    alternatives.append({
                        "doctor_id": str(other.id),
                        "doctor_name": other.name,
                        "datetime": alt_datetime,
                        "reason": f"Alternative doctor in {doctor.department} department"
                    })
        
        return alternatives[:max_alternatives]

    def _find_nearby_slots(
        self, 
        available_slots: List[time], 
        target_time: time,
        max_results: int
    ) -> List[time]:
        """Find slots closest to target time"""
        if not available_slots:
            return []
        
        # Convert to minutes for comparison
        target_minutes = target_time.hour * 60 + target_time.minute
        slot_minutes = [(s, s.hour * 60 + s.minute) for s in available_slots]
        
        # Sort by proximity to target time
        sorted_slots = sorted(
            slot_minutes,
            key=lambda x: abs(x[1] - target_minutes)
        )
        
        # Return the closest slots, excluding the exact target (already booked)
        return [s[0] for s in sorted_slots[:max_results]]