from fastapi import APIRouter, HTTPException, Query
from .schemas import (
    GeneralSettings,
    AgentConfig,
    PersonalizationSettings,
    DataControlsSettings,
    SecuritySettings,
    ParentalControlsSettings,
    ProjectSettings,
    SettingsUpdateResponse,
)

from .service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])

service = SettingsService()


# ──────────────────────────────────────────────
# FULL SETTINGS
# ──────────────────────────────────────────────

@router.get("/")
async def get_all_settings():
    """Get all settings including agents."""
    return service.get_full_settings()


@router.post("/reset", response_model=SettingsUpdateResponse)
async def reset_all_settings():
    """Reset all settings to defaults."""
    success = service.reset_all_settings()
    return SettingsUpdateResponse(
        success=success,
        message="All settings reset to defaults" if success else "Reset failed",
        updated_section="all"
    )


# ──────────────────────────────────────────────
# GENERAL
# ──────────────────────────────────────────────

@router.get("/general")
async def get_general_settings():
    return service.get_general()


@router.put("/general", response_model=SettingsUpdateResponse)
async def update_general_settings(settings: GeneralSettings):
    success = service.update_general(settings)
    return SettingsUpdateResponse(
        success=success,
        message="General settings updated" if success else "Update failed",
        updated_section="general"
    )


# ──────────────────────────────────────────────
# PERSONALIZATION
# ──────────────────────────────────────────────

@router.get("/personalization")
async def get_personalization_settings():
    return service.get_personalization()


@router.put("/personalization", response_model=SettingsUpdateResponse)
async def update_personalization_settings(settings: PersonalizationSettings):
    success = service.update_personalization(settings)
    return SettingsUpdateResponse(
        success=success,
        message="Personalization settings updated" if success else "Update failed",
        updated_section="personalization"
    )


@router.get("/system-prompt")
async def get_system_prompt():
    """Get the constructed system prompt from personalization + active agent."""
    prompt = service.get_system_prompt()
    return {"system_prompt": prompt}


# ──────────────────────────────────────────────
# DATA CONTROLS
# ──────────────────────────────────────────────

@router.get("/data-controls")
async def get_data_controls():
    return service.get_data_controls()


@router.put("/data-controls", response_model=SettingsUpdateResponse)
async def update_data_controls(settings: DataControlsSettings):
    success = service.update_data_controls(settings)
    return SettingsUpdateResponse(
        success=success,
        message="Data controls updated" if success else "Update failed",
        updated_section="data_controls"
    )


# ──────────────────────────────────────────────
# SECURITY
# ──────────────────────────────────────────────

@router.get("/security")
async def get_security_settings():
    data = service.get_security()
    # Never return password hash to frontend
    data.pop("password_hash", None)
    return data


@router.put("/security", response_model=SettingsUpdateResponse)
async def update_security_settings(settings: SecuritySettings):
    success = service.update_security(settings)
    return SettingsUpdateResponse(
        success=success,
        message="Security settings updated" if success else "Update failed",
        updated_section="security"
    )


@router.post("/security/set-password", response_model=SettingsUpdateResponse)
async def set_password(password: str):
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    success = service.set_password(password)
    return SettingsUpdateResponse(
        success=success,
        message="Password set" if success else "Failed to set password",
        updated_section="security"
    )


@router.post("/security/verify-password")
async def verify_password(password: str):
    valid = service.verify_password(password)
    return {"valid": valid}


# ──────────────────────────────────────────────
# PARENTAL CONTROLS
# ──────────────────────────────────────────────

@router.get("/parental-controls")
async def get_parental_controls():
    data = service.get_parental_controls()
    data.pop("pin_hash", None)
    return data


@router.put("/parental-controls", response_model=SettingsUpdateResponse)
async def update_parental_controls(settings: ParentalControlsSettings):
    success = service.update_parental_controls(settings)
    return SettingsUpdateResponse(
        success=success,
        message="Parental controls updated" if success else "Update failed",
        updated_section="parental_controls"
    )


@router.post("/parental-controls/set-pin", response_model=SettingsUpdateResponse)
async def set_parental_pin(pin: str):
    if len(pin) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 digits")
    success = service.set_parental_pin(pin)
    return SettingsUpdateResponse(
        success=success,
        message="Parental PIN set" if success else "Failed to set PIN",
        updated_section="parental_controls"
    )


@router.post("/parental-controls/verify-pin")
async def verify_parental_pin(pin: str):
    valid = service.verify_parental_pin(pin)
    return {"valid": valid}


# ──────────────────────────────────────────────
# PROJECT
# ──────────────────────────────────────────────

@router.get("/project")
async def get_project_settings():
    return service.get_project()


@router.put("/project", response_model=SettingsUpdateResponse)
async def update_project_settings(settings: ProjectSettings):
    success = service.update_project(settings)
    return SettingsUpdateResponse(
        success=success,
        message="Project settings updated" if success else "Update failed",
        updated_section="project"
    )



# ──────────────────────────────────────────────
# AGENTS
# ──────────────────────────────────────────────

@router.get("/agents")
async def get_all_agents():
    return service.get_all_agents()


@router.get("/agents/active")
async def get_active_agent():
    agent = service.get_active_agent()
    return agent if agent else {"active": False}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/agents", response_model=SettingsUpdateResponse)
async def create_agent(agent: AgentConfig):
    success = service.create_agent(agent)
    if not success:
        raise HTTPException(status_code=409, detail="Agent with this ID already exists")
    return SettingsUpdateResponse(
        success=True,
        message=f"Agent '{agent.name}' created",
        updated_section="agents"
    )


@router.put("/agents/{agent_id}", response_model=SettingsUpdateResponse)
async def update_agent(agent_id: str, agent: AgentConfig):
    success = service.update_agent(agent_id, agent)
    return SettingsUpdateResponse(
        success=success,
        message=f"Agent updated" if success else "Update failed",
        updated_section="agents"
    )


@router.delete("/agents/{agent_id}", response_model=SettingsUpdateResponse)
async def delete_agent(agent_id: str):
    success = service.delete_agent(agent_id)
    return SettingsUpdateResponse(
        success=success,
        message="Agent deleted" if success else "Delete failed",
        updated_section="agents"
    )


@router.post("/agents/{agent_id}/activate", response_model=SettingsUpdateResponse)
async def activate_agent(agent_id: str):
    agent = service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    success = service.activate_agent(agent_id)
    return SettingsUpdateResponse(
        success=success,
        message=f"Agent '{agent['name']}' activated" if success else "Activation failed",
        updated_section="agents"
    )


@router.post("/agents/deactivate", response_model=SettingsUpdateResponse)
async def deactivate_all_agents():
    success = service.deactivate_agents()
    return SettingsUpdateResponse(
        success=success,
        message="All agents deactivated" if success else "Deactivation failed",
        updated_section="agents"
    )


# ──────────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(limit: int = Query(default=100, ge=1, le=1000)):
    return service.get_audit_log(limit)