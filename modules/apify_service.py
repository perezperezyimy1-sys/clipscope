"""
apify_service.py
-----------------
Funciones para conectarse a Apify (apify-client) y extraer, de los últimos
videos de TikTok / Instagram Reels / Facebook Video: promedio de vistas,
fecha del último contenido y seguidores.

IMPORTANTE — Actores de Apify:
Los IDs de actor definidos abajo (TIKTOK_ACTOR, INSTAGRAM_*_ACTOR,
FACEBOOK_*_ACTOR) apuntan a actores públicos populares del Apify Store al
momento de escribir este código. Apify permite que cualquier desarrollador
publique actores y estos cambian, se renombran o pasan a ser de pago con el
tiempo. Antes de usar en producción:
  1. Verifica en https://apify.com/store que el actor siga activo.
  2. Revisa su "Input schema" y ajusta `run_input` si cambió.
  3. Revisa un ítem de ejemplo de su dataset y ajusta las listas de
     `*_keys` en cada función `analyze_*` si los nombres de campo cambiaron.

Estos IDs son fácilmente reemplazables porque están centralizados en las
constantes de arriba de este archivo.
"""

from datetime import datetime, timezone

from apify_client import ApifyClient

# ---------------------------------------------------------------------------
# IDs de actores (ajustables sin tocar la lógica de negocio)
# ---------------------------------------------------------------------------
TIKTOK_ACTOR = "clockworks/tiktok-scraper"
INSTAGRAM_PROFILE_ACTOR = "apify/instagram-profile-scraper"
INSTAGRAM_REELS_ACTOR = "apify/instagram-reel-scraper"
FACEBOOK_PAGE_ACTOR = "apify/facebook-pages-scraper"
FACEBOOK_VIDEOS_ACTOR = "apify/facebook-video-scraper"


def get_apify_client(token: str) -> ApifyClient:
    return ApifyClient(token)


# ---------------------------------------------------------------------------
# Utilidades genéricas para leer estructuras de datos heterogéneas
# ---------------------------------------------------------------------------
def _dig(d, dotted_key: str):
    """Navega un diccionario anidado usando una ruta tipo 'a.b.c'."""
    cur = d
    for parte in dotted_key.split("."):
        if isinstance(cur, dict) and parte in cur:
            cur = cur[parte]
        else:
            return None
    return cur


def _first_value(item: dict, candidates: list):
    """Devuelve el primer valor no nulo encontrado probando varias rutas posibles."""
    for c in candidates:
        v = _dig(item, c)
        if v is not None:
            return v
    return None


def _parse_date(value):
    """Intenta interpretar fechas en formato timestamp (int) o ISO 8601 (str)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def run_actor_sync(client: ApifyClient, actor_id: str, run_input: dict, timeout_secs: int = 150) -> list:
    """Ejecuta un actor de Apify de forma síncrona y devuelve los ítems del dataset resultante."""
    run = client.actor(actor_id).call(run_input=run_input, timeout_secs=timeout_secs)
    dataset_id = run["defaultDatasetId"]
    return list(client.dataset(dataset_id).iterate_items())


def summarize_platform_items(
    items: list,
    views_keys: list,
    date_keys: list,
    followers_keys: list = None,
    title_keys: list = None,
    url_keys: list = None,
    platform_name: str = "",
) -> dict:
    """Normaliza los ítems crudos de un actor de Apify a una estructura común."""
    followers_keys = followers_keys or []
    title_keys = title_keys or []
    url_keys = url_keys or []

    filas = []
    seguidores = None
    for it in items:
        vistas = _first_value(it, views_keys) or 0
        fecha = _parse_date(_first_value(it, date_keys))
        fol = _first_value(it, followers_keys)
        if fol is not None and seguidores is None:
            try:
                seguidores = int(fol)
            except (TypeError, ValueError):
                seguidores = fol
        filas.append({
            "titulo": (_first_value(it, title_keys) or "(sin título)")[:120] if isinstance(_first_value(it, title_keys), str) else "(sin título)",
            "vistas": int(vistas) if str(vistas).replace(".", "", 1).isdigit() else 0,
            "fecha": fecha,
            "url": _first_value(it, url_keys),
        })

    filas_ordenadas = sorted(
        filas, key=lambda r: r["fecha"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True
    )
    total = len(filas_ordenadas)
    promedio_vistas = round(sum(r["vistas"] for r in filas_ordenadas) / total, 0) if total else 0
    ultima_publicacion = filas_ordenadas[0]["fecha"] if filas_ordenadas else None

    return {
        "plataforma": platform_name,
        "seguidores": seguidores,
        "videos": filas_ordenadas,
        "promedio_vistas": promedio_vistas,
        "ultima_publicacion": ultima_publicacion,
        "total_analizado": total,
    }


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------
def analyze_tiktok(client: ApifyClient, username: str, max_videos: int = 20) -> dict:
    username_clean = (username or "").strip().lstrip("@")
    run_input = {
        "profiles": [username_clean],
        "resultsPerPage": max_videos,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "shouldDownloadSlideshowImages": False,
    }
    items = run_actor_sync(client, TIKTOK_ACTOR, run_input)
    return summarize_platform_items(
        items,
        views_keys=["playCount", "videoMeta.playCount"],
        date_keys=["createTimeISO", "createTime"],
        followers_keys=["authorMeta.fans", "authorMeta.followerCount"],
        title_keys=["text", "desc"],
        url_keys=["webVideoUrl"],
        platform_name="TikTok",
    )


# ---------------------------------------------------------------------------
# Instagram Reels
# ---------------------------------------------------------------------------
def analyze_instagram(client: ApifyClient, username: str, max_videos: int = 20) -> dict:
    username_clean = (username or "").strip().lstrip("@")

    seguidores = None
    try:
        perfil_items = run_actor_sync(
            client, INSTAGRAM_PROFILE_ACTOR, {"usernames": [username_clean]}
        )
        if perfil_items:
            seguidores = _first_value(
                perfil_items[0], ["followersCount", "edge_followed_by.count"]
            )
    except Exception:
        seguidores = None

    items = run_actor_sync(
        client, INSTAGRAM_REELS_ACTOR, {"username": [username_clean], "resultsLimit": max_videos}
    )
    resultado = summarize_platform_items(
        items,
        views_keys=["videoPlayCount", "videoViewCount", "playsCount"],
        date_keys=["timestamp"],
        title_keys=["caption"],
        url_keys=["url"],
        platform_name="Instagram Reels",
    )
    if seguidores is not None:
        resultado["seguidores"] = seguidores
    return resultado


# ---------------------------------------------------------------------------
# Facebook Video
# ---------------------------------------------------------------------------
def analyze_facebook(client: ApifyClient, page_url: str, max_videos: int = 20) -> dict:
    seguidores = None
    try:
        pagina_items = run_actor_sync(
            client, FACEBOOK_PAGE_ACTOR, {"startUrls": [{"url": page_url}]}
        )
        if pagina_items:
            seguidores = _first_value(pagina_items[0], ["followers", "followersCount", "likes"])
    except Exception:
        seguidores = None

    items = run_actor_sync(
        client,
        FACEBOOK_VIDEOS_ACTOR,
        {"startUrls": [{"url": page_url}], "resultsLimit": max_videos},
    )
    resultado = summarize_platform_items(
        items,
        views_keys=["viewCount", "videoViewCount", "views"],
        date_keys=["time", "date", "publishTime"],
        title_keys=["text", "title"],
        url_keys=["url", "videoUrl"],
        platform_name="Facebook Video",
    )
    if seguidores is not None:
        resultado["seguidores"] = seguidores
    return resultado
