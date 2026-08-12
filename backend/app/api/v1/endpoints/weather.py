"""Weather + disease-risk endpoints (M5, Task 1).

``GET /weather/current`` returns normalized current weather for a location;
``GET /weather/risk`` scores every catalog disease of a crop against the
current weather. Both are authenticated (any role, consistent with the
read-only catalog/soil endpoints) and provider-independent: the response never
exposes an upstream source beyond the normalized ``provider``/``is_fallback``
flags.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.weather import WeatherOut, WeatherRiskOut
from app.services.weather import WeatherService, weather_to_out
from app.services.weather_risk import DiseaseRiskService

router = APIRouter(prefix="/weather", tags=["weather"])

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# FastAPI-native range validation (422 for out-of-range coordinates) — the
# service re-validates as defense-in-depth for non-HTTP callers (400).
Latitude = Annotated[float, Query(ge=-90.0, le=90.0, description="Latitude (WGS84)")]
Longitude = Annotated[float, Query(ge=-180.0, le=180.0, description="Longitude (WGS84)")]


@router.get("/current", response_model=WeatherOut)
async def get_current_weather(
    lat: Latitude,
    lng: Longitude,
    _current_user: CurrentUser,
) -> WeatherOut:
    """Normalized current weather for a location.

    Degrades to the deterministic mock source when the configured live provider
    is unavailable (marked by ``is_fallback``). 502 when the live source fails
    and fallback is disabled.
    """
    result = await WeatherService().get_current(lat, lng)
    return weather_to_out(result.data, is_fallback=result.is_fallback)


@router.get("/risk", response_model=WeatherRiskOut)
async def get_disease_risk(
    crop_id: int,
    lat: Latitude,
    lng: Longitude,
    _current_user: CurrentUser,
    db: Db,
) -> WeatherRiskOut:
    """Per-crop disease risk under the current weather.

    Scores every catalog disease of ``crop_id`` from documented weather-rule
    constants keyed by the disease's pathogen class (see
    :mod:`app.services.weather_risk`). 404 when the crop is not in the catalog
    (unsupported crop).
    """
    result = await WeatherService().get_current(lat, lng)
    return await DiseaseRiskService(db).assess_crop(
        crop_id, result.data, is_fallback=result.is_fallback
    )
