"""
youtube_service.py
-------------------
Funciones para conectarse a la YouTube Data API v3 y extraer:
- Datos generales del canal (suscriptores, videos totales, descripción)
- Enlaces de venta / monetización detectados en la biografía
- Canales o podcasts vinculados (secciones destacadas del canal)
- Últimos videos largos (> 60s) y Shorts (<= 60s), con vistas exactas y fecha
"""

import re
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ---------------------------------------------------------------------------
# Patrones para detectar enlaces de venta / monetización en la biografía
# ---------------------------------------------------------------------------
BIO_LINK_PATTERNS = {
    "Linktree": r"linktr\.ee",
    "Beacons": r"beacons\.ai",
    "Hotmart": r"hotmart\.com",
    "Kajabi": r"kajabi\.com",
    "Gumroad": r"gumroad\.com",
    "Teachable": r"teachable\.com",
    "Thinkific": r"thinkific\.com",
    "Udemy": r"udemy\.com",
    "Shopify / Tienda propia": r"myshopify\.com|shopify\.com",
    "WhatsApp Business": r"wa\.me|whatsapp\.com",
    "Patreon": r"patreon\.com",
    "Stan Store": r"stan\.store",
    "Tienda / Curso genérico": r"/(shop|store|tienda|curso|course)\b",
}


def parse_duration_seconds(duration_iso: str) -> int:
    """Convierte una duración ISO 8601 (ej. 'PT4M13S') a segundos totales."""
    if not duration_iso:
        return 0
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = pattern.match(duration_iso)
    if not match:
        return 0
    h, m, s = match.groups()
    h = int(h) if h else 0
    m = int(m) if m else 0
    s = int(s) if s else 0
    return h * 3600 + m * 60 + s


def get_youtube_client(api_key: str):
    """Crea el cliente de la YouTube Data API v3."""
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def detect_bio_links(description: str) -> dict:
    """Analiza la descripción del canal en busca de enlaces de venta/monetización."""
    description = description or ""
    encontrados = [
        nombre for nombre, patron in BIO_LINK_PATTERNS.items()
        if re.search(patron, description, re.IGNORECASE)
    ]
    urls = re.findall(r"(https?://[^\s]+)", description)
    return {
        "tipos_detectados": encontrados,
        "urls_en_descripcion": urls,
        "tiene_venta": len(encontrados) > 0,
    }


