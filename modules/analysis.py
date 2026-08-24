"""
analysis.py
-----------
Construye la tabla comparativa cross-platform, el motor de alertas
automáticas y el generador de pitch de ventas personalizado.
"""

from datetime import datetime, timezone

import pandas as pd


def _avg(valores: list) -> float:
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores), 0) if valores else 0.0


def _to_utc(fecha):
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def _fmt_date(fecha):
    if fecha is None:
        return "Sin datos"
    return fecha.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Tabla comparativa
# ---------------------------------------------------------------------------
def build_comparative_table(youtube_data, tiktok_data, instagram_data, facebook_data) -> pd.DataFrame:
    filas = []

    if youtube_data:
        overview = youtube_data.get("overview", {}) or {}
        largos = youtube_data.get("longs", [])
        shorts = youtube_data.get("shorts", [])

        filas.append({
            "Plataforma": "YouTube (Videos largos)",
            "Seguidores": overview.get("subscribers"),
            "Prom. Vistas": _avg([v["vistas"] for v in largos]),
            "Última Publicación": _fmt_date(largos[0]["fecha"]) if largos else "Sin datos",
            "Contenidos Analizados": len(largos),
        })
        filas.append({
            "Plataforma": "YouTube Shorts",
            "Seguidores": overview.get("subscribers"),
            "Prom. Vistas": _avg([v["vistas"] for v in shorts]),
            "Última Publicación": _fmt_date(shorts[0]["fecha"]) if shorts else "Sin datos",
            "Contenidos Analizados": len(shorts),
        })

    for etiqueta, data in (
        ("TikTok", tiktok_data),
        ("Instagram Reels", instagram_data),
        ("Facebook Video", facebook_data),
    ):
        if data:
            filas.append({
                "Plataforma": etiqueta,
                "Seguidores": data.get("seguidores"),
                "Prom. Vistas": data.get("promedio_vistas"),
                "Última Publicación": _fmt_date(data.get("ultima_publicacion")),
                "Contenidos Analizados": data.get("total_analizado"),
            })

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Motor de alertas
# ---------------------------------------------------------------------------
def generate_alerts(youtube_data, tiktok_data, instagram_data, facebook_data) -> list:
    alertas = []
    now = datetime.now(timezone.utc)

    # --- Alerta 1: "Atención" — largos superan 3x a los cortos ---
    if youtube_data:
        largos = youtube_data.get("longs", [])
        shorts = youtube_data.get("shorts", [])
        avg_largos = _avg([v["vistas"] for v in largos])

        promedios_cortos = []
        if shorts:
            promedios_cortos.append(_avg([v["vistas"] for v in shorts]))
        for data in (tiktok_data, instagram_data, facebook_data):
            if data and data.get("promedio_vistas"):
                promedios_cortos.append(data["promedio_vistas"])

        if promedios_cortos:
            avg_cortos_combinado = _avg(promedios_cortos)
            if avg_cortos_combinado > 0 and avg_largos > 3 * avg_cortos_combinado:
                alertas.append({
                    "tipo": "Atención",
                    "nivel": "warning",
                    "mensaje": (
                        f"Los videos largos generan {avg_largos:,.0f} vistas promedio, "
                        f"más de 3 veces el promedio del contenido corto ({avg_cortos_combinado:,.0f}). "
                        "Hay una oportunidad clara de Clipping para capturar esa audiencia en formato corto."
                    ),
                })

    # --- Alerta 2: "Inactividad" — sin contenido corto en 14+ días ---
    ultimas_fechas_cortas = []
    if youtube_data and youtube_data.get("shorts"):
        ultimas_fechas_cortas.append(_to_utc(youtube_data["shorts"][0]["fecha"]))
    for data in (tiktok_data, instagram_data, facebook_data):
        if data and data.get("ultima_publicacion"):
            ultimas_fechas_cortas.append(_to_utc(data["ultima_publicacion"]))

    ultimas_fechas_cortas = [f for f in ultimas_fechas_cortas if f is not None]
    if ultimas_fechas_cortas:
        mas_reciente = max(ultimas_fechas_cortas)
        dias_inactivo = (now - mas_reciente).days
        if dias_inactivo >= 14:
            alertas.append({
                "tipo": "Inactividad",
                "nivel": "error",
                "mensaje": (
                    f"No se detecta contenido corto nuevo en los últimos {dias_inactivo} días. "
                    "Riesgo de pérdida de alcance por inactividad en los algoritmos de recomendación."
                ),
            })

    # --- Alerta 3: "Monetización Alta" — vende productos en la bio ---
    if youtube_data:
        bio_links = (youtube_data.get("overview", {}) or {}).get("bio_links", {}) or {}
        if bio_links.get("tiene_venta"):
            tipos = ", ".join(bio_links.get("tipos_detectados", []))
            alertas.append({
                "tipo": "Monetización Alta",
                "nivel": "success",
                "mensaje": (
                    f"Se detectaron enlaces de venta/monetización en la biografía ({tipos}). "
                    "Alta probabilidad de presupuesto activo para marketing y producción de contenido."
                ),
            })

    return alertas


# ---------------------------------------------------------------------------
# Generador de pitch de ventas
# ---------------------------------------------------------------------------
def generate_pitch(nombre_prospecto: str, youtube_data, alertas: list) -> str:
    hallazgos = []

    if youtube_data:
        overview = youtube_data.get("overview", {}) or {}
        subs = overview.get("subscribers")
        if subs:
            hallazgos.append(f"- {subs:,} suscriptores en YouTube")
        total_videos = overview.get("total_videos")
        if total_videos:
            hallazgos.append(f"- {total_videos:,} videos publicados en el canal")

    for alerta in alertas:
        hallazgos.append(f"- [{alerta['tipo']}] {alerta['mensaje']}")

    bloque_hallazgos = "\n".join(hallazgos) if hallazgos else (
        "- Presencia activa en múltiples plataformas con potencial de crecimiento en formato corto."
    )

    nombre = nombre_prospecto.strip() if nombre_prospecto and nombre_prospecto.strip() else "su equipo"

    pitch = f"""Hola {nombre},

Analizamos su presencia digital en las plataformas donde publican contenido y detectamos una oportunidad concreta para potenciar su alcance a través de un servicio de Clipping profesional.

Hallazgos clave del diagnóstico:
{bloque_hallazgos}

Con un servicio de Clipping especializado podemos ayudarles a:
- Convertir su contenido largo en piezas cortas de alto impacto para TikTok, Reels y Shorts
- Mantener una cadencia de publicaciones constante para evitar caídas de alcance por inactividad
- Aprovechar el interés ya validado de su audiencia actual para maximizar conversiones

¿Tienen 15 minutos esta semana para mostrarles una propuesta con ejemplos reales editados a partir de su propio contenido?

Saludos,
[Tu nombre / Tu agencia]
"""
    return pitch
