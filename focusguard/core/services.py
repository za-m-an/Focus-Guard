"""Service-Level Blocking Definitions and Companion Registry.

Supports blocking whole distraction platforms across desktop browsers,
mobile applications (iOS & Android companion APIs and CDNs), and background processes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceDefinition:
    """Represents a full distraction service with its mobile APIs, CDNs, and domains."""
    id: str
    name: str
    category: str
    description: str
    primary_domains: list[str]
    companion_domains: list[str]
    mobile_api_endpoints: list[str] = field(default_factory=list)
    cdn_domains: list[str] = field(default_factory=list)
    doh_endpoints: list[str] = field(default_factory=list)

    @property
    def all_domains(self) -> set[str]:
        """Return all domains associated with this service."""
        return set(
            self.primary_domains
            + self.companion_domains
            + self.mobile_api_endpoints
            + self.cdn_domains
            + self.doh_endpoints
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "primary_domains": self.primary_domains,
            "domain_count": len(self.all_domains),
        }


# Curated, battle-tested service definitions covering web, Android, iOS apps, and CDNs
SERVICE_REGISTRY: dict[str, ServiceDefinition] = {
    "youtube": ServiceDefinition(
        id="youtube",
        name="YouTube",
        category="Video / Streaming",
        description="YouTube website, mobile apps, video delivery CDNs, and API services",
        primary_domains=["youtube.com", "youtu.be"],
        companion_domains=[
            "youtube-nocookie.com",
            "youtubei.googleapis.com",
            "yt.be",
            "ytimg.com",
        ],
        mobile_api_endpoints=[
            "yt3.ggpht.com",
            "yt4.ggpht.com",
            "youtubei.googleapis.com",
            "wide-youtube.l.google.com",
        ],
        cdn_domains=[
            "googlevideo.com",
            "redirector.googlevideo.com",
        ],
    ),
    "instagram": ServiceDefinition(
        id="instagram",
        name="Instagram",
        category="Social Media",
        description="Instagram web, iOS/Android mobile apps, Stories, Reels, and CDN media",
        primary_domains=["instagram.com", "ig.me"],
        companion_domains=[
            "cdninstagram.com",
            "instagr.am",
            "igsonar.com",
        ],
        mobile_api_endpoints=[
            "i.instagram.com",
            "graph.instagram.com",
            "b.i.instagram.com",
            "edge-chat.instagram.com",
        ],
        cdn_domains=[
            "scontent.cdninstagram.com",
            "static.cdninstagram.com",
            "z-p3-scontent.cdninstagram.com",
        ],
    ),
    "facebook": ServiceDefinition(
        id="facebook",
        name="Facebook & Messenger",
        category="Social Media",
        description="Facebook web, Messenger app, Graph API, and media delivery CDNs",
        primary_domains=["facebook.com", "fb.com", "messenger.com"],
        companion_domains=[
            "fb.me",
            "fbsbx.com",
            "facebook.net",
            "connect.facebook.net",
            "fbcdn.net",
        ],
        mobile_api_endpoints=[
            "graph.facebook.com",
            "api.facebook.com",
            "edge-chat.facebook.com",
            "b-graph.facebook.com",
            "gateway.facebook.com",
        ],
        cdn_domains=[
            "scontent.xx.fbcdn.net",
            "static.xx.fbcdn.net",
            "external.xx.fbcdn.net",
        ],
    ),
    "tiktok": ServiceDefinition(
        id="tiktok",
        name="TikTok",
        category="Short Video",
        description="TikTok website, mobile apps (iOS/Android), and ByteDance media APIs",
        primary_domains=["tiktok.com", "tiktokv.com"],
        companion_domains=[
            "musical.ly",
            "byteoversea.com",
            "ibytedtos.com",
            "tiktokcdn.com",
            "ibyteimg.com",
        ],
        mobile_api_endpoints=[
            "api.tiktokv.com",
            "api-h2.tiktokv.com",
            "api16-normal-c-useast1a.tiktokv.com",
            "log.byteoversea.com",
            "mon.byteoversea.com",
        ],
        cdn_domains=[
            "v16-webapp.tiktok.com",
            "p16-va.tiktokcdn.com",
            "p16-sign-va.tiktokcdn.com",
        ],
    ),
    "reddit": ServiceDefinition(
        id="reddit",
        name="Reddit",
        category="Community / Forum",
        description="Reddit website, native mobile clients, media storage, and OAuth APIs",
        primary_domains=["reddit.com", "redd.it"],
        companion_domains=[
            "redditmedia.com",
            "redditstatic.com",
            "redditmedia.com",
            "reddithelp.com",
        ],
        mobile_api_endpoints=[
            "oauth.reddit.com",
            "gateway.reddit.com",
            "gql.reddit.com",
            "v.redd.it",
            "i.redd.it",
        ],
        cdn_domains=[
            "preview.redd.it",
            "external-preview.redd.it",
        ],
    ),
    "twitter": ServiceDefinition(
        id="twitter",
        name="Twitter / X",
        category="Social Media",
        description="X / Twitter web, iOS/Android mobile clients, short links, and media CDNs",
        primary_domains=["twitter.com", "x.com"],
        companion_domains=[
            "t.co",
            "twimg.com",
            "x.team",
        ],
        mobile_api_endpoints=[
            "api.twitter.com",
            "api.x.com",
            "upload.twitter.com",
        ],
        cdn_domains=[
            "pbs.twimg.com",
            "video.twimg.com",
            "ton.twimg.com",
        ],
    ),
    "netflix": ServiceDefinition(
        id="netflix",
        name="Netflix",
        category="Entertainment",
        description="Netflix streaming service, TV and mobile apps, and CDN video nodes",
        primary_domains=["netflix.com", "netflix.net"],
        companion_domains=[
            "nflxext.com",
            "nflximg.net",
            "nflxvideo.net",
            "nflxso.net",
        ],
        mobile_api_endpoints=[
            "api-global.netflix.com",
            "ichnaea.netflix.com",
        ],
        cdn_domains=[
            "occ-0-*.1.nflxso.net",
        ],
    ),
    "twitch": ServiceDefinition(
        id="twitch",
        name="Twitch",
        category="Live Streaming",
        description="Twitch livestreaming website, mobile apps, chat gateways, and video CDNs",
        primary_domains=["twitch.tv"],
        companion_domains=[
            "ttvnw.net",
            "jtvnw.net",
            "twitchcdn.net",
        ],
        mobile_api_endpoints=[
            "api.twitch.tv",
            "gql.twitch.tv",
            "irc.chat.twitch.tv",
        ],
        cdn_domains=[
            "static-cdn.jtvnw.net",
            "video-edge-*.hls.ttvnw.net",
        ],
    ),
}


def get_service(service_id: str) -> ServiceDefinition | None:
    """Retrieve service definition by canonical ID or alias."""
    sid = service_id.strip().lower()
    if sid in ("x", "x.com"):
        sid = "twitter"
    return SERVICE_REGISTRY.get(sid)


def list_available_services() -> list[dict[str, Any]]:
    """Return summary list of all available distraction services."""
    return [svc.to_dict() for svc in SERVICE_REGISTRY.values()]


def match_service_by_domain(domain: str) -> str | None:
    """
    Identify if a domain belongs to a registered distraction service.
    Returns service name (e.g. 'Instagram') or None.
    """
    d = domain.strip().lower()
    for svc in SERVICE_REGISTRY.values():
        for candidate in svc.all_domains:
            if candidate.startswith("*."):
                suffix = candidate[2:]
                if d == suffix or d.endswith("." + suffix):
                    return svc.name
            else:
                if d == candidate or d.endswith("." + candidate):
                    return svc.name
    return None


def get_all_domains_for_services(service_ids: list[str] | set[str]) -> set[str]:
    """Resolve a collection of service IDs into complete domain sets."""
    domains: set[str] = set()
    for sid in service_ids:
        svc = get_service(sid)
        if svc:
            domains.update(svc.all_domains)
    return domains


def resolve_services_to_domains(service_ids: list[str] | set[str]) -> set[str]:
    """Alias for get_all_domains_for_services."""
    return get_all_domains_for_services(service_ids)


def match_domain_to_service(domain: str) -> tuple[bool, str | None]:
    """
    Check if domain matches any registered service.
    Returns (True, service_id) or (False, None).
    """
    d = domain.strip().lower()
    for sid, svc in SERVICE_REGISTRY.items():
        for candidate in svc.all_domains:
            if candidate.startswith("*."):
                suffix = candidate[2:]
                if d == suffix or d.endswith("." + suffix):
                    return True, sid
            else:
                if d == candidate or d.endswith("." + candidate):
                    return True, sid
    return False, None