def resolve_channel_id(youtube, channel_input: str):
    """
    Resuelve el channelId a partir de:
    - Un channelId directo (UCxxxxxxxx...)
    - Una URL de canal (/channel/, /c/, /user/, /@handle)
    - Un @handle o nombre de usuario suelto
    """
    channel_input = (channel_input or "").strip()
    if not channel_input:
        return None

    if channel_input.startswith("UC") and len(channel_input) == 24:
        return channel_input

    m = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", channel_input)
    if m:
        return m.group(1)

    m = re.search(r"youtube\.com/@([A-Za-z0-9_.\-]+)", channel_input)
    handle = m.group(1) if m else None

    if not handle:
        m = re.search(r"youtube\.com/(?:c/|user/)([A-Za-z0-9_.\-]+)", channel_input)
        legacy_name = m.group(1) if m else None
    else:
        legacy_name = None

    if not handle and not legacy_name:
        handle = channel_input.lstrip("@")

    # 1) Intentar resolver por handle moderno (@usuario)
    if handle:
        try:
            resp = youtube.channels().list(part="id", forHandle=handle).execute()
            items = resp.get("items", [])
            if items:
                return items[0]["id"]
        except HttpError:
            pass

    # 2) Intentar resolver por nombre de usuario legado
    lookup_name = legacy_name or handle
    if lookup_name:
        try:
            resp = youtube.channels().list(part="id", forUsername=lookup_name).execute()
            items = resp.get("items", [])
            if items:
                return items[0]["id"]
        except HttpError:
            pass

    # 3) Último recurso: búsqueda (consume más cuota, ~100 unidades)
    try:
        resp = youtube.search().list(
            part="snippet", q=lookup_name or channel_input, type="channel", maxResults=1
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    except HttpError:
        pass

    return None


def get_channel_overview(youtube, channel_id: str) -> dict:
    """Obtiene estadísticas generales, descripción y enlaces detectados en la bio."""
    resp = youtube.channels().list(
        part="snippet,statistics,contentDetails", id=channel_id
    ).execute()
    items = resp.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item["snippet"]
    stats = item["statistics"]
    description = snippet.get("description", "")

    return {
        "channel_id": channel_id,
        "title": snippet.get("title"),
        "description": description,
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        "subscribers": None if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "bio_links": detect_bio_links(description),
    }


def get_linked_channels(youtube, channel_id: str) -> list:
    """
    Busca canales / podcasts vinculados a través de las secciones destacadas
    del canal (channelSections del tipo 'multipleChannels').
    """
    linked = []
    try:
        resp = youtube.channelSections().list(
            part="snippet,contentDetails", channelId=channel_id
        ).execute()
        ids_a_resolver = []
        for section in resp.get("items", []):
            ids_a_resolver.extend(section.get("contentDetails", {}).get("channels", []))

        ids_a_resolver = list(dict.fromkeys(ids_a_resolver))  # únicos, conserva orden
        for i in range(0, len(ids_a_resolver), 50):
            lote = ids_a_resolver[i:i + 50]
            sub_resp = youtube.channels().list(part="snippet", id=",".join(lote)).execute()
            for c in sub_resp.get("items", []):
                linked.append({
                    "title": c["snippet"]["title"],
                    "channel_id": c["id"],
                    "url": f"https://www.youtube.com/channel/{c['id']}",
                })
    except HttpError:
        pass
    return linked


def get_recent_video_ids(youtube, uploads_playlist_id: str, max_results: int = 150) -> list:
    """Recorre la playlist de uploads del canal y devuelve los IDs de video más recientes."""
    video_ids = []
    next_page = None
    while len(video_ids) < max_results:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=min(50, max_results - len(video_ids)),
            pageToken=next_page,
        ).execute()
        for item in resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return video_ids


def get_videos_details(youtube, video_ids: list) -> list:
    """Obtiene título, fecha, vistas exactas, duración y clasifica Short vs. Largo."""
    videos = []
    for i in range(0, len(video_ids), 50):
        lote = video_ids[i:i + 50]
        resp = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(lote)
        ).execute()
        for item in resp.get("items", []):
            duracion_s = parse_duration_seconds(item["contentDetails"]["duration"])
            stats = item.get("statistics", {})
            fecha_raw = item["snippet"]["publishedAt"]
            fecha = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
            videos.append({
                "video_id": item["id"],
                "titulo": item["snippet"]["title"],
                "fecha": fecha,
                "vistas": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                "comentarios": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
                "duracion_segundos": duracion_s,
                "es_short": duracion_s <= 60,
                "url": f"https://www.youtube.com/watch?v={item['id']}",
            })
    return videos


def classify_videos(videos: list, n_longs: int = 10, n_shorts: int = 20):
    """Ordena por fecha descendente y separa los últimos N largos y N Shorts."""
    videos_ordenados = sorted(videos, key=lambda v: v["fecha"], reverse=True)
    shorts = [v for v in videos_ordenados if v["es_short"]][:n_shorts]
    largos = [v for v in videos_ordenados if not v["es_short"]][:n_longs]
    return largos, shorts


def analyze_channel(api_key: str, channel_input: str) -> dict:
    """Función de conveniencia: ejecuta todo el flujo de análisis de un canal de YouTube."""
    youtube = get_youtube_client(api_key)
    channel_id = resolve_channel_id(youtube, channel_input)
    if not channel_id:
        return None

    overview = get_channel_overview(youtube, channel_id)
    if not overview:
        return None

    linked_channels = get_linked_channels(youtube, channel_id)
    video_ids = get_recent_video_ids(youtube, overview["uploads_playlist_id"], max_results=150)
    videos = get_videos_details(youtube, video_ids)
    largos, shorts = classify_videos(videos, n_longs=10, n_shorts=20)

    return {
        "overview": overview,
        "linked_channels": linked_channels,
        "longs": largos,
        "shorts": shorts,
    }
