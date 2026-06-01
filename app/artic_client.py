import aiohttp
from typing import Optional, Dict, Any

ARTIC_BASE_URL = "https://api.artic.edu/api/v1"
ARTIC_IMAGE_BASE = "https://www.artic.edu/iiif/2"


async def fetch_artwork(artwork_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a single artwork by ID from the Art Institute of Chicago API.
    Returns None if not found, raises on network/server errors.
    """
    url = f"{ARTIC_BASE_URL}/artworks/{artwork_id}"
    params = {"fields": "id,title,artist_display,image_id"}

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()
            return data.get("data")


def build_image_url(image_id: Optional[str]) -> Optional[str]:
    if not image_id:
        return None
    return f"{ARTIC_IMAGE_BASE}/{image_id}/full/843,/0/default.jpg"


async def validate_and_fetch_artwork(artwork_id: int) -> Optional[Dict[str, Any]]:
    """
    Validate artwork exists and return normalised place data.
    Returns None if the artwork doesn't exist in the API.
    """
    artwork = await fetch_artwork(artwork_id)
    if not artwork:
        return None

    return {
        "external_id": artwork["id"],
        "title": artwork.get("title") or "Unknown Title",
        "artist": artwork.get("artist_display"),
        "image_url": build_image_url(artwork.get("image_id")),
    }
