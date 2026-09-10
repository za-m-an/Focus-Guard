"""Tests for service-level distraction blocking registry."""

import pytest
from focusguard.core.services import (
    SERVICE_REGISTRY,
    get_service,
    list_available_services,
    match_domain_to_service,
    resolve_services_to_domains,
)


def test_service_registry_contents():
    services = list_available_services()
    service_ids = [s["id"] for s in services]
    assert "instagram" in service_ids
    assert "facebook" in service_ids
    assert "youtube" in service_ids
    assert "tiktok" in service_ids
    assert "reddit" in service_ids
    assert "twitter" in service_ids
    assert "netflix" in service_ids
    assert "twitch" in service_ids
    assert "xbox" in service_ids
    assert "playstation" in service_ids
    assert "googleplay" in service_ids
    assert "steam" in service_ids
    assert "discord" in service_ids
    assert "roblox" in service_ids
    assert "epicgames" in service_ids
    assert "nintendo" in service_ids
    assert "spotify" in service_ids
    assert len(services) >= 17


def test_gaming_and_store_services():
    # Xbox
    xbox = get_service("xbox")
    assert xbox is not None
    assert "xbox.com" in xbox.all_domains
    assert "xboxlive.com" in xbox.all_domains
    assert "gamepass.com" in xbox.all_domains
    assert get_service("xboxlive") == xbox
    assert get_service("gamepass") == xbox

    # PlayStation
    ps = get_service("playstation")
    assert ps is not None
    assert "playstation.com" in ps.all_domains
    assert "playstation.net" in ps.all_domains
    assert "sonyentertainmentnetwork.com" in ps.all_domains
    assert get_service("psn") == ps
    assert get_service("ps5") == ps

    # Google Play
    gp = get_service("googleplay")
    assert gp is not None
    assert "play.google.com" in gp.all_domains
    assert "android.clients.google.com" in gp.all_domains
    assert get_service("gplay") == gp
    assert get_service("playstore") == gp

    # Steam, Discord, Roblox, Epic, Nintendo, Spotify
    assert get_service("steam") is not None
    assert get_service("valve") is not None
    assert get_service("discord") is not None
    assert get_service("roblox") is not None
    assert get_service("epicgames") is not None
    assert get_service("fortnite") is not None
    assert get_service("nintendo") is not None
    assert get_service("switch") is not None
    assert get_service("spotify") is not None




def test_get_service():
    insta = get_service("instagram")
    assert insta is not None
    assert insta.name == "Instagram"
    assert "instagram.com" in insta.all_domains
    assert "cdninstagram.com" in insta.all_domains

    # Case insensitive
    yt = get_service("YouTube")
    assert yt is not None
    assert "youtube.com" in yt.all_domains
    assert "googlevideo.com" in yt.all_domains

    unknown = get_service("nonexistent_service")
    assert unknown is None



def test_resolve_services_to_domains():
    domains = resolve_services_to_domains(["Instagram", "reddit"])
    assert "instagram.com" in domains
    assert "cdninstagram.com" in domains
    assert "reddit.com" in domains
    assert "redd.it" in domains

    # Unknown services are skipped gracefully
    domains_with_unknown = resolve_services_to_domains(["youtube", "fake_service_xyz"])
    assert "youtube.com" in domains_with_unknown
    assert len(domains_with_unknown) > 1


def test_match_domain_to_service():
    # Exact and subdomain matching
    matched, s_id = match_domain_to_service("instagram.com")
    assert matched is True
    assert s_id == "instagram"

    matched, s_id = match_domain_to_service("graph.instagram.com")
    assert matched is True
    assert s_id == "instagram"

    matched, s_id = match_domain_to_service("rr5---sn-4g5edn6s.googlevideo.com")
    assert matched is True
    assert s_id == "youtube"

    matched, s_id = match_domain_to_service("v16-webapp-prime.tiktok.com")
    assert matched is True
    assert s_id == "tiktok"

    # Non-service domain
    matched, s_id = match_domain_to_service("wikipedia.org")
    assert matched is False
    assert s_id is None
