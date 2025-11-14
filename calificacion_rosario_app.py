# ===============================================
#  Universidad del Rosario – Calificación (Streamlit)
#  - Ítems con "No aplica" y reponderación al 100%
#  - PDF tabulado (formato carta) con ajuste de texto
#  - 3 líneas de observaciones y pie (Nombre, Firma, Fecha)
# ===============================================

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ReportLab (PDF)
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import (
    Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

st.set_page_config(page_title="Calificación – Universidad del Rosario", layout="wide")

# -----------------------------
# Configuración del instrumento
# -----------------------------
SECCIONES = {
    "1. CONOCIMIENTOS (35%)": {
        "peso": 0.35,
        "items": [
            "1.1 Conocimientos ciencias",
            "1.2 Conocimientos clínicos generales",
            "1.3 Conocimientos de fisiopatología",
            "1.4 Conocimientos de terapéutica",
            "1.5 Conocimientos de la especialidad específicos al final de la rotación",
        ],
    },
    "2. HABILIDADES EN LA PRÁCTICA CLÍNICA (35%)": {
        "peso": 0.35,
        "items": [
            "2.1 Elaboración de historias clínicas",
            "2.2 Práctica del examen físico de rutina",
            "2.3 Habilidad de la práctica de procedimientos diagnósticos especiales",
            "2.4 Conocimientos de las historias clínicas de sus pacientes",
            "2.5 Interpretación de exámenes clínicos y paraclínicos",
            "2.6 Habilidad y técnica en procedimientos médicos o quirúrgicos",
            "2.7 Participación en reuniones científicas",
            "2.8 Elaboración de informes",
            "2.9 Criterio clínico y terapéutico",
        ],
    },
    "3. ACTITUDES Y VALORES (30%)": {
        "peso": 0.30,
        "items": [
            "3.1 Relaciones con los pacientes y sus familias",
            "3.2 Relaciones con el personal del escenario de práctica",
            "3.3 Relaciones con sus compañeros y personal en formación",
            "3.4 Relaciones con sus docentes y superiores",
            "3.5 Responsabilidad en el cuidado de los pacientes",
            "3.6 Responsabilidad en las actividades médicas de rutina",
            "3.7 Cumplimiento",
            "3.8 Iniciativa",
        ],
    },
}

# -----------------------------
# Utilidades
# -----------------------------
def fmt_nota(val):
    return "N/A" if val is None else f"{val:.2f}"

def promedio_sin_na(valores):
    v = [x for x in valores if x is not None]
    if not v:
        return None
    return round(sum(v) / len(v), 2)

# -----------------------------
# UI – Encabezado y datos
# -----------------------------
st.title("Universidad del Rosario – Formato de Calificación (Automático)")

with st.expander("Datos del estudiante / rotación", expanded=True):
    colA, colB = st.columns(2)
    nombre = colA.text_input("Nombres y apellidos")
    rotacion = colB.text_input("Rotación")
    periodo = colA.text_input("Periodo")
    hospital = colB.text_input("Hospital")
    programa = colA.text_input("Programa")
    evaluador = colB.text_input("Nombre del calificador")
    firma = colA.text_input("Firma (texto para PDF)")
    fecha_texto = colB.text_input("Fecha (si vacío, hoy)", value=datetime.now().strftime("%Y-%m-%d"))

with st.expander("Logo institucional (opcional)", expanded=False):
    st.write("Puedes **subir un logo** (.png/.jpg). Si no cargas nada, se intentará usar `logo_rosario.png` junto al archivo.")
    uploaded_logo = st.file_uploader("Subir logo", type=["png", "jpg", "jpeg"])

st.markdown("---")
st.markdown("Ingrese calificaciones **entre 0.00 y 5.00**. Marque **No aplica** si no corresponde.")

# -----------------------------
# Entrada de notas con "No aplica"
# -----------------------------
detalle_rows = []
promedios_seccion = {}

for titulo_seccion, cfg in SECCIONES.items():
    peso = cfg["peso"]
    items = cfg["items"]

    st.subheader(titulo_seccion)
    head = st.columns([3, 1, 1])
    head[0].caption("Ítem")
    head[1].caption("Calificación (0–5)")
    head[2].caption("No aplica")

    notas = []
    for it in items:
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1: st.markdown(f"- {it}")
        with c3: na = st.checkbox(" ", key=f"na_{it}")
        with c2:
            n = st.number_input(
                "", min_value=0.00, max_value=5.00, step=0.01,
                format="%.2f", value=0.00, disabled=na, key=f"nota_{it}",
            )
        nota = None if na else float(n)
        notas.append(nota)
        detalle_rows.append({"Sección": titulo_seccion, "Ítem": it, "Calificación": nota})

    prom = promedio_sin_na(notas)
    promedios_seccion[titulo_seccion] = prom
    st.info(f"**PROMEDIO {titulo_seccion}: {fmt_nota(prom)}** (peso {int(peso*100)}%)")

# -----------------------------
# Nota final con reponderación (100%)
# -----------------------------
pesos_originales = {sec: cfg["peso"] for sec, cfg in SECCIONES.items()}
secciones_activas = {sec for sec, prom in promedios_seccion.items() if prom is not None}
peso_total_activo = sum(pesos_originales[s] for s in secciones_activas)

if peso_total_activo > 0:
    nota_final = sum(
        promedios_seccion[sec] * (pesos_originales[sec] / peso_total_activo)
        for sec in secciones_activas
    )
    nota_final = round(nota_final, 2)
else:
    nota_final = None

aprobado = None if nota_final is None else ("Sí" if nota_final >= 3.00 else "No")

st.markdown("---")
st.success(f"**NOTA FINAL:** {fmt_nota(nota_final)}  |  **Aprobado (≥ 3.00):** {aprobado or 'N/A'}")

df_detalle = pd.DataFrame(detalle_rows)

# -----------------------------
# Observaciones (3 líneas)
# -----------------------------
st.subheader("Observaciones")
obs1 = st.text_input("Observación 1")
obs2 = st.text_input("Observación 2")
obs3 = st.text_input("Observación 3")

# -----------------------------
# PDF – Tablas con ajuste de texto (formato carta)
# -----------------------------
def generar_pdf(
    nombre, rotacion, periodo, hospital, programa, evaluador, firma, fecha_texto,
    promedios_seccion, pesos_originales, secciones_activas,
    nota_final, aprobado, df_detalle,
    obs1, obs2, obs3,
    uploaded_logo=None, default_logo_path="logo_rosario.png",
):
    # Configuración de página carta con márgenes 0.5"
    PAGE_W, PAGE_H = LETTER
    LM = RM = TM = BM = 36  # 0.5 inch
    usable_w = PAGE_W - LM - RM

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        rightMargin=RM, leftMargin=LM, topMargin=TM, bottomMargin=BM
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Header", fontSize=12, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="Section", fontSize=11, leading=13, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(
        name="SmallWrap", fontSize=9, leading=11,
        wordWrap="CJK"  # permite cortar palabras largas
    ))

    def P(txt, style="SmallWrap"):
        # Paragraph con splitLongWords para evitar desbordes
        return Paragraph(str(txt if txt is not None else ""), styles[style])

    elems = []

    # Logo (si existe)
    logo_flowable = None
    if uploaded_logo is not None:
        try:
            logo_flowable = Image(uploaded_logo, width=200, height=60)
        except Exception:
            logo_flowable = None
    else:
        p = Path(default_logo_path)
        if p.exists():
            try:
                logo_flowable = Image(str(p), width=200, height=60)
            except Exception:
                logo_flowable = None
    if logo_flowable:
        elems.append(logo_flowable)
        elems.append(Spacer(1, 6))

    # Encabezado
    elems.append(Paragraph("Universidad del Rosario<br/>Escuela de Medicina y Ciencias de la Salud", styles["Header"]))
    elems.append(Paragraph("<b>Formato de Calificación – Especializaciones Médico Quirúrgicas</b>", styles["Header"]))
    elems.append(Spacer(1, 6))

    instr = ("Coloque en frente del parámetro a evaluar la calificación obtenida por el residente "
             "siendo 0,0 la más baja y 5,0 la más alta. La mínima nota aprobatoria es 3,0. "
             "Para la calificación final: Conocimientos 35%, Habilidades 35%, Actitudes/Valores 30%.")
    elems.append(Paragraph(instr, styles["Small"]))
    elems.append(Spacer(1, 6))

    # Datos
    datos = [
        [P("NOMBRES Y APELLIDOS:"), P(nombre or "")],
        [P("ROTACIÓN:"), P(rotacion or ""), P("PERIODO:"), P(periodo or "")],
        [P("HOSPITAL:"), P(hospital or ""), P("PROGRAMA:"), P(programa or "")],
    ]
    t_datos = Table(datos, colWidths=[1.8*inch, 4.1*inch, 1.0*inch, 1.0*inch])
    t_datos.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (0,0), colors.whitesmoke),
    ]))
    elems.append(t_datos)
    elems.append(Spacer(1, 8))

    # Anchos fijos para que no se salga en carta
    col_param = 6.0 * inch
    col_calif = usable_w - col_param  # ~1.5"

    # Tablas por sección
    for titulo_seccion, cfg in SECCIONES.items():
        elems.append(Paragraph(titulo_seccion, styles["Section"]))

        filas = [[P("Parámetro", "Small"), P("Calificación (0–5)", "Small")]]
        sub = df_detalle[df_detalle["Sección"] == titulo_seccion]
        for _, r in sub.iterrows():
            val = "N/A" if r["Calificación"] is None else f"{float(r['Calificación']):.2f}"
            filas.append([P(r["Ítem"]), Paragraph(val, styles["Small"])])

        prom = promedios_seccion[titulo_seccion]
        filas.append([Paragraph("<b>PROMEDIO</b>", styles["Small"]), Paragraph(f"<b>{fmt_nota(prom)}</b>", styles["Small"])])

        t_sec = Table(filas, colWidths=[col_param, col_calif])
        t_sec.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.25, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
            ("ALIGN", (1,1), (1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elems.append(t_sec)
        elems.append(Spacer(1, 8))

    # Nota final y leyenda
    elems.append(Paragraph(f"<b>NOTA FINAL:</b> {fmt_nota(nota_final)} – Aprobado: {aprobado or 'N/A'}", styles["Section"]))
    leyenda = ("Nota: Ítems marcados como N/A no computan. Si una sección queda completamente N/A, "
               "su peso se redistribuye proporcionalmente entre las secciones activas (suma total 100%).")
    elems.append(Paragraph(leyenda, styles["Small"]))
    elems.append(Spacer(1, 10))

    # Observaciones
    elems.append(Paragraph("OBSERVACIONES:", styles["Section"]))
    t_obs = Table([[P(obs1 or "")],[P(obs2 or "")],[P(obs3 or "")]],
                  colWidths=[usable_w], rowHeights=[0.45*inch, 0.45*inch, 0.45*inch])
    t_obs.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.25, colors.black),
        ("GRID", (0,0), (-1,-1), 0.25, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    elems.append(t_obs)
    elems.append(Spacer(1, 12))

    # Pie
    t_pie = Table(
        [
            [P("NOMBRE DEL CALIFICADOR(ES):"), P(evaluador or "")],
            [P("FIRMA:"), P(firma or ""), P("FECHA:"), P(fecha_texto or "")],
        ],
        colWidths=[2.5*inch, 2.2*inch, 0.8*inch, 1.4*inch],
    )
    t_pie.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(t_pie)

    doc.build(elems)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# -----------------------------
# Botón de descarga
# -----------------------------
pdf_bytes = generar_pdf(
    nombre, rotacion, periodo, hospital, programa, evaluador, firma, fecha_texto,
    promedios_seccion, pesos_originales, secciones_activas,
    nota_final, aprobado, df_detalle,
    obs1, obs2, obs3,
    uploaded_logo=uploaded_logo,
)

st.download_button(
    label="📄 Descargar PDF de calificación",
    data=pdf_bytes,
    file_name=f"Calificacion_{(nombre or 'estudiante').replace(' ', '_')}.pdf",
    mime="application/pdf",
)
