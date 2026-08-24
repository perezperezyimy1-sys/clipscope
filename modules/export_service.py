"""
export_service.py
------------------
Exporta los resultados del diagnóstico a Excel (multi-hoja) y a un
reporte PDF resumido, listos para descargar desde la interfaz de Streamlit.
"""

import io

import pandas as pd
from fpdf import FPDF


def export_to_excel(comparative_df, youtube_data, tiktok_data, instagram_data, facebook_data, alerts) -> io.BytesIO:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        comparative_df.to_excel(writer, sheet_name="Resumen Comparativo", index=False)

        if alerts:
            pd.DataFrame(alerts)[["tipo", "mensaje"]].rename(
                columns={"tipo": "Alerta", "mensaje": "Detalle"}
            ).to_excel(writer, sheet_name="Alertas", index=False)

        if youtube_data:
            if youtube_data.get("longs"):
                pd.DataFrame(youtube_data["longs"]).drop(columns=["video_id"], errors="ignore").to_excel(
                    writer, sheet_name="YT Videos Largos", index=False
                )
            if youtube_data.get("shorts"):
                pd.DataFrame(youtube_data["shorts"]).drop(columns=["video_id"], errors="ignore").to_excel(
                    writer, sheet_name="YT Shorts", index=False
                )
            if youtube_data.get("linked_channels"):
                pd.DataFrame(youtube_data["linked_channels"]).to_excel(
                    writer, sheet_name="YT Canales Vinculados", index=False
                )

        for nombre, data in (
            ("TikTok", tiktok_data),
            ("Instagram", instagram_data),
            ("Facebook", facebook_data),
        ):
            if data and data.get("videos"):
                pd.DataFrame(data["videos"]).to_excel(writer, sheet_name=f"{nombre} Videos", index=False)

    buffer.seek(0)
    return buffer


def _safe_text(value) -> str:
    """Evita errores de codificación con las fuentes core (latin-1) de fpdf2."""
    if value is None:
        return ""
    texto = str(value)
    return texto.encode("latin-1", "replace").decode("latin-1")


def export_to_pdf(nombre_prospecto: str, comparative_df: pd.DataFrame, alerts: list, pitch_text: str) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe_text(f"Diagnóstico de Clipping — {nombre_prospecto or 'Prospecto'}"), ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _safe_text("Generado con ClipScope"), ln=True)
    pdf.ln(4)

    # --- Tabla comparativa ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Resumen Comparativo", ln=True)

    if not comparative_df.empty:
        col_width = pdf.epw / len(comparative_df.columns)
        pdf.set_font("Helvetica", "B", 8)
        for col in comparative_df.columns:
            pdf.cell(col_width, 7, _safe_text(col), border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for _, fila in comparative_df.iterrows():
            for col in comparative_df.columns:
                pdf.cell(col_width, 7, _safe_text(fila[col])[:24], border=1)
            pdf.ln()
    else:
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "Sin datos disponibles.", ln=True)

    pdf.ln(6)

    # --- Alertas ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Alertas Detectadas", ln=True)
    pdf.set_font("Helvetica", "", 9)
    if alerts:
        for alerta in alerts:
            pdf.multi_cell(0, 6, _safe_text(f"[{alerta['tipo']}] {alerta['mensaje']}"))
            pdf.ln(1)
    else:
        pdf.cell(0, 6, "No se detectaron alertas relevantes.", ln=True)

    pdf.ln(4)

    # --- Pitch de ventas ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Pitch de Ventas Sugerido", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6, _safe_text(pitch_text))

    salida = pdf.output()
    return bytes(salida)
