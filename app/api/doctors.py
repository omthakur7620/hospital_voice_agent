"""
Doctor API endpoints.

GET /doctors - List doctors with optional department filter
GET /slots - Get available slots for a doctor on a specific date
"""

from datetime import date as date_type
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.doctor_service import DoctorService
from app.schemas import (
    DoctorResponse,
    SlotResponse,
    SlotAvailabilityRequest,
    ErrorResponse
)
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Doctors"])


@router.get(
    "/doctors",
    response_model=list[DoctorResponse],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_doctors(
    department: Optional[str] = Query(None, description="Filter by department"),
    name: Optional[str] = Query(None, description="Filter by doctor name (partial)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all doctors with optional filters.
    
    Returns doctors with their available slots and working days.
    Used by Vapi AI to list doctors by department.
    """
    try:
        service = DoctorService(db)
        doctors = await service.get_doctors_by_department(
            department=department,
            name=name
        )
        
        # Format response for Vapi AI
        return [DoctorResponse.from_orm_with_formatting(d) for d in doctors]
    
    except Exception as e:
        logger.error(f"Error fetching doctors: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to fetch doctors"}
        )


@router.get(
    "/slots",
    response_model=SlotResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_available_slots(
    doctor_id: str = Query(..., description="Doctor UUID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available slots for a doctor on a specific date.
    
    Checks:
    1. Doctor exists and is active
    2. Doctor works on this day
    3. Slot is in doctor's base schedule
    4. Slot is not already booked
    
    Returns available slots in human-readable format.
    """
    try:
        # Parse and validate request - using check_date parameter
        request = SlotAvailabilityRequest(check_date=date, doctor_id=doctor_id)
        
        service = DoctorService(db)
        doctor = await service.get_doctor_by_id(UUID(doctor_id))
        
        if not doctor:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Doctor not found"}
            )
        
        # Get available slots using check_date
        available_slots, booked_slots = await service.get_available_slots(
            UUID(doctor_id),
            request.check_date
        )
        
        # Format response
        response = SlotResponse.create(
            doctor=doctor,
            date_obj=request.check_date,
            available_times=available_slots,
            booked_count=len(booked_slots)
        )
        
        logger.info(
            f"Slots fetched for {doctor.name} on {request.check_date}: "
            f"{len(available_slots)} available, {len(booked_slots)} booked"
        )
        
        return response
    
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Error fetching slots: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to fetch available slots"}
        )