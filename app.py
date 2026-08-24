"""
ClipScope — Herramienta de prospección para servicios de Clipping
===================================================================
App de Streamlit que analiza el desempeño cross-platform de un prospecto
(YouTube, TikTok, Instagram Reels y Facebook Video), genera un panel de
diagnóstico con alertas automáticas y un pitch de ventas personalizado.

Ejecutar localmente:
    streamlit run app.py

Desplegar gratis:
    Streamlit Community Cloud (ver README.md)
"""

import pandas as pd
import streamlit as st

from modules import analysis as an
from modules import apify_service as ays
from modules import export_service as exp
from modules import youtube_service as yts
from modules.ui_helpers import (
    empty_state,
    inject_custom_css,
    render_alert,
    render_bio_badges,
)

# ---------------------------------------------------------------------------
# Configuración general de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ClipScope | Diagnóstico de Clipping",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_custom_css()

DEFAULT_KEYS = ["youtube_data", "tiktok_data", "instagram_data", "facebook_data",
                 "comparative_df", "alerts", "pitch_text", "nombre_prospecto", "errores"]
for key in DEFAULT_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None


# ---------------------------------------------------------------------------
# Funciones cacheadas (evitan volver a golpear las APIs en cada rerun)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def cached_youtube_analysis(api_key: str, channel_input: str):
    return yts.analyze_channel(api_key, channel_input)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_tiktok_analysis(token: str, username: str):
    client = ays.get_apify_client(token)
    return ays.analyze_tiktok(client, username)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_instagram_analysis(token: str, username: str):
    client = ays.get_apify_client(token)
    return ays.analyze_instagram(client, username)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_facebook_analysis(token: str, page_url: str):
    client = ays.get_apify_client(token)
    return ays.analyze_facebook(client, page_url)


