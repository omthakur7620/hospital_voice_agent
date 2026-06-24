"""
Appointment API endpoints.

POST /book-appointment - Book a new appointment
POST /cancel-appointment - Cancel an existing appointment
POST /reschedule-appointment - Reschedule an existing appointment
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.appointment_service import AppointmentService
from app.schemas import (
    BookAppointmentRequest,
    CancelAppointmentRequest,
    RescheduleAppointmentRequest,
    BookingResponse,
    CancelResponse,
    RescheduleResponse,
    SlotUnavailableResponse,
    AlternativeSlot,
    ErrorResponse
)
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Appointments"])


@router.post(
    "/book-appointment",
    response_model=BookingResponse,
    responses={
        400: {"model": SlotUnavailableResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def book_appointment(
    request: BookAppointmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Book a new appointment.
    
    Steps:
    1. Validate doctor exists and is active
    2. Check doctor works on requested day
    3. Check slot is in doctor's available slots
    4. Check slot is not already booked
    5. Get or create patient (deduplication by phone)
    6. Create appointment with UNIQUE constraint
    
    If slot is unavailable, returns alternative suggestions.
    """
    try:
        service = AppointmentService(db)
        
        # Book the appointment
        appointment, is_new_patient = await service.book_appointment(
            patient_name=request.patient_name,
            phone_number=request.phone_number,
            doctor_id=UUID(request.doctor_id),
            appointment_datetime=request.appointment_datetime,
            appointment_type=request.appointment_type or "New Consultation",
            email=request.email,
            notes=request.notes
        )
        
        # Format response
        response = BookingResponse(
            status="success",
            appointment_id=appointment.appointment_id,
            message=f"Appointment confirmed with Dr. {appointment.doctor.name}",
            patient_name=appointment.patient.name,
            doctor_name=appointment.doctor.name,
            appointment_datetime=appointment.appointment_datetime.isoformat(),
            appointment_type=appointment.appointment_type
        )
        
        logger.info(
            f"Booking successful: {appointment.appointment_id} "
            f"for {request.patient_name}"
        )
        
        return response
    
    except ValueError as e:
        # Check if error has alternatives (slot unavailable)
        if isinstance(e.args[0], dict) and "alternatives" in e.args[0]:
            error_data = e.args[0]
            alternatives = [
                AlternativeSlot(
                    doctor_id=alt["doctor_id"],
                    doctor_name=alt["doctor_name"],
                    datetime=alt["datetime"].isoformat(),
                    reason=alt["reason"]
                )
                for alt in error_data.get("alternatives", [])
            ]
            
            raise HTTPException(
                status_code=400,
                detail=SlotUnavailableResponse(
                    status="error",
                    message=error_data.get("message", "Slot unavailable"),
                    requested_slot=request.appointment_datetime.isoformat(),
                    alternatives=alternatives
                ).model_dump()
            )
        
        # Generic validation error
        logger.warning(f"Booking validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Booking error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to book appointment"}
        )


@router.post(
    "/cancel-appointment",
    response_model=CancelResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def cancel_appointment(
    request: CancelAppointmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an existing appointment.
    
    Sets status to CANCELLED, freeing the slot for rebooking.
    
    Cannot cancel:
    - Already cancelled appointments
    - Completed appointments
    - Non-existent appointments
    """
    try:
        service = AppointmentService(db)
        appointment = await service.cancel_appointment(request.appointment_id)
        
        response = CancelResponse(
            status="success",
            appointment_id=appointment.appointment_id,
            message=f"Appointment cancelled successfully",
            cancelled_at=datetime.now().isoformat()
        )
        
        logger.info(f"Cancellation successful: {appointment.appointment_id}")
        return response
    
    except ValueError as e:
        logger.warning(f"Cancellation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Unexpected cancellation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to cancel appointment"}
        )


@router.post(
    "/reschedule-appointment",
    response_model=RescheduleResponse,
    responses={
        400: {"model": SlotUnavailableResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def reschedule_appointment(
    request: RescheduleAppointmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reschedule an existing appointment.
    
    Steps:
    1. Find existing appointment
    2. Check new slot availability
    3. Update appointment with new datetime
    4. Set status to RESCHEDULED
    
    If new slot is unavailable, returns alternative suggestions.
    """
    try:
        service = AppointmentService(db)
        
        # Get existing appointment for logging
        old_appointment = await service.get_appointment_by_id(
            request.appointment_id
        )
        if not old_appointment:
            raise HTTPException(
                status_code=404,
                detail={"status": "error", "message": "Appointment not found"}
            )
        
        old_datetime = old_appointment.appointment_datetime
        
        # Reschedule
        appointment, old_dt = await service.reschedule_appointment(
            appointment_id=request.appointment_id,
            new_datetime=request.new_datetime
        )
        
        response = RescheduleResponse(
            status="success",
            appointment_id=appointment.appointment_id,
            old_datetime=old_dt.isoformat(),
            new_datetime=appointment.appointment_datetime.isoformat(),
            message=f"Appointment rescheduled from {old_dt} to {appointment.appointment_datetime}"
        )
        
        logger.info(
            f"Reschedule successful: {appointment.appointment_id} "
            f"from {old_dt} to {appointment.appointment_datetime}"
        )
        
        return response
    
    except ValueError as e:
        # Check if error has alternatives (slot unavailable)
        if isinstance(e.args[0], dict) and "alternatives" in e.args[0]:
            error_data = e.args[0]
            alternatives = [
                AlternativeSlot(
                    doctor_id=alt["doctor_id"],
                    doctor_name=alt["doctor_name"],
                    datetime=alt["datetime"].isoformat(),
                    reason=alt["reason"]
                )
                for alt in error_data.get("alternatives", [])
            ]
            
            raise HTTPException(
                status_code=400,
                detail=SlotUnavailableResponse(
                    status="error",
                    message=error_data.get("message", "Slot unavailable"),
                    requested_slot=request.new_datetime.isoformat(),
                    alternatives=alternatives
                ).model_dump()
            )
        
        logger.warning(f"Reschedule validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Reschedule error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Failed to reschedule appointment"}
        )


# Import datetime for timestamp
from datetime import datetime