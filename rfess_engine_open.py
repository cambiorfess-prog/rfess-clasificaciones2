from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional

import pandas as pd

DEFAULT_POINTS = {1:20, 2:18, 3:16, 4:14, 5:13, 6:12, 7:11, 8:10, 9:8, 10:7, 11:6, 12:5, 13:4, 14:3, 15:2, 16:1}
CATEGORY_ORDER = ["benjamin", "alevin", "infantil", "cadete", "juvenil", "junior", "absoluto", "master"]
SEX_ORDER = ["femenina", "masculina", "mixta"]

TEAM_KEYWORDS = [
    "relevo", "relay", "triada", "triada", "rescate con tabla", "board rescue",
    "salvamento con tubo", "rescue tube rescue", "ocean relay", "sprint relay",
]


def strip_accents(value: str) -> str:
    value = "" if value is None else str(value)
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def norm_text(value: str) -> str:
    value = strip_accents(value).lower()
    value = value.replace("'", " ").replace("’", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_liveheats_csv(file_or_path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "utf-16", "latin1"]
    last = None
    for enc in encodings:
        try:
            if hasattr(file_or_path, "read"):
                file_or_path.seek(0)
            return pd.read_csv(file_or_path, encoding=enc)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"No se pudo leer el CSV. Ultimo error: {last}")


def load_aliases(file_or_path=None) -> Dict[str, str]:
    if file_or_path is None:
        return {}
    try:
        df = read_liveheats_csv(file_or_path)
    except Exception:
        return {}
    if df.empty:
        return {}
    cols = {norm_text(c): c for c in df.columns}
    a_col = cols.get("club liveheats") or cols.get("liveheats") or cols.get("origen") or list(df.columns)[0]
    b_col = cols.get("club rfess") or cols.get("rfess") or cols.get("destino") or (list(df.columns)[1] if len(df.columns) > 1 else a_col)
    aliases = {}
    for _, r in df.iterrows():
        a = str(r.get(a_col, "")).strip()
        b = str(r.get(b_col, "")).strip()
        if a and b and a.lower() != "nan" and b.lower() != "nan":
            aliases[norm_text(a)] = b
    return aliases


def detect_category(division: str) -> str:
    d = norm_text(division)
    if "benjamin" in d or "benjam" in d:
        return "benjamin"
    if "alevin" in d:
        return "alevin"
    if "infantil" in d:
        return "infantil"
    if "cadete" in d:
        return "cadete"
    if "juvenil" in d:
        return "juvenil"
    if "junior" in d or "júnior" in str(division).lower():
        return "junior"
    if "absolut" in d or "open" in d:
        return "absoluto"
    if "master" in d or "máster" in str(division).lower():
        return "master"
    return "sin_categoria"


def detect_sex(division: str) -> str:
    d = norm_text(division)
    # Primero femenino: woman contiene "man", por eso tiene prioridad.
    if "mixto" in d or "mixta" in d or "mixed" in d:
        return "mixta"
    if (
        "femenino" in d or "femenina" in d or
        re.search(r"\bwomen\b", d) or re.search(r"\bwoman\b", d) or
        "oceanwoman" in d or "female" in d
    ):
        return "femenina"
    if (
        "masculino" in d or "masculina" in d or
        re.search(r"\bmen\b", d) or re.search(r"\bman\b", d) or
        "oceanman" in d or "male" in d
    ):
        return "masculina"
    return "sin_sexo"


def detect_is_team(division: str, division_team_value=None) -> bool:
    d = norm_text(division)
    if division_team_value is not None and str(division_team_value).strip() and str(division_team_value).lower() != "nan":
        return True
    return any(k in d for k in TEAM_KEYWORDS)


def apply_club_alias(club: str, aliases: Dict[str, str]) -> str:
    club = "" if club is None else str(club).strip()
    return aliases.get(norm_text(club), club)


