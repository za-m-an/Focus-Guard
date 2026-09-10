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
    "xbox": ServiceDefinition(
        id="xbox",
        name="Xbox & Game Pass",
        category="Gaming / Console",
        description="Xbox Live network, console telemetry, Game Pass cloud, and store services",
        primary_domains=["xbox.com", "xboxlive.com"],
        companion_domains=[
            "xboxservices.com",
            "xboxab.com",
            "gamepass.com",
            "xboxgamestudio.com",
        ],
        mobile_api_endpoints=[
            "xsts.auth.xboxlive.com",
            "title.mgt.xboxlive.com",
            "user.auth.xboxlive.com",
            "device.auth.xboxlive.com",
            "licensing.xboxlive.com",
        ],
        cdn_domains=[
            "assets1.xboxlive.com",
            "images-eds.xboxlive.com",
            "dlassets.xboxlive.com",
        ],
    ),
    "playstation": ServiceDefinition(
        id="playstation",
        name="PlayStation & PSN",
        category="Gaming / Console",
        description="PlayStation Network (PSN), console gaming, PlayStation Store, and Sony auth APIs",
        primary_domains=["playstation.com", "playstation.net"],
        companion_domains=[
            "sonyentertainmentnetwork.com",
            "playstationnetwork.com",
            "psn.net",
            "sie.com",
            "playstation.org",
        ],
        mobile_api_endpoints=[
            "auth.api.sonyentertainmentnetwork.com",
            "ca.account.sony.com",
            "commerce.api.playstation.com",
            "status.playstation.com",
        ],
        cdn_domains=[
            "apollo2.dl.playstation.net",
            "gs2.ww.prod.dl.playstation.net",
            "static-resource.np.community.playstation.net",
        ],
    ),
    "googleplay": ServiceDefinition(
        id="googleplay",
        name="Google Play Store & Services",
        category="App Store / Services",
        description="Google Play Store, app download CDN endpoints, and Play Games services",
        primary_domains=["play.google.com", "market.android.com"],
        companion_domains=[
            "android.clients.google.com",
            "playgames.google.com",
            "play-lh.googleusercontent.com",
        ],
        mobile_api_endpoints=[
            "android.googleapis.com",
            "play.googleapis.com",
        ],
        cdn_domains=[
            "lh3.googleusercontent.com",
        ],
    ),
    "steam": ServiceDefinition(
        id="steam",
        name="Steam",
        category="Gaming / Store",
        description="Steam store, community discussions, game downloads, and friend chat",
        primary_domains=["steampowered.com", "steamcommunity.com"],
        companion_domains=[
            "steamgames.com",
            "steamstatic.com",
            "steamcontent.com",
            "steam-chat.com",
            "valvesoftware.com",
        ],
        mobile_api_endpoints=[
            "api.steampowered.com",
            "cm.steampowered.com",
        ],
        cdn_domains=[
            "steamcdn-a.akamaihd.net",
            "cdn.steamcommunity.com",
        ],
    ),
    "discord": ServiceDefinition(
        id="discord",
        name="Discord",
        category="Chat / Community",
        description="Discord voice, video, text chat apps, media attachments, and gateway APIs",
        primary_domains=["discord.com", "discord.gg"],
        companion_domains=[
            "discordapp.com",
            "discordapp.net",
            "discord.media",
            "discordstatus.com",
        ],
        mobile_api_endpoints=[
            "gateway.discord.gg",
            "status.discord.com",
        ],
        cdn_domains=[
            "cdn.discordapp.com",
            "media.discordapp.net",
        ],
    ),
    "roblox": ServiceDefinition(
        id="roblox",
        name="Roblox",
        category="Gaming / Metaverse",
        description="Roblox game client, web platform, asset delivery CDN, and user authentication",
        primary_domains=["roblox.com", "rbxcdn.com"],
        companion_domains=[
            "robloxlabs.com",
            "rbx.com",
        ],
        mobile_api_endpoints=[
            "api.roblox.com",
            "auth.roblox.com",
        ],
        cdn_domains=[
            "static.rbxcdn.com",
            "setup.rbxcdn.com",
        ],
    ),
    "epicgames": ServiceDefinition(
        id="epicgames",
        name="Epic Games & Fortnite",
        category="Gaming / Store",
        description="Epic Games launcher, store, Fortnite online services, and Unreal Engine APIs",
        primary_domains=["epicgames.com", "fortnite.com"],
        companion_domains=[
            "epicgames.net",
            "unrealengine.com",
        ],
        mobile_api_endpoints=[
            "account-public-service-prod.ol.epicgames.com",
        ],
        cdn_domains=[
            "fastly-epicgames.ol.epicgames.com",
        ],
    ),
    "nintendo": ServiceDefinition(
        id="nintendo",
        name="Nintendo & Switch Online",
        category="Gaming / Console",
        description="Nintendo eShop, Switch online services, account portal, and game updates",
        primary_domains=["nintendo.com", "nintendo.net"],
        companion_domains=[
            "nintendonetwork.net",
            "nintendo-europe.com",
        ],
        mobile_api_endpoints=[
            "api.accounts.nintendo.com",
        ],
        cdn_domains=[
            "atum.hac.lp1.d4c.nintendo.net",
        ],
    ),
    "spotify": ServiceDefinition(
        id="spotify",
        name="Spotify",
        category="Music / Streaming",
        description="Spotify desktop, web player, mobile applications, and music delivery CDNs",
        primary_domains=["spotify.com", "spotifycdn.com"],
        companion_domains=[
            "spoti.fi",
            "scdn.co",
        ],
        mobile_api_endpoints=[
            "api.spotify.com",
            "ap.spotify.com",
        ],
        cdn_domains=[
            "audio-fa.scdn.co",
            "audio4-fa.scdn.co",
        ],
    ),
}


def get_service(service_id: str) -> ServiceDefinition | None:
    """Retrieve service definition by canonical ID or alias."""
    sid = service_id.strip().lower()
    alias_map = {
        "x": "twitter",
        "x.com": "twitter",
        "psn": "playstation",
        "playstation5": "playstation",
        "playstation4": "playstation",
        "ps4": "playstation",
        "ps5": "playstation",
        "xboxlive": "xbox",
        "gamepass": "xbox",
        "gplay": "googleplay",
        "playstore": "googleplay",
        "google-play": "googleplay",
        "valve": "steam",
        "fortnite": "epicgames",
        "epic": "epicgames",
        "switch": "nintendo",
    }
    canonical_id = alias_map.get(sid, sid)
    return SERVICE_REGISTRY.get(canonical_id)



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

