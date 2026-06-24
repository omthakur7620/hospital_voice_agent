"""
Pydantic schemas for request/response validation.

All API endpoints use these schemas to validate input and format output.
This ensures:
1. Type safety at the API boundary
2. Clean, documented response structures for Vapi AI
3. Automatic OpenAPI documentation
4. Consistent error responses

Design principle: Separate request schemas (what client sends) from
response schemas (what client receives) for flexibility.
"""

from datetime import date as date_type, datetime, time
from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


# ============ Request Schemas ============

class DoctorQueryParams(BaseModel):
    """Query parameters for GET /doctors"""
    department: Optional[str] = Field(None, description="Filter by department name")
    name: Optional[str] = Field(None, description="Filter by doctor name (partial match)")


class SlotAvailabilityRequest(BaseModel):
    """Query parameters for GET /slots"""
    doctor_id: str = Field(..., description="UUID of the doctor")
    check_date: date_type = Field(..., alias="date", description="Date to check availability (YYYY-MM-DD)")
    
    @field_validator('check_date')
    @classmethod
    def validate_date(cls, v: date_type) -> date_type:
        """Ensure date is not in the past"""
        if v < date_type.today():
            raise ValueError("Cannot check availability for past dates")
        return v


class BookAppointmentRequest(BaseModel):
    """Request body for POST /book-appointment"""
    patient_name: str = Field(..., min_length=2, max_length=150)
    phone_number: str = Field(..., description="Indian phone number with country code")
    doctor_id: str = Field(..., description="UUID of the doctor")
    appointment_datetime: datetime = Field(..., description="ISO format with timezone")
    appointment_type: Optional[str] = Field("New Consultation", max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate Indian phone number format"""
        # Remove any whitespace
        v = v.strip()
        # Basic validation: +91 followed by 10 digits, or 10 digits
        if not re.match(r'^(\+91)?[6-9]\d{9}$', v):
            raise ValueError("Invalid Indian phone number. Use format: +91XXXXXXXXXX or 10 digits")
        return v
    
    @field_validator('appointment_datetime')
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        """Ensure appointment is not in the past"""
        if v < datetime.now(v.tzinfo):
            raise ValueError("Cannot book appointments in the past")
        return v


class CancelAppointmentRequest(BaseModel):
    """Request body for POST /cancel-appointment"""
    appointment_id: str = Field(..., description="Appointment ID (e.g., APT-20250115-A7F3B2)")


class RescheduleAppointmentRequest(BaseModel):
    """Request body for POST /reschedule-appointment"""
    appointment_id: str = Field(..., description="Appointment ID to reschedule")
    new_datetime: datetime = Field(..., description="New appointment date and time (ISO format)")
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('new_datetime')
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        """Ensure reschedule is not in the past"""
        if v < datetime.now(v.tzinfo):
            raise ValueError("Cannot reschedule to past date/time")
        return v


# ============ Response Schemas ============

class DoctorResponse(BaseModel):
    """Response for GET /doctors"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    department: str
    specialization: Optional[str] = None
    location: Optional[str] = None
    available_slots: List[str]  # Human-readable format: ["10:00 AM", "11:30 AM"]
    working_days: List[str]     # Human-readable: ["Monday", "Tuesday"]
    
    @classmethod
    def from_orm_with_formatting(cls, doctor: Any) -> "DoctorResponse":
        """Create response with human-readable formatting"""
        # Convert working days integers to names
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        working_days_human = [day_names[d] for d in doctor.working_days if 0 <= d < 7]
        
        # Convert time objects to 12-hour format strings
        slots_human = []
        for slot_time in doctor.available_slots:
            # Convert time to 12-hour format
            hour = slot_time.hour
            minute = slot_time.minute
            am_pm = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12
            slots_human.append(f"{hour_12}:{minute:02d} {am_pm}")
        
        return cls(
            id=str(doctor.id),
            name=doctor.name,
            department=doctor.department,
            specialization=doctor.specialization,
            location=doctor.location,
            available_slots=slots_human,
            working_days=working_days_human
        )


class SlotResponse(BaseModel):
    """Response for GET /slots"""
    model_config = ConfigDict(from_attributes=True)
    
    doctor_id: str
    doctor_name: str
    department: str
    date: str  # YYYY-MM-DD
    available_slots: List[str]  # Human-readable: ["10:00 AM", "11:30 AM"]
    total_slots: int
    booked_slots: int
    timezone: str = "Asia/Kolkata"
    
    @classmethod
    def create(
        cls, 
        doctor: Any, 
        date_obj: date_type, 
        available_times: List[time], 
        booked_count: int
    ) -> "SlotResponse":
        """Create response with formatting"""
        # Convert time objects to human-readable
        slots_human = []
        for slot_time in available_times:
            hour = slot_time.hour
            minute = slot_time.minute
            am_pm = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12
            slots_human.append(f"{hour_12}:{minute:02d} {am_pm}")
        
        return cls(
            doctor_id=str(doctor.id),
            doctor_name=doctor.name,
            department=doctor.department,
            date=date_obj.isoformat(),
            available_slots=slots_human,
            total_slots=len(doctor.available_slots),
            booked_slots=booked_count
        )


class BookingResponse(BaseModel):
    """Response for POST /book-appointment"""
    status: str
    appointment_id: str
    message: str
    patient_name: str
    doctor_name: str
    appointment_datetime: str  # ISO format
    appointment_type: Optional[str] = None


class CancelResponse(BaseModel):
    """Response for POST /cancel-appointment"""
    status: str = "success"
    appointment_id: str
    message: str
    cancelled_at: str  # ISO timestamp


class RescheduleResponse(BaseModel):
    """Response for POST /reschedule-appointment"""
    status: str = "success"
    appointment_id: str
    old_datetime: str  # ISO format
    new_datetime: str  # ISO format
    message: str


class AlternativeSlot(BaseModel):
    """Alternative slot suggestion"""
    doctor_id: str
    doctor_name: str
    datetime: str  # ISO format
    reason: str  # Why this is suggested


class SlotUnavailableResponse(BaseModel):
    """Response when requested slot is unavailable"""
    status: str = "error"
    message: str = "Requested slot is not available"
    requested_slot: str  # ISO format
    alternatives: List[AlternativeSlot]


class ErrorResponse(BaseModel):
    """Standard error response"""
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============ Vapi AI Optimized Responses ============

class VapiSlotResponse(BaseModel):
    """Optimized slot response for Vapi AI function calling"""
    status: str
    data: SlotResponse
    ai_message: str  # Natural language message for Vapi to speak


class VapiBookingResponse(BaseModel):
    """Optimized booking response for Vapi AI function calling"""
    status: str
    data: BookingResponse
    ai_message: str  # Natural language message for Vapi to speak


class VapiCancelResponse(BaseModel):
    """Optimized cancel response for Vapi AI function calling"""
    status: str
    data: CancelResponse
    ai_message: str  # Natural language message for Vapi to speak