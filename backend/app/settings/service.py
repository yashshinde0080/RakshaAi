import bcrypt
from typing import Optional
from .database import SettingsDatabase
from .schemas import (
    GeneralSettings,
    AgentConfig,
    PersonalizationSettings,
    DataControlsSettings,
    SecuritySettings,
    ParentalControlsSettings,
    ProjectSettings,
    FullSettings,
)



class SettingsService:
    def __init__(self, db_path: Optional[str] = None):
        self.db = SettingsDatabase(db_path)

    # ── Full Settings ──

    def get_full_settings(self) -> dict:
        all_settings = self.db.get_all_settings()
        agents = self.db.get_all_agents()
        all_settings["agents"] = agents
        return all_settings

    def reset_all_settings(self) -> bool:
        return self.db.reset_all()

    # ── General ──

    def get_general(self) -> dict:
        data = self.db.get_section("general")
        if data is None:
            return GeneralSettings().model_dump()
        return data

    def update_general(self, settings: GeneralSettings) -> bool:
        return self.db.update_section("general", settings.model_dump())

    # ── Personalization ──

    def get_personalization(self) -> dict:
        data = self.db.get_section("personalization")
        if data is None:
            return PersonalizationSettings().model_dump()
        return data

    def update_personalization(self, settings: PersonalizationSettings) -> bool:
        return self.db.update_section("personalization", settings.model_dump())

    # ── Data Controls ──

    def get_data_controls(self) -> dict:
        data = self.db.get_section("data_controls")
        if data is None:
            return DataControlsSettings().model_dump()
        return data

    def update_data_controls(self, settings: DataControlsSettings) -> bool:
        return self.db.update_section("data_controls", settings.model_dump())

    # ── Security ──

    def get_security(self) -> dict:
        data = self.db.get_section("security")
        if data is None:
            return SecuritySettings().model_dump()
        return data

    def update_security(self, settings: SecuritySettings) -> bool:
        return self.db.update_section("security", settings.model_dump())

    def set_password(self, password: str) -> bool:
        security = self.get_security()
        security["require_password"] = True
        security["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return self.db.update_section("security", security)

    def verify_password(self, password: str) -> bool:
        security = self.get_security()
        if not security.get("require_password"):
            return True
        stored_hash = security.get("password_hash", "").encode()
        return bcrypt.checkpw(password.encode(), stored_hash)

    # ── Parental Controls ──

    def get_parental_controls(self) -> dict:
        data = self.db.get_section("parental_controls")
        if data is None:
            return ParentalControlsSettings().model_dump()
        return data

    def update_parental_controls(self, settings: ParentalControlsSettings) -> bool:
        return self.db.update_section("parental_controls", settings.model_dump())

    def set_parental_pin(self, pin: str) -> bool:
        parental = self.get_parental_controls()
        parental["pin_hash"] = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
        parental["require_pin_for_settings"] = True
        return self.db.update_section("parental_controls", parental)

    def verify_parental_pin(self, pin: str) -> bool:
        parental = self.get_parental_controls()
        stored_hash = parental.get("pin_hash", "")
        if not stored_hash:
            return True
        return bcrypt.checkpw(pin.encode(), stored_hash.encode())

    # ── Project ──

    def get_project(self) -> dict:
        data = self.db.get_section("project")
        if data is None:
            return ProjectSettings().model_dump()
        return data

    def update_project(self, settings: ProjectSettings) -> bool:
        return self.db.update_section("project", settings.model_dump())


    # ── Agents ──

    def get_all_agents(self) -> list[dict]:
        return self.db.get_all_agents()

    def get_agent(self, agent_id: str) -> Optional[dict]:
        return self.db.get_agent(agent_id)

    def create_agent(self, agent: AgentConfig) -> bool:
        return self.db.create_agent(agent)

    def update_agent(self, agent_id: str, agent: AgentConfig) -> bool:
        return self.db.update_agent(agent_id, agent)

    def delete_agent(self, agent_id: str) -> bool:
        return self.db.delete_agent(agent_id)

    def activate_agent(self, agent_id: str) -> bool:
        return self.db.set_active_agent(agent_id)

    def deactivate_agents(self) -> bool:
        return self.db.deactivate_all_agents()

    def get_active_agent(self) -> Optional[dict]:
        return self.db.get_active_agent()

    def get_system_prompt(self) -> str:
        """Build the full system prompt from personalization + active agent."""
        personalization = self.get_personalization()
        active_agent = self.get_active_agent()

        parts = []

        # Base style
        style = personalization.get("base_style_tone", "professional")
        parts.append(f"Respond in a {style} style.")

        # Characteristics
        chars = personalization.get("characteristics", ["default"])
        if "default" not in chars:
            char_str = ", ".join(chars)
            parts.append(f"Be {char_str} in your responses.")

        # Headers/lists
        hl_mode = personalization.get("headers_lists_mode", "default")
        if hl_mode == "always":
            parts.append("Use headers and bullet lists frequently for organization.")
        elif hl_mode == "never":
            parts.append("Avoid using headers and bullet lists. Use flowing prose.")
        elif hl_mode == "minimal":
            parts.append("Use headers and lists sparingly, only when necessary.")

        # Response length
        length = personalization.get("response_length", "default")
        if length == "short":
            parts.append("Keep responses concise and brief.")
        elif length == "long":
            parts.append("Provide thorough and comprehensive responses.")
        elif length == "detailed":
            parts.append("Provide extremely detailed and in-depth responses.")

        # User context
        name = personalization.get("preferred_name", "")
        if name:
            parts.append(f"Address the user as {name}.")

        profession = personalization.get("profession", "")
        if profession:
            parts.append(f"The user works as a {profession}.")

        user_context = personalization.get("user_context", "")
        if user_context:
            parts.append(f"About the user: {user_context}")

        # Custom instructions
        custom = personalization.get("custom_instructions", "")
        if custom:
            parts.append(f"Additional instructions: {custom}")

        # Active agent
        if active_agent and active_agent.get("enabled"):
            parts.append(f"\n--- Agent Role: {active_agent['name']} ---")
            parts.append(active_agent.get("system_instruction", ""))

        return "\n".join(parts)

    # ── Audit ──

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        return self.db.get_audit_log(limit)