# ---------------------------------------------------------------------------
# Sidebar: configuración de API Keys y plataformas
# ---------------------------------------------------------------------------
def _get_secret(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return ""


with st.sidebar:
    st.markdown("## 🔑 API Keys")
    st.caption("Las claves solo se usan en esta sesión de navegador; no se almacenan en el servidor.")

    yt_key_secret = _get_secret("YOUTUBE_API_KEY")
    apify_token_secret = _get_secret("APIFY_TOKEN")

    youtube_api_key = st.text_input(
        "YouTube Data API Key",
        value=yt_key_secret,
        type="password",
        help="Google Cloud Console → APIs y Servicios → Credenciales",
    )
    apify_token = st.text_input(
        "Apify API Token",
        value=apify_token_secret,
        type="password",
        help="console.apify.com → Settings → Integrations",
    )

    if yt_key_secret:
        st.success("YouTube API Key cargada desde secrets ✅")
    if apify_token_secret:
        st.success("Apify Token cargado desde secrets ✅")

    st.divider()
    st.markdown("## 🌐 Plataformas a analizar")
    usar_youtube = st.checkbox("YouTube", value=True)
    usar_tiktok = st.checkbox("TikTok", value=True)
    usar_instagram = st.checkbox("Instagram Reels", value=True)
    usar_facebook = st.checkbox("Facebook Video", value=False)

    st.divider()
    st.caption("💡 ClipScope · Herramienta de prospección para servicios de Clipping")


# ---------------------------------------------------------------------------
# Encabezado y formulario de prospección
# ---------------------------------------------------------------------------
st.markdown("# 🎬 ClipScope")
st.markdown(
    "Analiza el desempeño cross-platform de un prospecto y genera, en segundos, "
    "un diagnóstico con alertas automáticas y un pitch de ventas personalizado."
)

with st.form("prospecto_form"):
    col1, col2 = st.columns(2)
    with col1:
        nombre_prospecto = st.text_input("Nombre del prospecto / marca", placeholder="Ej. Canal de Juan Pérez")
        youtube_url = st.text_input("Canal de YouTube (URL, @handle o ID)", placeholder="https://youtube.com/@usuario")
        tiktok_user = st.text_input("Usuario de TikTok", placeholder="@usuario")
    with col2:
        instagram_user = st.text_input("Usuario de Instagram", placeholder="usuario")
        facebook_url = st.text_input("Página de Facebook (URL)", placeholder="https://facebook.com/pagina")

    submitted = st.form_submit_button("🔍 Analizar prospecto", use_container_width=True)


# ---------------------------------------------------------------------------
# Lógica de análisis al enviar el formulario
# ---------------------------------------------------------------------------
if submitted:
    errores = []

    if usar_youtube and not youtube_api_key:
        errores.append("Falta la YouTube API Key para analizar YouTube.")
    if (usar_tiktok or usar_instagram or usar_facebook) and not apify_token:
        errores.append("Falta el Apify Token para analizar TikTok / Instagram / Facebook.")

    if errores:
        for e in errores:
            st.error(e)
    else:
        youtube_data = tiktok_data = instagram_data = facebook_data = None
        errores_ejecucion = []

        if usar_youtube and youtube_url:
            with st.spinner("Analizando YouTube..."):
                try:
                    youtube_data = cached_youtube_analysis(youtube_api_key, youtube_url)
                    if youtube_data is None:
                        errores_ejecucion.append("No se pudo resolver el canal de YouTube indicado.")
                except Exception as e:
                    errores_ejecucion.append(f"Error en YouTube: {e}")

        if usar_tiktok and tiktok_user:
            with st.spinner("Analizando TikTok..."):
                try:
                    tiktok_data = cached_tiktok_analysis(apify_token, tiktok_user)
                except Exception as e:
                    errores_ejecucion.append(f"Error en TikTok: {e}")

        if usar_instagram and instagram_user:
            with st.spinner("Analizando Instagram..."):
                try:
                    instagram_data = cached_instagram_analysis(apify_token, instagram_user)
                except Exception as e:
                    errores_ejecucion.append(f"Error en Instagram: {e}")

        if usar_facebook and facebook_url:
            with st.spinner("Analizando Facebook..."):
                try:
                    facebook_data = cached_facebook_analysis(apify_token, facebook_url)
                except Exception as e:
                    errores_ejecucion.append(f"Error en Facebook: {e}")

        comparative_df = an.build_comparative_table(youtube_data, tiktok_data, instagram_data, facebook_data)
        alerts = an.generate_alerts(youtube_data, tiktok_data, instagram_data, facebook_data)
        pitch_text = an.generate_pitch(nombre_prospecto, youtube_data, alerts)

        st.session_state["youtube_data"] = youtube_data
        st.session_state["tiktok_data"] = tiktok_data
        st.session_state["instagram_data"] = instagram_data
        st.session_state["facebook_data"] = facebook_data
        st.session_state["comparative_df"] = comparative_df
        st.session_state["alerts"] = alerts
        st.session_state["pitch_text"] = pitch_text
        st.session_state["nombre_prospecto"] = nombre_prospecto
        st.session_state["errores"] = errores_ejecucion

        if errores_ejecucion:
            for e in errores_ejecucion:
                st.warning(e)


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
if st.session_state["comparative_df"] is not None:
    youtube_data = st.session_state["youtube_data"]
    tiktok_data = st.session_state["tiktok_data"]
    instagram_data = st.session_state["instagram_data"]
    facebook_data = st.session_state["facebook_data"]
    comparative_df = st.session_state["comparative_df"]
    alerts = st.session_state["alerts"]
    pitch_text = st.session_state["pitch_text"]
    nombre_prospecto = st.session_state["nombre_prospecto"]

    tab_panel, tab_yt, tab_tiktok, tab_ig, tab_fb, tab_pitch = st.tabs(
        ["📊 Panel Comparativo", "▶️ YouTube", "🎵 TikTok", "📸 Instagram", "📘 Facebook", "✉️ Pitch de Ventas"]
    )

    # --- Panel comparativo ---
    with tab_panel:
        st.subheader("Resumen comparativo cross-platform")
        if comparative_df.empty:
            empty_state("Aún no hay datos para comparar. Completa el formulario y ejecuta el análisis.")
        else:
            st.dataframe(comparative_df, use_container_width=True, hide_index=True)

            grafico_df = comparative_df.dropna(subset=["Prom. Vistas"]).set_index("Plataforma")
            if not grafico_df.empty:
                st.bar_chart(grafico_df["Prom. Vistas"])

            st.subheader("Alertas automáticas")
            if alerts:
                for alerta in alerts:
                    render_alert(alerta)
            else:
                st.info("No se detectaron alertas relevantes con los datos disponibles.")

            st.divider()
            st.subheader("Descargar reporte")
            col_a, col_b = st.columns(2)
            with col_a:
                excel_buffer = exp.export_to_excel(
                    comparative_df, youtube_data, tiktok_data, instagram_data, facebook_data, alerts
                )
                st.download_button(
                    "⬇️ Descargar Excel",
                    data=excel_buffer,
                    file_name=f"clipscope_{(nombre_prospecto or 'prospecto').strip().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with col_b:
                pdf_bytes = exp.export_to_pdf(nombre_prospecto, comparative_df, alerts, pitch_text)
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"clipscope_{(nombre_prospecto or 'prospecto').strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    # --- YouTube ---
    with tab_yt:
        if not youtube_data:
            empty_state("No se analizó YouTube para este prospecto.")
        else:
            overview = youtube_data["overview"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Suscriptores", f"{overview['subscribers']:,}" if overview["subscribers"] is not None else "Oculto")
            col2.metric("Total de videos", f"{overview['total_videos']:,}")
            col3.metric("Vistas totales del canal", f"{overview['total_views']:,}")

            with st.expander("📄 Descripción del canal"):
                st.write(overview["description"] or "Sin descripción.")

            st.markdown("**Enlaces de venta/monetización detectados en la bio:**")
            render_bio_badges(overview["bio_links"])

            st.markdown("**Canales / podcasts vinculados:**")
            linked = youtube_data.get("linked_channels", [])
            if linked:
                st.dataframe(pd.DataFrame(linked), use_container_width=True, hide_index=True)
            else:
                st.caption("No se detectaron canales vinculados en las secciones destacadas.")

            st.divider()
            largos = youtube_data.get("longs", [])
            shorts = youtube_data.get("shorts", [])

            st.markdown("### 🎬 Últimos videos largos")
            if largos:
                st.metric("Promedio de vistas (largos)", f"{sum(v['vistas'] for v in largos) / len(largos):,.0f}")
                df_largos = pd.DataFrame(largos)[["titulo", "vistas", "fecha", "url"]]
                st.dataframe(df_largos, use_container_width=True, hide_index=True)
            else:
                st.caption("No se encontraron videos largos recientes.")

            st.markdown("### ⚡ Últimos Shorts")
            if shorts:
                st.metric("Promedio de vistas (Shorts)", f"{sum(v['vistas'] for v in shorts) / len(shorts):,.0f}")
                df_shorts = pd.DataFrame(shorts)[["titulo", "vistas", "fecha", "url"]]
                st.dataframe(df_shorts, use_container_width=True, hide_index=True)
            else:
                st.caption("No se encontraron Shorts recientes.")

    # --- TikTok / Instagram / Facebook (misma plantilla) ---
    def render_social_tab(data, nombre_plataforma):
        if not data:
            empty_state(f"No se analizó {nombre_plataforma} para este prospecto.")
            return
        col1, col2, col3 = st.columns(3)
        col1.metric("Seguidores", f"{data['seguidores']:,}" if isinstance(data.get("seguidores"), int) else (data.get("seguidores") or "N/D"))
        col2.metric("Promedio de vistas", f"{data['promedio_vistas']:,.0f}")
        ultima = data.get("ultima_publicacion")
        col3.metric("Última publicación", ultima.strftime("%Y-%m-%d") if ultima else "Sin datos")

        videos = data.get("videos", [])
        if videos:
            df_videos = pd.DataFrame(videos)
            st.dataframe(df_videos, use_container_width=True, hide_index=True)
        else:
            st.caption("No se encontraron videos recientes.")

    with tab_tiktok:
        render_social_tab(tiktok_data, "TikTok")

    with tab_ig:
        render_social_tab(instagram_data, "Instagram")

    with tab_fb:
        render_social_tab(facebook_data, "Facebook")

    # --- Pitch de ventas ---
    with tab_pitch:
        st.subheader("Pitch de ventas personalizado")
        st.caption("Usa el ícono de copiar en la esquina del bloque para copiarlo al portapapeles.")
        st.code(pitch_text, language=None)

else:
    st.divider()
    empty_state(
        "Completa el formulario de arriba con al menos una plataforma y presiona "
        "**'Analizar prospecto'** para generar el diagnóstico."
    )
