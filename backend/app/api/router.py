"""Main API Router"""
from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.models import router as models_router
from app.api.system import router as system_router
from app.api.benchmark import router as benchmark_router
from app.api.rag import router as rag_router
from app.api.plugins import router as plugins_router
from app.api.workspace import router as workspace_router
from app.api.triage import router as triage_router
from app.settings.router import router as settings_router


api_router = APIRouter()

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(system_router, prefix="/system", tags=["system"])
api_router.include_router(benchmark_router, prefix="/benchmark", tags=["benchmark"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(plugins_router, prefix="/plugins", tags=["plugins"])
api_router.include_router(workspace_router, prefix="/workspace", tags=["workspace"])
api_router.include_router(triage_router, prefix="/triage", tags=["triage"])
api_router.include_router(settings_router)