import io
from pathlib import Path
import tempfile
import zipfile

import pandas as pd
import streamlit as st

from rfess_engine_open import (
    DEFAULT_POINTS,
    calculate_classifications,
    build_scored_rows,
    load_aliases,
    make_quality_report,
    normalize_liveheats,
    parse_blocks_text,
    read_liveheats_csv,
    apply_no_score_overrides,
)
from rfess_pdf_open import build_pdf

APP_VERSION = "Versión definitiva limpia"
ALL_SEXES_DEFAULT = ["femenina", "masculina", "mixta"]
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "rfess_logo.jpg"
RFESS_BLUE = "#2E5B92"
RFESS_RED = "#C8102E"
RFESS_YELLOW = "#F2D335"

st.set_page_config(
    page_title="RFESS | Clasificaciones desde LiveHeats",
    layout="wide",
    page_icon="🏊",
)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 220px);
        }}
        .hero {{
            background: white;
            border-radius: 18px;
            padding: 1.2rem 1.4rem;
            box-shadow: 0 8px 30px rgba(46, 91, 146, 0.10);
            border: 1px solid rgba(46, 91, 146, 0.10);
            margin-bottom: 1rem;
        }}
        .hero h1 {{
            color: {RFESS_BLUE};
            margin: 0 0 0.25rem 0;
            font-size: 2rem;
            line-height: 1.15;
        }}
        .hero p {{
            margin: 0.2rem 0;
            color: #394150;
            font-size: 1rem;
        }}
        .pill {{
            display: inline-block;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            background: rgba(46, 91, 146, 0.10);
            color: {RFESS_BLUE};
            font-size: 0.86rem;
            font-weight: 600;
            margin-right: 0.35rem;
            margin-top: 0.3rem;
        }}
        .card {{
            background: white;
            border: 1px solid #e8edf5;
            border-left: 6px solid {RFESS_BLUE};
            border-radius: 16px;
            padding: 1rem 1rem 0.85rem 1rem;
            box-shadow: 0 3px 14px rgba(0,0,0,0.04);
            margin-bottom: 1rem;
        }}
        .card h3 {{
            margin: 0 0 0.4rem 0;
            color: {RFESS_BLUE};
            font-size: 1.1rem;
        }}
        .mini-note {{
            font-size: 0.93rem;
            color: #5c6675;
        }}
        .section-title {{
            color: {RFESS_BLUE};
            margin-top: 0.4rem;
        }}
        div[data-testid="stMetricValue"] {{
            color: {RFESS_BLUE};
        }}
        div[data-testid="stSidebar"] .stFileUploader label p,
        div[data-testid="stSidebar"] label p {{
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    left, right = st.columns([1.1, 4.2], vertical_alignment="center")
    with left:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
    with right:
        st.markdown(
            f"""
            <div class="hero">
                <h1>Clasificaciones RFESS desde LiveHeats</h1>
                <p><strong>Aplicativo privado de apoyo</strong> para generar clasificaciones RFESS, PDF publicable y auditoría.</p>
                <p>Sube el archivo de LiveHeats <strong>“Clasificaciones finales de la categoría (CSV)”</strong> y construye las clasificaciones que necesites.</p>
                <div>
                    <span class="pill">100% en castellano</span>
                    <span class="pill">Constructor visual</span>
                    <span class="pill">CSV RFESS + PDF</span>
                    <span class="pill">Versión {APP_VERSION}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def categories_label(values):
    return ",".join(values) if values else ""


def sexes_label(values):
    return ",".join(values) if values else ""


def all_available_sexes(sexes):
    ordered = [s for s in ALL_SEXES_DEFAULT if s in sexes]
    ordered += [s for s in sexes if s not in ordered]
    return ordered


def add_block(block, categories, sexes):
    if not block or not categories or not sexes:
        return
    row = {
        "usar": True,
        "block": str(block).strip(),
        "categories": categories_label(categories) if categories != ["*"] else "*",
        "sexes": sexes_label(sexes) if sexes != ["*"] else "*",
    }
    existing = st.session_state.get("visual_blocks", [])
    key = (row["block"], row["categories"], row["sexes"])
    if key not in {(r.get("block"), r.get("categories"), r.get("sexes")) for r in existing}:
        existing.append(row)
    st.session_state["visual_blocks"] = existing


def add_category_joint_blocks(categories, sexes):
    for c in categories:
        add_block(f"{c.capitalize()} conjunta", [c], sexes)


def add_category_sex_blocks(categories, sexes):
    for c in categories:
        for s in sexes:
            add_block(f"{c.capitalize()} {s}", [c], [s])


def detected_key(categories, sexes):
    return "|".join(categories) + "__" + "|".join(sexes)


inject_css()
render_hero()

with st.sidebar:
    st.markdown("## 1. Carga de archivos")
    leaderboard_file = st.file_uploader(
        "Archivo obligatorio: “Clasificaciones finales de la categoría (CSV)”",
        type=["csv"],
        help="Es el archivo principal del informe de LiveHeats que actúa como leaderboard final.",
    )
    results_file = st.file_uploader(
        "Archivo opcional: “Detalle de resultados y puntajes (CSV)”",
        type=["csv"],
        help="Muy recomendable cuando exista. Ayuda a corregir No presentado, DQ, DNS o DNF que a veces el leaderboard no refleja bien.",
    )
    aliases_file = st.file_uploader(
        "Archivo opcional: alias o correcciones de clubes",
        type=["csv"],
        help="Plantilla disponible en la carpeta examples.",
    )

    st.markdown("## 2. Reglas RFESS")
    max_per_club = st.number_input(
        "Máximo de deportistas por club en pruebas individuales",
        min_value=1,
        max_value=10,
        value=3,
    )
    top_limit = st.number_input("Límite puntuable", min_value=1, max_value=50, value=16)
    score_source_label = st.selectbox(
        "Fuente de puntos",
        [
            "Automática: usar pointscore de LiveHeats si existe",
            "Usar solo pointscore de LiveHeats",
            "Calcular con tabla RFESS",
        ],
        index=0,
        help="Recomendado: Automática. Si el CSV trae “Club pointscore points”, la app usará esos puntos como base antes de aplicar la regla RFESS.",
    )
    score_source = {
        "Automática: usar pointscore de LiveHeats si existe": "auto",
        "Usar solo pointscore de LiveHeats": "liveheats",
        "Calcular con tabla RFESS": "table",
    }[score_source_label]
    limit_mode = st.selectbox(
        "Modo de corte top en individuales cuando no hay pointscore",
        ["ordinal", "place"],
        index=0,
        help="ordinal = top 16 por orden del listado. place = usa la posición oficial “Place”.",
    )
    st.markdown(
        '<div class="mini-note">Regla habitual RFESS: máximo 3 deportistas por club solo en pruebas individuales. En relevos/equipos el club puntúa normal.</div>',
        unsafe_allow_html=True,
    )

if not leaderboard_file:
    st.markdown(
        """
        <div class="card">
            <h3>Archivo que debes subir</h3>
            <p>Desde <strong>LiveHeats → Informes</strong>, descarga el CSV llamado:</p>
            <p><strong>Clasificaciones finales de la categoría (CSV)</strong></p>
            <p class="mini-note">Ese es el archivo principal para generar las clasificaciones. Si además tienes “Detalle de resultados y puntajes (CSV)”, súbelo también como apoyo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

aliases = load_aliases(aliases_file)
raw = read_liveheats_csv(leaderboard_file)
norm = normalize_liveheats(raw, aliases=aliases)
scored = build_scored_rows(norm, DEFAULT_POINTS, int(max_per_club), int(top_limit), limit_mode, score_source)
results_overrides = pd.DataFrame()
if results_file is not None:
    detailed_results = read_liveheats_csv(results_file)
    scored, results_overrides = apply_no_score_overrides(scored, detailed_results)

categories = sorted([c for c in norm["category"].dropna().unique() if c != "sin_categoria"])
sexes = sorted([s for s in norm["sex"].dropna().unique() if s != "sin_sexo"])
sexes_ordered = all_available_sexes(sexes)
key = detected_key(categories, sexes_ordered)

if "builder_detected_key" not in st.session_state or st.session_state["builder_detected_key"] != key:
    st.session_state["builder_detected_key"] = key
    initial_sexes = sexes_ordered if sexes_ordered else ALL_SEXES_DEFAULT
    st.session_state["visual_blocks"] = [{
        "usar": True,
        "block": "General campeonato",
        "categories": "*",
        "sexes": sexes_label(initial_sexes),
    }]

st.markdown("## Resumen del campeonato detectado")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Filas", len(norm))
c2.metric("Pruebas", norm["division"].nunique())
c3.metric("Categorías", len(categories))
c4.metric("Clubes", norm["club"].nunique())

st.markdown(
    f"""
    <div class="card">
        <h3>Detección automática</h3>
        <p><strong>Categorías detectadas:</strong> {', '.join(categories) if categories else '-'}</p>
        <p><strong>Sexos detectados:</strong> {', '.join(sexes_ordered) if sexes_ordered else '-'}</p>
        <p><strong>Columna de puntos LiveHeats:</strong> {'Sí' if (norm['liveheats_points'].notna().sum() > 0) else 'No'}</p>
        <p><strong>Ajustes desde detalle de resultados:</strong> {len(results_overrides)} registro(s)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Ver pruebas detectadas"):
    divisions = norm.groupby(["category", "sex", "division"], dropna=False).agg(
        filas=("division", "size"), equipo=("is_team_event", "max")
    ).reset_index()
    st.dataframe(divisions, use_container_width=True, hide_index=True)

st.markdown("## Constructor visual de clasificaciones")
st.caption("Añade las clasificaciones con botones rápidos o creando una a medida.")

st.markdown("### 1. Botones rápidos")
preset_cols = st.columns(4)
with preset_cols[0]:
    if st.button("+ General campeonato", use_container_width=True):
        add_block("General campeonato", ["*"], sexes_ordered or ALL_SEXES_DEFAULT)
with preset_cols[1]:
    if st.button("+ Generales por sexo", use_container_width=True):
        for s in sexes_ordered:
            add_block(f"General {s}", ["*"], [s])
with preset_cols[2]:
    if st.button("+ Conjunta por categoría", use_container_width=True):
        add_category_joint_blocks(categories, sexes_ordered or ALL_SEXES_DEFAULT)
with preset_cols[3]:
    if st.button("+ Categoría + sexo", use_container_width=True):
        add_category_sex_blocks(categories, sexes_ordered or ALL_SEXES_DEFAULT)

preset_cols2 = st.columns(4)
with preset_cols2[0]:
    if {"infantil", "cadete"}.issubset(set(categories)):
        if st.button("+ General Infantil y Cadete", use_container_width=True):
            add_block("General Infantil y Cadete", ["infantil", "cadete"], sexes_ordered or ALL_SEXES_DEFAULT)
    else:
        st.button("+ General Infantil y Cadete", disabled=True, use_container_width=True)
with preset_cols2[1]:
    if {"benjamin", "alevin"}.issubset(set(categories)):
        if st.button("+ General Benjamín y Alevín", use_container_width=True):
            add_block("General Benjamín y Alevín", ["benjamin", "alevin"], sexes_ordered or ALL_SEXES_DEFAULT)
    else:
        st.button("+ General Benjamín y Alevín", disabled=True, use_container_width=True)
with preset_cols2[2]:
    if {"juvenil", "junior"}.issubset(set(categories)):
        if st.button("+ General Juvenil y Júnior", use_container_width=True):
            add_block("General Juvenil y Júnior", ["juvenil", "junior"], sexes_ordered or ALL_SEXES_DEFAULT)
    else:
        st.button("+ General Juvenil y Júnior", disabled=True, use_container_width=True)
with preset_cols2[3]:
    if st.button("Vaciar lista", use_container_width=True):
        st.session_state["visual_blocks"] = []

st.markdown("### 2. Crear una clasificación a medida")
with st.form("form_add_block", clear_on_submit=False):
    f1, f2, f3 = st.columns([1.4, 1.4, 1.2])
    with f1:
        block_name = st.text_input("Nombre de la clasificación", value="General Infantil y Cadete")
    with f2:
        selected_categories = st.multiselect("Categorías incluidas", options=categories, default=categories)
    with f3:
        selected_sexes = st.multiselect("Sexos incluidos", options=sexes_ordered, default=sexes_ordered)
    submitted = st.form_submit_button("Añadir clasificación")
    if submitted:
        add_block(block_name, selected_categories, selected_sexes)
        st.success(f"Clasificación añadida: {block_name}")

st.markdown("### 3. Lista final de clasificaciones")
visual_df = pd.DataFrame(st.session_state.get("visual_blocks", []))
if visual_df.empty:
    visual_df = pd.DataFrame(columns=["usar", "block", "categories", "sexes"])

edited_visual = st.data_editor(
    visual_df,
    use_container_width=True,
    num_rows="dynamic",
    key="visual_blocks_editor",
    hide_index=True,
    column_config={
        "usar": st.column_config.CheckboxColumn("Generar", default=True),
        "block": st.column_config.TextColumn("Nombre de la clasificación"),
        "categories": st.column_config.TextColumn("Categorías"),
        "sexes": st.column_config.TextColumn("Sexos"),
    },
)

with st.expander("Modo avanzado: pegar clasificaciones por texto"):
    st.write("Formato: Nombre;categorías;sexos. Usa * para todas las categorías o todos los sexos.")
    example_text = (
        "# Ejemplos\n"
        "General Infantil y Cadete;infantil,cadete;femenina,masculina,mixta\n"
        "General Benjamín y Alevín;benjamin,alevin;femenina,masculina,mixta\n"
        "General Femenina;*;femenina\n"
    )
    custom_text = st.text_area("Bloques avanzados", value="", placeholder=example_text, height=120)

if not edited_visual.empty and "usar" in edited_visual.columns:
    blocks_visual = edited_visual[edited_visual["usar"].fillna(True)].copy()
    blocks_visual = blocks_visual[["block", "categories", "sexes"]]
else:
    blocks_visual = pd.DataFrame(columns=["block", "categories", "sexes"])

blocks_custom = parse_blocks_text(custom_text) if custom_text.strip() else pd.DataFrame(columns=["block", "categories", "sexes"])
blocks = pd.concat([blocks_visual, blocks_custom], ignore_index=True)
blocks = blocks.dropna(subset=["block", "categories", "sexes"])
blocks = blocks[blocks["block"].astype(str).str.strip().ne("")]
blocks = blocks.drop_duplicates(subset=["block", "categories", "sexes"]).reset_index(drop=True)

if blocks.empty:
    st.warning("No hay clasificaciones seleccionadas. Añade al menos una.")
    st.stop()

st.info(f"Se generarán {len(blocks)} clasificación(es).")

classifications = calculate_classifications(scored, blocks)
quality = make_quality_report(norm, scored, blocks)

st.markdown("## Vista previa de resultados")
if classifications.empty:
    st.warning("No hay resultados para las clasificaciones seleccionadas. Revisa las categorías y sexos elegidos.")
else:
    st.dataframe(classifications.head(300), use_container_width=True, hide_index=True)

csv_rfess = classifications.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
auditoria_csv = scored.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
quality_csv = quality.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
blocks_csv = blocks.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
overrides_csv = results_overrides.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")

with tempfile.TemporaryDirectory() as tmp:
    pdf_path = str(Path(tmp) / "clasificaciones.pdf")
    build_pdf(
        classifications,
        pdf_path,
        title="Clasificaciones RFESS",
        subtitle="Generado desde LiveHeats · Clasificaciones finales de la categoría (CSV)",
        logo_path=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    )
    pdf_bytes = Path(pdf_path).read_bytes()

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("clasificaciones_formato_rfess.csv", csv_rfess)
    z.writestr("clasificaciones_publicacion.pdf", pdf_bytes)
    z.writestr("auditoria_puntuacion.csv", auditoria_csv)
    z.writestr("control_calidad.csv", quality_csv)
    z.writestr("bloques_clasificacion.csv", blocks_csv)
    z.writestr("overrides_detalle_resultados.csv", overrides_csv)

st.markdown("## Descargas")
d1, d2, d3, d4 = st.columns(4)
d1.download_button("Descargar CSV RFESS", csv_rfess, "clasificaciones_formato_rfess.csv", "text/csv", use_container_width=True)
d2.download_button("Descargar PDF publicable", pdf_bytes, "clasificaciones_publicacion.pdf", "application/pdf", use_container_width=True)
d3.download_button("Descargar auditoría", auditoria_csv, "auditoria_puntuacion.csv", "text/csv", use_container_width=True)
d4.download_button("Descargar ZIP completo", zip_buffer.getvalue(), "rfess_resultados.zip", "application/zip", use_container_width=True)

st.markdown("## Control de calidad")
st.dataframe(quality, use_container_width=True, hide_index=True)
