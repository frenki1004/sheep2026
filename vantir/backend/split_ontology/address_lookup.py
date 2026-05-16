from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx


GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "Vantir Technologies Split MVP address lookup"


def lookup_reverse_address(*, lat: float, lon: float) -> dict[str, Any]:
    rounded_lat = round(float(lat), 5)
    rounded_lon = round(float(lon), 5)
    return _lookup_reverse_address_cached(rounded_lat, rounded_lon)


@lru_cache(maxsize=512)
def _lookup_reverse_address_cached(lat: float, lon: float) -> dict[str, Any]:
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if google_key:
        google_result = _lookup_google_reverse_address(lat=lat, lon=lon, key=google_key)
        if google_result["label"]:
            return google_result

    return _lookup_nominatim_reverse_address(lat=lat, lon=lon)


def _lookup_google_reverse_address(*, lat: float, lon: float, key: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=4) as client:
            response = client.get(
                GOOGLE_GEOCODE_URL,
                params={
                    "latlng": f"{lat},{lon}",
                    "language": "hr",
                    "region": "hr",
                    "result_type": "street_address|premise|route",
                    "key": key,
                },
            )
            response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return _empty_payload(lat=lat, lon=lon, source="Google Geocoding API")

    label = None
    if payload.get("status") == "OK":
        label = (payload.get("results") or [{}])[0].get("formatted_address")
    return {
        "type": "ReverseAddress",
        "status": "ok" if label else "unavailable",
        "label": label,
        "source": "Google Geocoding API",
        "lat": lat,
        "lon": lon,
    }


def _lookup_nominatim_reverse_address(*, lat: float, lon: float) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=4, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(
                NOMINATIM_REVERSE_URL,
                params={
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "accept-language": "hr,en",
                    "zoom": 18,
                    "lat": lat,
                    "lon": lon,
                },
            )
            response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return _empty_payload(lat=lat, lon=lon, source="OpenStreetMap Nominatim")

    label = _nominatim_label(payload)
    return {
        "type": "ReverseAddress",
        "status": "ok" if label else "unavailable",
        "label": label,
        "source": "OpenStreetMap Nominatim",
        "lat": lat,
        "lon": lon,
    }


def _nominatim_label(payload: dict[str, Any]) -> str | None:
    address = payload.get("address") or {}
    road = (
        address.get("road")
        or address.get("pedestrian")
        or address.get("footway")
        or address.get("path")
        or address.get("residential")
    )
    house_number = address.get("house_number")
    city = address.get("city") or address.get("town") or address.get("municipality")

    if road:
        street = f"{road} {house_number}".strip() if house_number else road
        return ", ".join(part for part in [street, city] if part)

    display_name = payload.get("display_name")
    if not display_name:
        return None
    parts = [part.strip() for part in display_name.split(",") if part.strip()]
    return ", ".join(parts[:3]) if parts else None


def _empty_payload(*, lat: float, lon: float, source: str) -> dict[str, Any]:
    return {
        "type": "ReverseAddress",
        "status": "unavailable",
        "label": None,
        "source": source,
        "lat": lat,
        "lon": lon,
    }