def normalize_liveheats(df: pd.DataFrame, aliases: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    aliases = aliases or {}
    cols = {norm_text(c): c for c in df.columns}
    division_col = cols.get("division") or cols.get("event") or cols.get("prueba")
    athlete_col = cols.get("athlete") or cols.get("competitor") or cols.get("deportista") or cols.get("socorrista")
    division_team_col = cols.get("division team") or cols.get("division_team") or cols.get("team")
    event_team_col = cols.get("event team") or cols.get("event_team") or cols.get("club team") or cols.get("club")
    bib_col = cols.get("bib") or cols.get("dorsal")
    place_col = cols.get("place") or cols.get("posicion") or cols.get("posicion") or cols.get("pos")

    points_col = None
    for k, v in cols.items():
        # LiveHeats suele usar "Club pointscore points".
        if "club" in k and "pointscore" in k and "point" in k:
            points_col = v
            break
    if points_col is None:
        for k, v in cols.items():
            if "point" in k and ("score" in k or "club" in k):
                points_col = v
                break

    if not division_col or not place_col:
        raise ValueError("No encuentro columnas imprescindibles. Necesito al menos Division y Place.")

    out = pd.DataFrame()
    out["division"] = df[division_col].astype(str)
    out["athlete"] = df[athlete_col].astype(str) if athlete_col else ""
    out["division_team"] = df[division_team_col] if division_team_col else pd.NA
    out["event_team"] = df[event_team_col] if event_team_col else out["division_team"]
    out["bib"] = df[bib_col] if bib_col else pd.NA
    out["place"] = pd.to_numeric(df[place_col], errors="coerce")
    out["liveheats_points"] = pd.to_numeric(df[points_col], errors="coerce") if points_col else pd.NA
    out["has_liveheats_points_col"] = bool(points_col)
    out["row_order"] = range(1, len(out)+1)
    out["category"] = out["division"].apply(detect_category)
    out["sex"] = out["division"].apply(detect_sex)
    out["is_team_event"] = [detect_is_team(d, t) for d, t in zip(out["division"], out["division_team"])]
    out["club_raw"] = out["event_team"].fillna(out["division_team"]).fillna("").astype(str).str.strip()
    out["club"] = out["club_raw"].apply(lambda x: apply_club_alias(x, aliases))
    out.loc[out["club"].str.lower().isin(["nan", "none"]), "club"] = ""
    out["entity"] = out["athlete"].fillna("").astype(str).str.strip()
    return out


def scoring_points(position: int, points_table: Dict[int, int]) -> int:
    try:
        p = int(position)
    except Exception:
        return 0
    return int(points_table.get(p, 0))


def _points_from_table(place, ordinal: int, points_table: Dict[int, int], top_limit: int, individual_limit_mode: str) -> int:
    if pd.isna(place):
        return 0
    pos_for_points = ordinal if individual_limit_mode == "ordinal" else int(place)
    return scoring_points(pos_for_points, points_table) if pos_for_points <= top_limit else 0


def _choose_base_points(row, ordinal: int, is_team: bool, points_table: Dict[int, int], top_limit: int,
                        individual_limit_mode: str, score_source: str) -> tuple[int, str]:
    """Return base points and explanation before the RFESS max-3 club rule."""
    live = row.get("liveheats_points", pd.NA)
    has_live = not pd.isna(live)
    if score_source in ["auto", "liveheats"] and has_live:
        # LiveHeats supplies the official pointscore, but in RFESS individual events
        # only the first N real rows score. This prevents extra 1-point ties at
        # Place 16 from counting as row 17/18 in individual events. Team events
        # keep their LiveHeats pointscore, including official ties.
        if not is_team:
            place = row.get("place", pd.NA)
            if individual_limit_mode == "ordinal" and ordinal > top_limit:
                return 0, "LIVEHEATS_POINT_SCORE_FUERA_TOP_ORDINAL"
            if individual_limit_mode == "place" and (pd.isna(place) or int(place) > top_limit):
                return 0, "LIVEHEATS_POINT_SCORE_FUERA_TOP_PLACE"
        return int(live), "LIVEHEATS_POINT_SCORE"
    if score_source == "liveheats" and not has_live:
        return 0, "SIN_POINT_SCORE_LIVEHEATS"
    if is_team:
        place = row.get("place", pd.NA)
        if pd.isna(place) or int(place) > top_limit:
            return 0, "FUERA_TOP"
        return scoring_points(int(place), points_table), "TABLA_PUNTOS_POR_PLACE"
    return _points_from_table(row.get("place", pd.NA), ordinal, points_table, top_limit, individual_limit_mode), "TABLA_PUNTOS"


def build_scored_rows(norm: pd.DataFrame, points_table: Optional[Dict[int, int]] = None,
                      max_per_club_individual: int = 3, top_limit: int = 16,
                      individual_limit_mode: str = "ordinal", score_source: str = "auto") -> pd.DataFrame:
    """Build RFESS points by result row.

    score_source:
    - auto: use LiveHeats Club pointscore points when present; fallback to the points table.
    - liveheats: use only LiveHeats pointscore points.
    - table: ignore LiveHeats pointscore points and calculate from place/ordinal.
    """
    points_table = points_table or DEFAULT_POINTS
    score_source = score_source if score_source in ["auto", "liveheats", "table"] else "auto"
    scored_parts = []

    for division, g in norm.groupby("division", sort=False):
        g = g.copy().sort_values(["place", "row_order"], na_position="last")
        is_team = bool(g["is_team_event"].fillna(False).any())

        if is_team:
            # Some LiveHeats leaderboards include a stray placeholder row in team events:
            # Athlete == club, Division_team empty, and a pointscore. If the same division
            # otherwise has real Division_team rows, that placeholder must not score.
            if g["division_team"].notna().any():
                placeholder = (
                    g["division_team"].isna()
                    & (g["entity"].map(norm_text) == g["club"].map(norm_text))
                )
                g = g.loc[~placeholder].copy()
            # Collapse athlete rows into one team result per club/place/division_team.
            team_cols = ["division", "category", "sex", "club", "place"]
            rows = []
            for keys, tg in g.groupby(team_cols, sort=False, dropna=False):
                div, cat, sex, club, place = keys
                tg2 = tg.copy().sort_values(["place", "row_order"], na_position="last")
                # The team pointscore normally appears only on the first athlete row of that team.
                live_values = pd.to_numeric(tg2["liveheats_points"], errors="coerce").dropna()
                first = tg2.iloc[0].copy()
                if len(live_values):
                    first["liveheats_points"] = live_values.iloc[0]
                else:
                    first["liveheats_points"] = pd.NA
                base, source_reason = _choose_base_points(first, 1, True, points_table, top_limit, individual_limit_mode, score_source)
                if base == 0 and pd.isna(place):
                    reason = "EQUIPO_SIN_POSICION"
                elif base == 0:
                    reason = "EQUIPO_SIN_PUNTOS"
                else:
                    reason = "EQUIPO_RELEVO_CLUB"
                rows.append({
                    "division": div, "category": cat, "sex": sex, "club": club, "place": place,
                    "entity": club, "bib": first.get("bib", pd.NA), "is_team_event": True,
                    "rfess_points": base, "base_points": base, "liveheats_points": first.get("liveheats_points", pd.NA),
                    "score_source": source_reason, "adjustment_reason": reason, "row_count": len(tg2)
                })
            scored_parts.append(pd.DataFrame(rows))
        else:
            club_counts = {}
            rows = []
            ordinal = 0
            for _, r in g.iterrows():
                ordinal += 1
                base, source_reason = _choose_base_points(r, ordinal, False, points_table, top_limit, individual_limit_mode, score_source)
                reason = "OK" if base > 0 else "SIN_PUNTOS"
                club = r["club"]
                if base > 0:
                    club_counts[club] = club_counts.get(club, 0) + 1
                    if club_counts[club] > max_per_club_individual:
                        pts = 0
                        reason = "CUARTO_DEPORTISTA_CLUB_PRUEBA_INDIVIDUAL"
                    else:
                        pts = base
                else:
                    pts = 0
                    if pd.isna(r.get("place", pd.NA)):
                        reason = "SIN_POSICION"
                    elif source_reason == "SIN_POINT_SCORE_LIVEHEATS":
                        reason = "SIN_POINT_SCORE_LIVEHEATS"
                    else:
                        reason = "FUERA_ZONA_PUNTOS"
                rows.append({
                    "division": r["division"], "category": r["category"], "sex": r["sex"], "club": club,
                    "place": r["place"], "entity": r["entity"], "bib": r["bib"], "is_team_event": False,
                    "rfess_points": pts, "base_points": base, "liveheats_points": r.get("liveheats_points", pd.NA),
                    "score_source": source_reason, "adjustment_reason": reason, "row_count": 1
                })
            scored_parts.append(pd.DataFrame(rows))
    return pd.concat(scored_parts, ignore_index=True) if scored_parts else pd.DataFrame()


def make_default_blocks(categories: List[str], include_sex_blocks: bool = True, include_category_blocks: bool = True,
                        include_category_sex_blocks: bool = True, include_general: bool = True) -> pd.DataFrame:
    cats = [c for c in CATEGORY_ORDER if c in set(categories)] + [c for c in categories if c not in CATEGORY_ORDER]
    rows = []
    if include_category_sex_blocks:
        for c in cats:
            for s in SEX_ORDER:
                rows.append({"block": f"{c} {s}", "categories": c, "sexes": s})
    if include_category_blocks:
        for c in cats:
            rows.append({"block": f"{c} conjunta", "categories": c, "sexes": "femenina,masculina,mixta"})
    if include_sex_blocks:
        for s in SEX_ORDER:
            rows.append({"block": s, "categories": ",".join(cats), "sexes": s})
    if include_general:
        rows.append({"block": "general", "categories": ",".join(cats), "sexes": "femenina,masculina,mixta"})
    return pd.DataFrame(rows)


def parse_blocks_text(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 3:
            continue
        rows.append({"block": parts[0], "categories": parts[1], "sexes": parts[2]})
    return pd.DataFrame(rows)


def _split_values(value: str) -> List[str]:
    if value is None:
        return []
    value = str(value).strip()
    if value in ["*", "todos", "todas"]:
        return ["*"]
    return [norm_text(x) for x in re.split(r"[,|]", value) if x.strip()]


def calculate_classifications(scored: pd.DataFrame, blocks: pd.DataFrame) -> pd.DataFrame:
    results = []
    if scored.empty:
        return pd.DataFrame(columns=["block", "rank", "club", "score"])
    all_categories = set(scored["category"].dropna().map(norm_text).unique())
    all_sexes = set(scored["sex"].dropna().map(norm_text).unique())
    for _, b in blocks.iterrows():
        block = str(b["block"]).strip()
        cats = _split_values(b["categories"])
        sexes = _split_values(b["sexes"])
        cats_set = all_categories if cats == ["*"] else set(cats)
        sexes_set = all_sexes if sexes == ["*"] else set(sexes)
        sub = scored[scored["category"].map(norm_text).isin(cats_set) & scored["sex"].map(norm_text).isin(sexes_set)]
        if sub.empty:
            continue
        agg = sub.groupby("club", dropna=False)["rfess_points"].sum().reset_index()
        agg = agg[agg["club"].astype(str).str.len() > 0]
        agg = agg.sort_values(["rfess_points", "club"], ascending=[False, True]).reset_index(drop=True)
        agg.insert(0, "rank", range(1, len(agg)+1))
        agg.insert(0, "block", block)
        results.append(agg.rename(columns={"rfess_points": "score"}))
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["block", "rank", "club", "score"])


def make_quality_report(norm: pd.DataFrame, scored: pd.DataFrame, blocks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    def add(item, value, detail=""):
        rows.append({"control": item, "value": value, "detail": detail})
    add("filas_leidas", len(norm))
    add("pruebas_detectadas", norm["division"].nunique())
    add("clubes_detectados", norm["club"].nunique())
    add("categorias_detectadas", ", ".join(sorted(norm["category"].dropna().unique())))
    add("sexos_detectados", ", ".join(sorted(norm["sex"].dropna().unique())))
    add("pruebas_equipo_relevo", int(norm.groupby("division")["is_team_event"].any().sum()))
    add("pruebas_individuales", int((~norm.groupby("division")["is_team_event"].any()).sum()))
    add("filas_con_liveheats_pointscore", int(pd.to_numeric(norm["liveheats_points"], errors="coerce").notna().sum()))
    add("ajustes_4o_deportista", int((scored["adjustment_reason"] == "CUARTO_DEPORTISTA_CLUB_PRUEBA_INDIVIDUAL").sum()) if not scored.empty else 0)
    add("clasificaciones_definidas", len(blocks))
    unknown_cats = sorted([c for c in norm["category"].unique() if str(c).startswith("sin_")])
    unknown_sex = sorted([s for s in norm["sex"].unique() if str(s).startswith("sin_")])
    add("categorias_sin_detectar", len(unknown_cats), ", ".join(unknown_cats))
    add("sexos_sin_detectar", len(unknown_sex), ", ".join(unknown_sex))
    if unknown_sex:
        divs = sorted(norm.loc[norm["sex"].isin(unknown_sex), "division"].unique())[:20]
        add("primeras_pruebas_sin_sexo", len(divs), " | ".join(divs))
    return pd.DataFrame(rows)

NO_SCORE_STATUS_KEYWORDS = ["dns", "dnf", "dsq", "dq", "baja", "descal", "no presentado", "no present", "no finaliza"]


def _find_column_by_candidates(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {norm_text(c): c for c in df.columns}
    for c in candidates:
        if c in cols:
            return cols[c]
    return None


def build_no_score_overrides_from_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """Build no-score overrides from LiveHeats detailed results.

    This is optional but important: the leaderboard can sometimes keep a pointscore
    for a team that is DNS in the final. The detailed results CSV contains the final
    modifier (for example DNS), so we can zero those rows.
    """
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=["division", "bib", "result_status", "override_reason"])

    division_col = _find_column_by_candidates(results_df, ["division", "event", "prueba"])
    bib_col = _find_column_by_candidates(results_df, ["bib", "dorsal"])
    round_col = _find_column_by_candidates(results_df, ["round", "ronda"])
    total_col = _find_column_by_candidates(results_df, ["total", "score", "puntuacion"])
    modifier_cols = [c for c in results_df.columns if "modifier" in norm_text(c) or "modificador" in norm_text(c)]

    if not division_col or not bib_col:
        return pd.DataFrame(columns=["division", "bib", "result_status", "override_reason"])

    df = results_df.copy()
    df["division"] = df[division_col].astype(str)
    df["bib"] = pd.to_numeric(df[bib_col], errors="coerce")
    df = df[df["bib"].notna()]
    if round_col:
        df["round_norm"] = df[round_col].apply(norm_text)
        # Prefer final rows when present; otherwise inspect all rows.
        final_mask = df["round_norm"].str.contains("final", na=False)
        if final_mask.any():
            df = df[final_mask].copy()

    if total_col:
        df["total_num"] = pd.to_numeric(df[total_col], errors="coerce")
    else:
        df["total_num"] = pd.NA

    if modifier_cols:
        df["result_status"] = df[modifier_cols].astype(str).agg(" ".join, axis=1).apply(lambda x: x.replace("nan", "").strip())
    else:
        df["result_status"] = ""
    df["status_norm"] = df["result_status"].apply(norm_text)
    df["is_no_score_status"] = df["status_norm"].apply(lambda s: any(k in s for k in NO_SCORE_STATUS_KEYWORDS))
    df["is_zero_total_with_status"] = df["is_no_score_status"] & (pd.to_numeric(df["total_num"], errors="coerce").fillna(0) <= 0)
    bad = df[df["is_zero_total_with_status"]].copy()
    if bad.empty:
        return pd.DataFrame(columns=["division", "bib", "result_status", "override_reason"])
    out = bad.groupby(["division", "bib"], dropna=False).agg(result_status=("result_status", lambda x: "; ".join(sorted(set([str(v).strip() for v in x if str(v).strip()]))))).reset_index()
    out["override_reason"] = "DETALLE_RESULTADOS_SIN_PUNTOS"
    return out


def apply_no_score_overrides(scored: pd.DataFrame, results_df: Optional[pd.DataFrame] = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    overrides = build_no_score_overrides_from_results(results_df) if results_df is not None else pd.DataFrame(columns=["division", "bib", "result_status", "override_reason"])
    if scored.empty or overrides.empty:
        return scored, overrides
    out = scored.copy()
    out["bib_match"] = pd.to_numeric(out.get("bib", pd.NA), errors="coerce")
    overrides = overrides.copy()
    overrides["bib_match"] = pd.to_numeric(overrides["bib"], errors="coerce")
    key = overrides[["division", "bib_match", "result_status", "override_reason"]].drop_duplicates()
    out = out.merge(key, on=["division", "bib_match"], how="left")
    mask = out["override_reason"].notna()
    out.loc[mask, "rfess_points"] = 0
    out.loc[mask, "adjustment_reason"] = out.loc[mask, "adjustment_reason"].astype(str) + "+" + out.loc[mask, "override_reason"].astype(str)
    out.loc[mask, "score_source"] = out.loc[mask, "score_source"].astype(str) + "+DETALLE_RESULTADOS"
    out = out.drop(columns=["bib_match"])
    return out, overrides
