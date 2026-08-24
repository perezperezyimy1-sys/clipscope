"""
ui_helpers.py
-------------
Estilos CSS y componentes visuales reutilizables para darle a la app
una estética de producto SaaS limpia y moderna.
"""

import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
        :root {
            --cs-primary: #4F46E5;
            --cs-primary-light: #EEF2FF;
            --cs-bg-card: #FFFFFF;
            --cs-border: #E5E7EB;
            --cs-text-muted: #6B7280;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }

        /* Tarjetas de métricas nativas de Streamlit */
        div[data-testid="stMetric"] {
            background-color: var(--cs-bg-card);
            border: 1px solid var(--cs-border);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }
        div[data-testid="stMetricLabel"] {
            color: var(--cs-text-muted);
        }

        /* Botones primarios */
        div.stButton > button, div.stFormSubmitButton > button {
            background-color: var(--cs-primary);
            color: white;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            padding: 0.55rem 1.2rem;
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            background-color: #4338CA;
            color: white;
        }

        /* Pestañas */
        button[data-baseweb="tab"] {
            font-weight: 600;
        }

        /* Badges para enlaces de bio detectados */
        .cs-badge {
            display: inline-block;
            background-color: var(--cs-primary-light);
            color: var(--cs-primary);
            border-radius: 999px;
            padding: 0.2rem 0.75rem;
            margin: 0.15rem 0.25rem 0.15rem 0;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .cs-subtle {
            color: var(--cs-text-muted);
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_alert(alerta: dict):
    """Renderiza una alerta con el color/ícono correspondiente a su nivel."""
    nivel = alerta.get("nivel", "warning")
    icono = {"warning": "⚠️", "error": "🔴", "success": "🟢"}.get(nivel, "ℹ️")
    texto = f"**{icono} {alerta['tipo']}** — {alerta['mensaje']}"
    if nivel == "warning":
        st.warning(texto)
    elif nivel == "error":
        st.error(texto)
    elif nivel == "success":
        st.success(texto)
    else:
        st.info(texto)


def render_bio_badges(bio_links: dict):
    """Muestra los tipos de enlaces de venta/monetización detectados como badges."""
    tipos = bio_links.get("tipos_detectados", []) if bio_links else []
    if not tipos:
        st.caption("No se detectaron enlaces de venta/monetización en la biografía.")
        return
    html = "".join(f'<span class="cs-badge">{t}</span>' for t in tipos)
    st.markdown(html, unsafe_allow_html=True)


def empty_state(mensaje: str):
    st.info(mensaje)
