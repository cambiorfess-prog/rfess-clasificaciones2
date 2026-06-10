import argparse
from pathlib import Path
import pandas as pd
from rfess_engine_open import read_liveheats_csv, load_aliases, normalize_liveheats, build_scored_rows, make_default_blocks, parse_blocks_text, calculate_classifications, make_quality_report, DEFAULT_POINTS, apply_no_score_overrides
from rfess_pdf_open import build_pdf

p = argparse.ArgumentParser()
p.add_argument("--leaderboard", required=True)
p.add_argument("--out", required=True)
p.add_argument("--aliases")
p.add_argument("--results")
p.add_argument("--blocks")
p.add_argument("--mode", default="ordinal", choices=["ordinal", "place"])
p.add_argument("--score-source", default="auto", choices=["auto", "liveheats", "table"])
args = p.parse_args()
out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
raw = read_liveheats_csv(args.leaderboard)
aliases = load_aliases(args.aliases) if args.aliases else {}
norm = normalize_liveheats(raw, aliases)
scored = build_scored_rows(norm, DEFAULT_POINTS, 3, 16, args.mode, args.score_source)
if args.results:
    detailed_results = read_liveheats_csv(args.results)
    scored, overrides = apply_no_score_overrides(scored, detailed_results)
    overrides.to_csv(out/"overrides_detalle_resultados.csv", sep=";", index=False, encoding="utf-8-sig")
categories = sorted([c for c in norm["category"].dropna().unique() if c != "sin_categoria"])
blocks = make_default_blocks(categories)
if args.blocks:
    blocks = parse_blocks_text(Path(args.blocks).read_text(encoding="utf-8"))
clas = calculate_classifications(scored, blocks)
quality = make_quality_report(norm, scored, blocks)
clas.to_csv(out/"clasificaciones_formato_rfess.csv", sep=";", index=False, encoding="utf-8-sig")
scored.to_csv(out/"auditoria_puntuacion.csv", sep=";", index=False, encoding="utf-8-sig")
quality.to_csv(out/"control_calidad.csv", sep=";", index=False, encoding="utf-8-sig")
build_pdf(clas, str(out/"clasificaciones_publicacion.pdf"), "Clasificaciones RFESS", "Generado desde CSV LiveHeats")
print("OK", out)
