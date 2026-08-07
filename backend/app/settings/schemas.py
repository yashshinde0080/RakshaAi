from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class LanguageOption(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    JAPANESE = "ja"
    CHINESE = "zh"
    HINDI = "hi"
    ARABIC = "ar"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"


class BaseStyleTone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    DETAILED = "detailed"
    ACADEMIC = "academic"
    CREATIVE = "creative"


class Characteristic(str, Enum):
    WARM = "warm"
    ENTHUSIASTIC = "enthusiastic"
    CYNICAL = "cynical"
    DEFAULT = "default"
    HUMOROUS = "humorous"
    DIRECT = "direct"
    EMPATHETIC = "empathetic"
    ANALYTICAL = "analytical"
    ENCOURAGING = "encouraging"
    SARCASTIC = "sarcastic"


class HeadersListsMode(str, Enum):
    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    MINIMAL = "minimal"


class ResponseLength(str, Enum):
    DEFAULT = "default"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    DETAILED = "detailed"


class AgentRole(str, Enum):
    DOCTOR = "doctor"
    ENGINEER = "engineer"
    LAWYER = "lawyer"
    TEACHER = "teacher"
    SCIENTIST = "scientist"
    WRITER = "writer"
    THERAPIST = "therapist"
    FINANCIAL_ADVISOR = "financial_advisor"
    CHEF = "chef"
    FITNESS_TRAINER = "fitness_trainer"
    DATA_ANALYST = "data_analyst"
    MARKETING_EXPERT = "marketing_expert"
    CYBERSECURITY_EXPERT = "cybersecurity_expert"
    HISTORIAN = "historian"
    PHILOSOPHER = "philosopher"
    CUSTOM = "custom"


class ContentFilterLevel(str, Enum):
    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


class DataRetentionPeriod(str, Enum):
    SESSION_ONLY = "session_only"
    ONE_DAY = "1_day"
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    NINETY_DAYS = "90_days"
    INDEFINITE = "indefinite"


# ──────────────────────────────────────────────
# SETTINGS MODELS
# ──────────────────────────────────────────────

class GeneralSettings(BaseModel):
    theme: ThemeMode = ThemeMode.DARK
    language: LanguageOption = LanguageOption.ENGLISH
    auto_start_backend: bool = True
    minimize_to_tray: bool = True
    show_status_bar: bool = True
    enable_notifications: bool = True
    startup_model: Optional[str] = None
    default_mode: str = "auto"
    max_context_length: int = Field(default=4096, ge=512, le=131072)
    stream_responses: bool = True
    show_token_speed: bool = True
    font_size: int = Field(default=14, ge=10, le=24)
    send_on_enter: bool = True
    enable_sounds: bool = False
    auto_save_sessions: bool = True


class AgentConfig(BaseModel):
    id: str
    name: str
    role: AgentRole
    description: str = ""
    system_instruction: str = ""
    is_active: bool = False
    icon: str = "bot"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=32768)
    enabled: bool = True


class PersonalizationSettings(BaseModel):
    base_style_tone: BaseStyleTone = BaseStyleTone.PROFESSIONAL
    characteristics: list[Characteristic] = [Characteristic.DEFAULT]
    headers_lists_mode: HeadersListsMode = HeadersListsMode.DEFAULT
    response_length: ResponseLength = ResponseLength.DEFAULT
    custom_instructions: str = ""
    user_context: str = ""
    preferred_name: str = ""
    profession: str = ""
    interests: list[str] = []


class DataControlsSettings(BaseModel):
    save_chat_history: bool = True
    data_retention: DataRetentionPeriod = DataRetentionPeriod.THIRTY_DAYS
    allow_model_training: bool = False
    export_format: str = "json"
    auto_delete_sessions: bool = False
    encrypt_local_data: bool = True
    log_api_requests: bool = False
    clear_on_exit: bool = False


class SecuritySettings(BaseModel):
    require_password: bool = False
    password_hash: Optional[str] = None
    encrypt_models: bool = True
    bind_localhost_only: bool = True
    api_port: int = Field(default=8000, ge=1024, le=65535)
    enable_cors: bool = False
    allowed_origins: list[str] = ["http://localhost:3000"]
    session_timeout_minutes: int = Field(default=0, ge=0, le=1440)
    audit_logging: bool = True
    disable_external_plugins: bool = True
    max_concurrent_requests: int = Field(default=4, ge=1, le=32)


class ParentalControlsSettings(BaseModel):
    enabled: bool = False
    pin_hash: Optional[str] = None
    content_filter_level: ContentFilterLevel = ContentFilterLevel.OFF
    block_explicit_content: bool = False
    restrict_topics: list[str] = []
    max_session_duration_minutes: int = Field(default=0, ge=0, le=480)
    allowed_models: list[str] = []
    disable_custom_instructions: bool = False
    require_pin_for_settings: bool = False
    activity_log: bool = False


class ProjectSettings(BaseModel):
    project_name: str = "SovereignAI"
    project_version: str = "1.0.0"
    project_description: str = "A powerful AI platform with local and cloud model support."
    author: str = "Sovereign Team"
    github_repo: str = "https://github.com/SovereignAI/Sovereign"
    environment: str = "development"
    api_endpoint: str = "http://localhost:8000"
    documentation_url: str = "https://docs.sovereign.ai"



class FullSettings(BaseModel):
    general: GeneralSettings = GeneralSettings()
    agents: list[AgentConfig] = []
    personalization: PersonalizationSettings = PersonalizationSettings()
    data_controls: DataControlsSettings = DataControlsSettings()
    security: SecuritySettings = SecuritySettings()
    parental_controls: ParentalControlsSettings = ParentalControlsSettings()
    project: ProjectSettings = ProjectSettings()



class SettingsUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_section: str