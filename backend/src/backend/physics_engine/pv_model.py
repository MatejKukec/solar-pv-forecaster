"""PV power model: clear-sky → POA transposition → DC/AC conversion.

Pure computation over already-fetched weather data. No network I/O here —
callers pass in raw provider JSON or a parsed DataFrame.
"""

from typing import Any, cast

import pandas as pd
import pvlib

from backend.models import Location, PVArray

# PVWatts temperature coefficient for crystalline silicon, %/°C — a reasonable
# default until real panel presets (Section 6.2, nice-to-have) are wired in.
_GAMMA_PDC = -0.004


def parse_open_meteo_hourly(raw: dict[str, Any]) -> pd.DataFrame:
    """Convert a raw Open-Meteo `hourly` payload into an indexed weather DataFrame.

    Args:
        raw: Raw JSON from OpenMeteoClient.get_forecast/get_historical.

    Returns:
        DataFrame indexed by UTC timestamp with columns: ghi, dni, dhi,
        temp_air, wind_speed, cloud_cover.

    Raises:
        ValueError: If the payload is missing the expected `hourly.time` field.
    """
    hourly = raw.get("hourly")
    if not hourly or "time" not in hourly:
        raise ValueError("weather payload missing 'hourly.time'")

    df = pd.DataFrame(
        {
            "ghi": hourly.get("shortwave_radiation", []),
            "dni": hourly.get("direct_normal_irradiance", []),
            "dhi": hourly.get("diffuse_radiation", []),
            "temp_air": hourly.get("temperature_2m", []),
            "wind_speed": hourly.get("wind_speed_10m", []),
            "cloud_cover": hourly.get("cloud_cover", []),
        },
        index=pd.to_datetime(hourly["time"], utc=True),
    )
    df.index.name = "timestamp"
    return df


def get_clearsky(times: pd.DatetimeIndex, location: Location) -> pd.DataFrame:
    """Compute clear-sky GHI/DNI/DHI for a location using the Ineichen model.

    Used as a reference baseline for anomaly detection and calibration.

    Args:
        times: Timestamps to evaluate, timezone-aware.
        location: Site coordinates.

    Returns:
        DataFrame with columns ghi, dni, dhi.
    """
    site = pvlib.location.Location(location.latitude, location.longitude, altitude=location.elevation_m)
    return cast(pd.DataFrame, site.get_clearsky(times, model="ineichen"))


def compute_poa_irradiance(weather: pd.DataFrame, location: Location, array: PVArray) -> pd.Series:
    """Transpose GHI/DNI/DHI onto the plane of array (POA) for a given tilt/azimuth.

    Args:
        weather: DataFrame with ghi, dni, dhi columns (from parse_open_meteo_hourly).
        location: Site coordinates, used for solar position.
        array: Array tilt/azimuth configuration.

    Returns:
        Series of plane-of-array global irradiance (W/m²), same index as weather.
    """
    solar_position = pvlib.solarposition.get_solarposition(
        weather.index, location.latitude, location.longitude, altitude=location.elevation_m
    )
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=array.tilt_deg,
        surface_azimuth=array.azimuth_deg,
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni=weather["dni"].clip(lower=0),
        ghi=weather["ghi"].clip(lower=0),
        dhi=weather["dhi"].clip(lower=0),
    )
    return cast(pd.Series, poa["poa_global"])


def compute_cell_temperature(weather: pd.DataFrame, location: Location, array: PVArray) -> pd.Series:
    """Compute modeled cell temperature (Faiman model) for a weather window.

    Split out from `forecast_ac_power` so the loss-diagnostics analytics
    (Day 2) can get cell temperature without duplicating the POA step.

    Args:
        weather: DataFrame with ghi, dni, dhi, temp_air, wind_speed columns.
        location: Site coordinates, used for solar position.
        array: Array tilt/azimuth configuration.

    Returns:
        Series of cell temperature (°C), same index as weather.
    """
    poa_global = compute_poa_irradiance(weather, location, array)
    return cast(pd.Series, pvlib.temperature.faiman(poa_global, weather["temp_air"], weather["wind_speed"]))


def forecast_ac_power(weather_raw: dict[str, Any], location: Location, array: PVArray) -> pd.DataFrame:
    """Run the full pipeline: parse weather → POA → cell temp → DC/AC power.

    Args:
        weather_raw: Raw Open-Meteo JSON payload.
        location: Site coordinates.
        array: Array configuration (capacity, tilt, azimuth, losses).

    Returns:
        DataFrame indexed by UTC timestamp with columns: ac_power_kw, ghi, cloud_cover.

    Raises:
        ValueError: If the weather payload has no hourly data.
    """
    weather = parse_open_meteo_hourly(weather_raw)
    if weather.empty:
        raise ValueError("no hourly weather data to forecast from")

    poa_global = compute_poa_irradiance(weather, location, array)
    cell_temp = pvlib.temperature.faiman(poa_global, weather["temp_air"], weather["wind_speed"])

    pdc0_w = array.capacity_kw * 1000
    dc_power_w = pvlib.pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0_w, _GAMMA_PDC)
    ac_power_w = pvlib.inverter.pvwatts(dc_power_w, pdc0_w)

    loss_factor = 1 - (array.system_loss_pct / 100)
    ac_power_kw = (ac_power_w * loss_factor / 1000).clip(lower=0)

    result = pd.DataFrame({"ac_power_kw": ac_power_kw, "ghi": weather["ghi"], "cloud_cover": weather["cloud_cover"]})
    result.index.name = "timestamp"
    return result
