"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from backend.ai_layer import AIProvider, GeminiProvider, MockProvider
from backend.config import settings
from backend.data_ingestion import OpenMeteoClient, PVGISClient
from backend.db import get_session


def get_open_meteo_client() -> OpenMeteoClient:
    """Provide an Open-Meteo client instance."""
    return OpenMeteoClient()


def get_pvgis_client() -> PVGISClient:
    """Provide a PVGIS client instance."""
    return PVGISClient()


def get_ai_provider() -> AIProvider:
    """Provide the active AIProvider implementation.

    Returns GeminiProvider when GEMINI_API_KEY is set, else MockProvider —
    swapping this one function is the only change needed elsewhere in the app.
    """
    if settings.gemini_api_key:
        return GeminiProvider()
    return MockProvider()


OpenMeteoDep = Annotated[OpenMeteoClient, Depends(get_open_meteo_client)]
PVGISDep = Annotated[PVGISClient, Depends(get_pvgis_client)]
AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]
SessionDep = Annotated[Session, Depends(get_session)]
