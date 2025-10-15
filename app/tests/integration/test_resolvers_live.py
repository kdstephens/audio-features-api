import os
import pytest
import asyncio

from app.core import resolvers

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_deezer_preview_live():
    res = await resolvers.resolve_deezer_preview("Aretha Franklin", "Respect")
    assert res is not None, "Deezer didn't return a preview for this query"
    assert res["preview_url"].startswith("http")
    # actually download the 30s preview
    b = await resolvers.fetch_bytes(res["preview_url"])
    assert len(b) > 1000  # got some bytes
    assert res["source"] == "deezer"

@pytest.mark.asyncio
async def test_apple_preview_live():
    res = await resolvers.resolve_apple_preview("Aretha Franklin", "Respect")
    assert res is not None, "Apple didn't return a preview for this query"
    assert res["preview_url"].startswith("http")
    b = await resolvers.fetch_bytes(res["preview_url"])
    assert len(b) > 1000
    assert res["source"] == "apple"

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("SPOTIFY_BEARER"), reason="Set SPOTIFY_BEARER to run this test")
async def test_spotify_metadata_live():
    # Example Spotify track ID for testing metadata only
    spid = "2takcwOaAZWiXQijPHIx7B"  # Spotify example track (from docs)
    token = os.getenv("SPOTIFY_BEARER")
    data = await resolvers.resolve_spotify_metadata(spid, token)
    assert data.get("title"), "Spotify metadata should include a title"
    # preview_url is often null; we *do not* download Spotify audio
