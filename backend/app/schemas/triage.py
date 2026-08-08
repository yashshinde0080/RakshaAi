"""Triage API Schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional


class TriageVitals(BaseModel):
    heart_rate: Optional[float] = None          # bpm
    systolic_bp: Optional[float] = None         # mmHg
    spo2: Optional[float] = None                # %
    temperature_c: Optional[float] = None       # °C
    respiratory_rate: Optional[float] = None    # breaths/min
    gender: Optional[str] = None                # male | female | other (carried, not a rule input)


class TriageRedFlags(BaseModel):
    unresponsive: bool = False
    not_breathing: bool = False
    stroke_signs: bool = False
    chest_pain_severe: bool = False
    uncontrolled_bleeding: bool = False
    anaphylaxis_signs: bool = False
    seizure_active: bool = False


class TriageRequest(BaseModel):
    age_years: int = Field(ge=0, le=120)
    pain_score: int = Field(ge=0, le=10)
    symptom_duration_hours: float = Field(ge=0)
    vitals: TriageVitals = TriageVitals()
    red_flags: TriageRedFlags = TriageRedFlags()
    symptoms: List[str] = Field(default_factory=list)


class TriageValidation(BaseModel):
    validator_errors: List[str] = Field(default_factory=list)
    schema_ok: bool = True
    retries: int = 0


class TriageResponse(BaseModel):
    severity: int                                   # ESI level 1-5
    label: str
    is_emergency: bool                              # severity <= 2
    recommended_action: str
    reasons: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    source: str = "rules"                           # llm | llm_retry | rules
    escalated: bool = False                         # rule engine raised the LLM's level
    over_triage: bool = False                       # LLM rated more severe than the rule floor
    validation: TriageValidation = TriageValidation()
