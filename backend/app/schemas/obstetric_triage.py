"""Obstetric (LaQshya) Triage API Schemas.

JSON contract for the LaQshya SOP 2018 binary-trigger input/output. All fields
optional — the rule engine treats a missing value as "no trigger", which is the
safe direction for a binary system (a missing reading cannot fabricate an
escalation; it can only under-trigger, so the front gate enforces what must be
present per facility policy).
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class MotherInput(BaseModel):
    temp_c: Optional[float] = None                    # >=38 triggers danger + antibiotic
    systolic_bp: Optional[float] = None               # mmHg
    diastolic_bp: Optional[float] = None              # mmHg
    fast_feeble_pulse: bool = False                   # shock criterion (all 3 needed)
    cold_moist_skin: bool = False                     # shock criterion (all 3 needed)
    foul_smelling_discharge: bool = False             # antibiotic trigger


class LabourInput(BaseModel):
    rom_hours: Optional[float] = None                 # rupture of membranes duration
    rom_with_labour: bool = False                     # ROM >18h with labour vs >12h without
    rom_before_37wks: bool = False                    # antibiotic trigger
    labour_hours: Optional[float] = None              # >24h -> antibiotic trigger
    obstructed_labour: bool = False                   # antibiotic trigger


class DangerSigns(BaseModel):
    vaginal_bleeding: bool = False
    severe_abdominal_pain: bool = False
    severe_headache_or_blurred_vision: bool = False
    difficulty_breathing: bool = False
    convulsions: bool = False
    hx_heart_disease_major_illness: bool = False


class PreeclampsiaInput(BaseModel):
    proteinuria: Optional[str] = None                 # "0" | "trace" | "1" | "2" | "3" | "4"
    epigastric_pain: bool = False
    oliguria_ml_24h: Optional[float] = None           # <400 -> severe pre-eclampsia symptom


class PPHInput(BaseModel):
    blood_loss_ml: Optional[float] = None             # >=500 immediate protocol; >350 + bleeding -> obstetrician
    pad_soaked_minutes: Optional[float] = None       # <5 -> immediate PPH protocol
    retained_placenta_hours: Optional[float] = None  # >1 -> obstetrician
    continued_bleeding: bool = False


class FetalInput(BaseModel):
    fhr_bpm: Optional[float] = None                   # <120 or >160 -> fetal distress
    meconium_stained_liquor: bool = False


class BabyInput(BaseModel):
    rr_per_min: Optional[float] = None                # >60 or <30 -> danger
    chest_indrawing: bool = False
    grunting: bool = False
    convulsions: bool = False
    lethargic_or_irritable: bool = False
    temp_c: Optional[float] = None                    # <36 or >38 -> danger
    excessive_crying: bool = False


class PartographInput(BaseModel):
    cervix_dilation_cm: Optional[float] = None       # start partograph at >=4cm (context only)
    alert_line_crossed: bool = False                 # -> MO review
    action_line_crossed: bool = False                # -> obstetrician
    no_progress_hours: Optional[float] = None        # >=8 -> refer FRU


class ObstetricTriageRequest(BaseModel):
    gestation_weeks: Optional[int] = Field(default=None, ge=0, le=45)
    mother: MotherInput = MotherInput()
    labour: LabourInput = LabourInput()
    danger_signs: DangerSigns = DangerSigns()
    preeclampsia: PreeclampsiaInput = PreeclampsiaInput()
    pph: PPHInput = PPHInput()
    fetal: FetalInput = FetalInput()
    baby: BabyInput = BabyInput()
    partograph: PartographInput = PartographInput()


class ObstetricTriageResponse(BaseModel):
    escalation_level: int                             # 0 routine | 1 MO | 2 obstetrician | 3 refer FRU
    label: str
    next_step: str
    is_urgent: bool                                   # level >= 2
    reasons: List[str] = Field(default_factory=list)
    source: str = "rules"
