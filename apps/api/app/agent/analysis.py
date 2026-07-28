"""Deterministic analysis battery — the cost heart of report generation.

Instead of an LLM-driven ReAct loop that decides which statistics to compute (a
model round-trip per decision), we compute a broad, varied battery of statistics
in pure pandas *before spending a single token*: distributions, correlations,
single- and two-way segment comparisons, cohort/quartile profiling, categorical
composition and cross-tabs, missingness, outliers, and time trends. Each notable
result becomes a ``Finding`` (an exact, pre-computed fact) plus, where useful, a
ready-to-render chart — and we deliberately spread the work across many chart
types (bar, grouped/stacked bar, scatter, line/multi-line, pie/donut, histogram,
radar) so reports stay visually varied.

The LLM's only remaining job is to *select and narrate* these findings — it
never calculates. Report numbers are therefore Python-exact by construction and
charts are always valid.

Everything here is blocking pandas work; call ``run_analysis`` via
``asyncio.to_thread`` from the async endpoint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app.agent.context import DatasetContext
from app.agent.tools.chart_spec import build_chart_spec
from app.core.config import settings
from app.core.logging import logger
from app.services.data_access import QueryError, load_dataframe

_SCATTER_SAMPLE = 2000
_HIST_SAMPLE = 20000
_MIN_SEGMENTS = 2
_MAX_SEGMENTS = 12
# A goal-named dimension (e.g. "by Country", 43 distinct) is kept up to this many
# categories — we show the TOP-N groups rather than discarding the column.
_MAX_FOCUS_SEGMENTS = 60
# When a dimension has many groups, chart/describe only the top N by the measure.
_TOP_GROUPS = 15
# A column with almost as many distinct values as rows is an identifier, not a
# measure or a segment — never analyze it as one.
_ID_RATIO = 0.9
# Row-scope guardrails: a goal-derived sub-population is only honoured if it keeps
# at least this many rows AND this fraction of the data — otherwise the analysis
# fails open to the full dataset rather than reporting on a sliver.
_MIN_SCOPE_ROWS = 5
_MIN_SCOPE_FRAC = 0.10
# Above this, a correlation is almost certainly two names for the same underlying
# metric (a derived/duplicate column). Reporting r≈1.00 as an "insight" is noise.
_REDUNDANT_R = 0.985
# Count-like columns: SUM reads better than a fractional MEAN across a segment.
_COUNT_KW = (
    "award", "wins", "win", "goals", "goal", "assists", "cards", "saves", "tackles",
    "fouls", "count", "num", "total", "apps", "appearances", "matches", "titles",
    "trophies", "penalt", "clean_sheet", "offsides", "recoveries", "punches",
    "conceded", "interceptions", "shots", "passes",
)
# Columns that label a row as a real-world entity worth naming.
_ENTITY_KW = (
    "name", "player", "team", "club", "customer", "company", "product", "title",
    "user", "email", "country", "city", "brand", "account", "employee", "store",
)
# Measures that express "how good" a row is — used to rank a leaderboard, tiered
# so a genuine quality metric (score/rating) beats a raw count (total_*).
_RANK_STRONG = ("score", "rating", "index", "performance", "clutch", "efficiency", "impact", "quality")
_RANK_BIZ = ("value", "revenue", "sales", "profit", "margin", "ltv")


@dataclass
class Finding:
    """One exact, pre-computed fact about the dataset."""

    id: str
    kind: str  # overview|quality|distribution|correlation|segment|cohort|category|crosstab|trend
    text: str  # a single self-contained sentence WITH the numbers
    importance: float  # for ranking; higher = surface first
    columns: list[str] = field(default_factory=list)
    chart_id: str | None = None


@dataclass
class AnalysisResult:
    findings: list[Finding]
    charts: dict[str, dict]  # chart_id -> {id, kind, title, spec, label}
    # Set when the battery restricted itself to a goal-relevant sub-population
    # (e.g. "defenders and goalkeepers" for a goals-conceded goal); the report
    # opens by declaring it. None means the whole dataset was analyzed.
    scope_note: str | None = None

    def digest_text(self) -> str:
        lines = []
        for f in self.findings:
            chart = f" [chart: {f.chart_id}]" if f.chart_id else ""
            lines.append(f"[{f.id}] ({f.kind}) {f.text}{chart}")
        return "\n".join(lines)

    def chart_index_text(self) -> str:
        return "\n".join(f"[{cid}] {c['label']}" for cid, c in self.charts.items()) or "(none)"

    def findings_by_id(self, ids: list[str]) -> list[Finding]:
        by_id = {f.id: f for f in self.findings}
        return [by_id[i] for i in ids if i in by_id]

    def top_chart_id(self) -> str | None:
        for f in self.findings:
            if f.chart_id:
                return f.chart_id
        return None


def run_analysis(ctx: DatasetContext, goal: str = "", spec: dict | None = None) -> AnalysisResult:
    """Compute the full battery for one dataset, STEERED toward the report goal.

    ``spec`` (from a cheap upstream LLM call, see report._infer_spec) carries the
    SEMANTIC understanding pandas can't infer: which column is the readable entity
    NAME (vs an id code), which id to collapse duplicate rows on, whether the data
    is multi-row-per-entity (so per-entity totals must not be summed across rows),
    which groupings are meaningful, and which columns to avoid. Absent a spec, we
    fall back to heuristics.

    Never raises: a failed probe is logged and skipped so a report always has
    something to narrate.
    """
    df = load_dataframe(ctx.parquet_path)
    b = _Builder(ctx, df, goal, spec)
    b.overview()
    b.missingness()
    b.entities()          # name the actual top rows (players/customers/…)
    b.performance_gap()   # goal-driven actual-vs-expected; ranks highest when present
    b.measures_across_dims()  # goal-driven 'A vs B by <dimension>' (top-N groups)
    b.correlations()
    b.segments()
    b.two_way_segments()
    b.cohorts()
    b.crosstabs()
    b.categories()
    b.distributions()
    b.trends()
    b.outliers()
    return b.finalize()


def _focus_columns(goal: str, columns: list[dict]) -> set[str]:
    """Columns the goal actually talks about — matched by whole-word token overlap
    so 'expected_goals_xg' matches "expected_goals_xg", 'position' matches
    "positions", and 'goals_scored' matches "actual goals scored"."""
    g = (goal or "").lower()
    if not g:
        return set()
    focus: set[str] = set()
    for c in columns:
        name = str(c["name"])
        low = name.lower()
        if low in g:
            focus.add(name)
            continue
        tokens = [t for t in re.split(r"[^a-z0-9]+", low) if len(t) >= 3]
        if any(re.search(rf"\b{re.escape(t)}\b", g) for t in tokens):
            focus.add(name)
    return focus


class _Builder:
    def __init__(
        self, ctx: DatasetContext, df: pd.DataFrame, goal: str = "", spec: dict | None = None
    ) -> None:
        self.ctx = ctx
        self.goal = goal
        self.focus = _focus_columns(goal, ctx.columns)
        spec = spec or {}
        self._findings: list[Finding] = []
        self._charts: dict[str, dict] = {}
        self._fc = 0
        self._cc = 0

        cols = set(df.columns)
        # Semantic hints from the spec (validated against real columns).
        self.entity = spec.get("entity_column") if spec.get("entity_column") in cols else None
        self.dedupe = spec.get("dedupe_column") if spec.get("dedupe_column") in cols else None

        # Collapse multi-row-per-entity tables (e.g. one row per player PER MATCH)
        # to ONE row per entity, so denormalized per-entity totals (awards, ratings)
        # are never summed across duplicate rows — the "30 awards in the final" bug.
        key = self.dedupe or self.entity
        if spec.get("entity_grain") and key and df[key].nunique(dropna=False) < len(df):
            df = self._collapse(df, key)
        # Restrict to the goal-relevant sub-population (e.g. defensive roles for a
        # goals-conceded goal) so comparisons aren't polluted by irrelevant groups.
        # Fails open to the full frame if the scope is invalid or too aggressive.
        df, self.scope_note = self._apply_scope(df, spec.get("scope"))
        self.df = df
        self.n = len(df)

        # Columns to never treat as a measure or grouping: spec's avoid list, plus
        # the id we deduped on.
        self.avoid = {c for c in (spec.get("avoid_columns") or []) if c in cols}
        if self.dedupe:
            self.avoid.add(self.dedupe)

        def not_id(name: str) -> bool:
            if not pd.api.types.is_integer_dtype(self.df[name]):
                return True  # floats/continuous are real measures, never ids
            nun = self.df[name].nunique(dropna=True)
            return not (self.n and nun / self.n > _ID_RATIO)

        self.numeric = [
            c["name"] for c in ctx.columns
            if _is_numeric(c) and c["name"] in self.df.columns and c["name"] not in self.avoid
            and pd.api.types.is_numeric_dtype(self.df[c["name"]]) and not_id(c["name"])
        ]
        self.categorical = [
            c["name"] for c in ctx.columns
            if c.get("dtype") in ("categorical", "boolean") and c["name"] in self.df.columns
            and c["name"] not in self.avoid and c["name"] != self.entity
        ]
        self.datetime = [
            c["name"] for c in ctx.columns
            if c.get("dtype") == "datetime" and c["name"] in self.df.columns
        ]
        # Ranking preference + segment whitelist from the spec.
        self.rank_pref = [m for m in (spec.get("rank_measures") or []) if m in self.numeric]
        seg_whitelist = [c for c in (spec.get("segment_dimensions") or []) if c in cols]

        # Order measures goal-FIRST, then by how SPECIFICALLY the name matches the
        # goal (so "Solo/Lead Streams" outrank "Feature Streams"), then by spread.
        self.measures = sorted(
            self.numeric,
            key=lambda m: (m in self.focus, self._goal_match(m), self._cov(m)),
            reverse=True,
        )
        # A dimension the goal/spec explicitly calls for (e.g. "by Country", 43
        # distinct) MUST NOT be dropped for having many categories — we just show
        # the top-N groups. Only unrequested dimensions get the tight cap.
        priority = set(self.focus) | set(seg_whitelist)
        seg_source = seg_whitelist if seg_whitelist else self.categorical

        def _seg_ok(c: str) -> bool:
            if c not in self.df.columns or c in self.avoid or c == self.entity:
                return False
            nun = self.df[c].nunique(dropna=True)
            cap = _MAX_FOCUS_SEGMENTS if c in priority else _MAX_SEGMENTS
            return _MIN_SEGMENTS <= nun <= cap

        self.segment_cols = self._focus_first([c for c in seg_source if _seg_ok(c)])

    def _apply_scope(
        self, df: pd.DataFrame, scope: dict | None
    ) -> tuple[pd.DataFrame, str | None]:
        """Filter to the sub-population the goal is really about.

        ``scope`` is ``{"column", "include": [values], "reason"}`` from the semantic
        spec. Matching is case/whitespace-insensitive against the real values. The
        filter is honoured ONLY when it keeps ≥ _MIN_SCOPE_ROWS and ≥ _MIN_SCOPE_FRAC
        of the rows and actually removes some — otherwise we analyze everything and
        return no note (a wrong scope must never yield an empty or misleading report).
        Returns ``(frame, scope_note)``.
        """
        if not isinstance(scope, dict):
            return df, None
        col = scope.get("column")
        include = scope.get("include") or []
        if col not in df.columns or not include:
            return df, None

        total = len(df)
        values = df[col].astype(str).str.strip()
        want = {str(v).strip().lower() for v in include}
        mask = values.str.lower().isin(want)
        kept = int(mask.sum())
        if kept == total or kept < max(_MIN_SCOPE_ROWS, int(_MIN_SCOPE_FRAC * total)):
            logger.info(
                "analysis scope on '%s' skipped (kept %d/%d rows)", col, kept, total
            )
            return df, None

        shown = ", ".join(sorted({v for v in values[mask].unique()}))
        reason = str(scope.get("reason", "")).strip().rstrip(".")
        lead = f"This analysis focuses on {reason}" if reason else "This analysis is scoped"
        note = (
            f"{lead}: {kept:,} of {total:,} rows where {col} is {shown}. "
            "All figures below describe that group."
        )
        return df[mask].copy(), note

    def _collapse(self, df: pd.DataFrame, key: str) -> pd.DataFrame:
        """One row per entity: numeric columns averaged, others take the first value."""
        num = df.select_dtypes("number").columns.tolist()
        agg = {c: "mean" for c in num if c != key}
        agg.update({c: "first" for c in df.columns if c not in num and c != key})
        return df.groupby(key, dropna=False).agg(agg).reset_index()

    def _focus_first(self, cols: list[str]) -> list[str]:
        return [c for c in cols if c in self.focus] + [c for c in cols if c not in self.focus]

    # -- registration -------------------------------------------------------- #
    def _add(self, kind, text, importance, columns=None, chart_id=None) -> None:
        self._fc += 1
        self._findings.append(
            Finding(id=f"f{self._fc}", kind=kind, text=text, importance=importance,
                    columns=columns or [], chart_id=chart_id)
        )

    def _chart(self, label, chart_type, rows, x, y=None, **kw) -> str | None:
        if not rows:
            return None
        try:
            spec = build_chart_spec(chart_type, rows, x, y, **kw)
        except Exception as exc:  # noqa: BLE001 — one bad chart must not kill the battery
            logger.debug("skipped candidate chart %r: %s", label, exc)
            return None
        self._cc += 1
        cid = f"c{self._cc}"
        self._charts[cid] = {"id": cid, "kind": "chart", "title": kw.get("title") or label,
                             "spec": spec, "label": label}
        return cid

    def _scatter_sample(self, xcol: str, ycol: str) -> tuple[list[dict], str | None]:
        """Sampled (x, y) rows for a scatter, carrying the entity NAME as a
        per-point label when the dataset has one — so a dot is identifiable
        (which player/team/customer), not just a pair of numbers."""
        label = self.entity if self.entity and self.entity in self.df.columns else None
        cols = [xcol, ycol] + ([label] if label and label not in (xcol, ycol) else [])
        d = self.df[cols].dropna(subset=[xcol, ycol])
        if len(d) > _SCATTER_SAMPLE:
            d = d.sample(_SCATTER_SAMPLE, random_state=0)
        return d.to_dict("records"), label

    def _probe(self, name, fn) -> None:
        try:
            fn()
        except Exception:  # noqa: BLE001 — resilient battery
            logger.debug("analysis probe %s failed", name, exc_info=True)

    def _cov(self, c: str) -> float:
        s = self.df[c].dropna()
        return float(s.std() / (abs(s.mean()) + 1e-9)) if len(s) else 0.0

    def _goal_match(self, col: str) -> int:
        """How specifically a column name matches the goal — distinguishes
        'Solo Streams'/'Lead Streams' (named) from 'Feature Streams' (only shares
        the generic 'streams' token) so the right pair leads."""
        g = (self.goal or "").lower()
        toks = [t for t in re.split(r"[^a-z0-9]+", col.lower()) if len(t) >= 3]
        return sum(1 for t in toks if re.search(rf"\b{re.escape(t)}\b", g))

    def _agg_for(self, col: str) -> str:
        """Pick a meaningful aggregate. A count (awards, cards, goals) reads better
        as a SUM ("210 awards") than a fractional MEAN (0.06). Scores/ratings average."""
        low = col.lower()
        s = self.df[col].dropna()
        if any(k in low for k in _COUNT_KW):
            return "sum"
        if pd.api.types.is_integer_dtype(self.df[col]) and len(s) and s.mean() < 1.5 and s.min() >= 0:
            return "sum"
        return "mean"

    def _entity_column(self) -> str | None:
        """The column that labels each row as a real-world thing (player, customer,
        product…). Prefer a readable NAME; never an id code."""
        if self.entity:  # the spec already told us the readable label
            return self.entity
        best, best_score = None, -1.0
        for c in self.ctx.columns:
            col = c["name"]
            low = col.lower()
            if col not in self.df.columns or col in self.avoid:
                continue
            if str(c.get("dtype", "")) not in ("text", "categorical"):
                continue
            nun = self.df[col].nunique(dropna=True)
            if nun < 5:
                continue
            ratio = nun / self.n if self.n else 0
            has_name = "name" in low
            has_entity = any(k in low for k in _ENTITY_KW)
            is_id = low == "id" or low.endswith("_id") or (low.endswith("id") and not has_name)
            if ratio < 0.2 and not (has_name or has_entity):
                continue
            score = ratio + (3 if has_name else 0) + (2 if has_entity else 0) - (5 if is_id else 0)
            if score > best_score:
                best, best_score = col, score
        return best

    def _rank_measure(self) -> str | None:
        """The measure that best expresses 'how good' a row is. The spec's
        rank_measures win; otherwise a score/rating beats a business value beats a
        raw count, keeping the goal-first order baked into self.measures."""
        if self.rank_pref:
            return self.rank_pref[0]
        fm = [m for m in self.measures if m in self.focus] or self.measures
        if not fm:
            return None

        def tier(m: str) -> int:
            low = m.lower()
            if any(k in low for k in _RANK_STRONG):
                return 2
            if any(k in low for k in _RANK_BIZ):
                return 1
            return 0

        # stable sort by tier desc preserves self.measures order within a tier
        return sorted(fm, key=tier, reverse=True)[0]

    # -- probes -------------------------------------------------------------- #
    _BASELINE_KW = ("expected", "predicted", "projected", "target", "xg", "potential", "est")

    def entities(self) -> None:
        """Name names. Goals like 'profile the top performers' want the actual
        rows identified, not group averages — so rank the entity column by the key
        measure, list the leaders, and contrast them with the field."""
        def _run():
            ent, measure = self._entity_column(), self._rank_measure()
            if not ent or not measure:
                return
            d = self.df[[ent, measure]].dropna()
            if d[ent].nunique() < 5:
                return
            agg = self._agg_for(measure)
            per = d.groupby(ent)[measure].agg(agg).sort_values(ascending=False)
            top = per.head(10)
            rows = [{ent: str(k), measure: round(float(v), 2)} for k, v in top.items()]
            cid = self._chart(f"Top {ent} by {measure}", "bar", rows, x=ent, y=measure,
                              title=f"Top 10 {ent} by {measure}", y_label=measure)
            names = ", ".join(f"{k} ({v:.1f})" for k, v in list(top.items())[:5])
            self._add("entity",
                      f"The standout {ent} by {measure} are {names} — the specific individuals "
                      f"this report is about.",
                      importance=1.05, columns=[ent, measure], chart_id=cid)
            # Contrast the leaders with everyone else, in real numbers.
            leaders = set(top.index)
            mask = self.df[ent].isin(leaders)
            fmeas = [m for m in self.measures if m in self.focus] or self.measures[:4]
            diffs = []
            for m in fmeas[:5]:
                t, r = self.df.loc[mask, m].mean(), self.df.loc[~mask, m].mean()
                if pd.notna(t) and pd.notna(r):
                    diffs.append((m, t, r, abs(t - r) / (abs(r) + 1e-9)))
            if diffs:
                diffs.sort(key=lambda x: x[3], reverse=True)
                m, t, r, _ = diffs[0]
                self._add("entity",
                          f"These top {ent} separate from the field most on '{m}' "
                          f"({t:.2f} vs {r:.2f} for everyone else), marking it as the defining "
                          f"trait of the elite group.",
                          importance=0.9, columns=[ent, m])
        self._probe("entities", _run)

    def performance_gap(self) -> None:
        """Goal-driven: when the goal focuses on two comparable measures (e.g. actual
        goals vs expected_goals_xg), compute the per-row gap and find who over/under-
        performs — overall and by the focus segment. This is usually THE analysis the
        user asked for, so it ranks at the very top."""
        def _run():
            fm = [m for m in self.measures if m in self.focus]
            if len(fm) < 2:
                return
            # Fire ONLY when a real baseline column exists (expected/xg/predicted…);
            # otherwise there is no "actual vs expected" concept and forcing a
            # subtraction produces nonsense (e.g. market_value minus goals).
            def is_base(name):
                toks = re.split(r"[^a-z0-9]+", name.lower())
                return any(k in toks or k in name.lower() for k in self._BASELINE_KW)
            baselines = [m for m in fm if is_base(m)]
            candidates = [m for m in fm if not is_base(m)]
            if not baselines or not candidates:
                return
            expected = baselines[0]
            # Pair it with the counterpart it actually tracks (highest |correlation|)
            # — that's the "actual" of the actual-vs-expected pair, not just the
            # highest-variance focus column.
            corrs = self.df[[expected] + candidates].corr(numeric_only=True)[expected]
            actual = max(candidates, key=lambda c: abs(corrs.get(c, 0)))
            if abs(corrs.get(actual, 0)) < 0.3:
                return  # nothing meaningfully tracks the baseline
            d = self.df[[actual, expected]].dropna()
            if len(d) < 5:
                return
            gap = d[actual] - d[expected]
            over, under = int((gap > 0).sum()), int((gap < 0).sum())
            rows, name_key = self._scatter_sample(actual, expected)
            cid = self._chart(f"{actual} vs {expected}", "scatter",
                              rows, x=expected, y=actual, name_key=name_key,
                              title=f"{actual} vs {expected} (above the line = overperforming)")
            self._add("performance",
                      f"Comparing '{actual}' against '{expected}': {over} records overperform and "
                      f"{under} underperform, with a mean gap of {gap.mean():+.2f} — the core "
                      f"over/under-performance signal the report is about.",
                      importance=1.0, columns=[actual, expected], chart_id=cid)
            # By the focus segment (e.g. which positions overperform xG).
            seg = next((s for s in self.segment_cols if s in self.focus),
                       self.segment_cols[0] if self.segment_cols else None)
            if seg:
                gdf = self.df[[seg, actual, expected]].dropna().copy()
                gdf["_gap"] = gdf[actual] - gdf[expected]
                g = gdf.groupby(seg, dropna=True)["_gap"].mean().dropna().sort_values(ascending=False)
                if len(g) >= 2:
                    rows = [{seg: str(k), "gap": round(float(v), 4)} for k, v in g.items()]
                    cid2 = self._chart(f"Average {actual}-minus-{expected} by {seg}", "bar", rows,
                                       x=seg, y="gap", title=f"Over/under-performance by {seg}",
                                       y_label=f"avg ({actual} − {expected})")
                    self._add("performance",
                              f"Over/under-performance ('{actual}' minus '{expected}') is greatest for "
                              f"{seg}='{g.index[0]}' ({g.iloc[0]:+.2f}) and worst for "
                              f"'{g.index[-1]}' ({g.iloc[-1]:+.2f}) — the elite finishers vs the "
                              f"inefficient ones.",
                              importance=1.0, columns=[seg, actual, expected], chart_id=cid2)
        self._probe("performance_gap", _run)

    def overview(self) -> None:
        def _run():
            cells = self.n * max(1, len(self.ctx.columns))
            missing = int(self.df.isna().sum().sum())
            pct = 100 * missing / cells if cells else 0
            self._add("overview",
                      f"The dataset has {self.n:,} rows and {len(self.ctx.columns)} columns "
                      f"({len(self.numeric)} numeric measures, {len(self.categorical)} categorical "
                      f"dimensions); {pct:.1f}% of all cells are missing.",
                      importance=0.25)
        self._probe("overview", _run)

    def missingness(self) -> None:
        def _run():
            nulls = self.df.isna().sum()
            miss = nulls[nulls > 0].sort_values(ascending=False)
            if miss.empty:
                self._add("quality", "The dataset is complete — no missing values in any column.",
                          importance=0.3)
                return
            rows = [{"column": str(c), "missing_pct": round(100 * v / self.n, 2)}
                    for c, v in miss.head(10).items()]
            cid = self._chart("Missing values by column (%)", "bar", rows,
                              x="column", y="missing_pct",
                              title="Missing values by column (%)", y_label="% missing")
            top = miss.index[0]
            self._add("quality",
                      f"{len(miss)} column(s) have missing data; '{top}' is worst at "
                      f"{100 * miss.iloc[0] / self.n:.1f}% missing.",
                      importance=0.5 if miss.iloc[0] / self.n > 0.05 else 0.35,
                      columns=[str(top)], chart_id=cid)
        self._probe("missingness", _run)

    def correlations(self) -> None:
        def _run():
            num = self.df[self.numeric] if self.numeric else self.df.iloc[:, :0]
            if num.shape[1] < 2:
                return
            corr = num.corr(numeric_only=True)
            seen, pairs = set(), []
            for a in corr.columns:
                for b in corr.columns:
                    if a == b or (b, a) in seen:
                        continue
                    seen.add((a, b))
                    r = corr.loc[a, b]
                    if pd.notna(r):
                        pairs.append((a, b, float(r)))
            pairs.sort(key=lambda p: abs(p[2]), reverse=True)
            kept = 0
            for a, b, r in pairs:
                if abs(r) < 0.3 or kept >= 3:
                    break
                if abs(r) >= _REDUNDANT_R:
                    continue  # duplicate/derived column — r≈1.00 is an artifact, not insight
                kept += 1
                rows, name_key = self._scatter_sample(a, b)
                cid = self._chart(f"{a} vs {b} (scatter)", "scatter",
                                  rows, x=a, y=b, name_key=name_key, title=f"{a} vs {b}")
                direction = "positive" if r > 0 else "negative"
                strength = "strong" if abs(r) >= 0.6 else "moderate"
                self._add("correlation",
                          f"'{a}' and '{b}' move together — a {strength} {direction} "
                          f"correlation (r = {r:.2f}).",
                          importance=0.6 + abs(r) * 0.35, columns=[a, b], chart_id=cid)
        self._probe("correlations", _run)

    def measures_across_dims(self) -> None:
        """The goal's core when it says 'A versus B by <dimension>' (e.g. Solo vs
        Lead streams by Country): two focus measures side-by-side per group, as a
        grouped bar over the TOP-N groups. Ranks highest — it's the actual question."""
        def _run():
            fmeasures = [m for m in self.measures if m in self.focus]
            fdims = [d for d in self.segment_cols if d in self.focus]
            if len(fmeasures) < 2 or not fdims:
                return
            a, b = fmeasures[0], fmeasures[1]
            agg = "mean"  # comparing two rates side by side; mean keeps them comparable
            for dim in fdims[:2]:
                g = self.df.groupby(dim, dropna=True)[[a, b]].agg(agg).dropna()
                if len(g) < 2:
                    continue
                top = g.sort_values(a, ascending=False).head(_TOP_GROUPS)
                rows = [
                    {dim: str(k), a: round(float(r[a]), 2), b: round(float(r[b]), 2)}
                    for k, r in top.iterrows()
                ]
                shown = f" (top {len(top)})" if len(g) > len(top) else ""
                cid = self._chart(f"{a} vs {b} by {dim}", "grouped_bar", rows,
                                  x=dim, y=a, y2=b, title=f"{a} vs {b} by {dim}{shown}")
                lead = top.index[0]
                ratio = top.iloc[0][a] / (top.iloc[0][b] + 1e-9)
                self._add("segment",
                          f"Comparing '{a}' against '{b}' across '{dim}', '{lead}' leads on "
                          f"'{a}' ({top.iloc[0][a]:.1f}) with a {a}-to-{b} ratio of {ratio:.2f} — "
                          f"the core '{a} versus {b} by {dim}' pattern the goal asks for"
                          + (f" (showing the top {len(top)} of {len(g)})." if len(g) > len(top) else "."),
                          importance=0.95, columns=[dim, a, b], chart_id=cid)
        self._probe("measures_across_dims", _run)

    def segments(self) -> None:
        def _run():
            measures = self.measures[:3]
            for measure in measures[:2]:
                agg = self._agg_for(measure)
                word = "Total" if agg == "sum" else "Average"
                for seg in self.segment_cols[:3]:
                    grp = self.df.groupby(seg, dropna=True)[measure].agg(agg).dropna().sort_values(ascending=False)
                    if len(grp) < 2:
                        continue
                    total_groups = len(grp)
                    top = grp.head(_TOP_GROUPS)  # top-N so a 43-category chart stays readable
                    rows = [{seg: str(k), measure: round(float(v), 4)} for k, v in top.items()]
                    shown = f" (top {len(top)})" if total_groups > len(top) else ""
                    cid = self._chart(f"{word} {measure} by {seg}", "bar", rows, x=seg, y=measure,
                                      title=f"{word} {measure} by {seg}{shown}", y_label=f"{word.lower()} {measure}")
                    hi_k, hi_v = grp.index[0], grp.iloc[0]
                    lo_k, lo_v = grp.index[-1], grp.iloc[-1]
                    spread = abs(hi_v - lo_v) / (abs(grp.mean()) + 1e-9)
                    scope = f" across {total_groups} groups" if total_groups > len(top) else ""
                    self._add("segment",
                              f"{word} '{measure}' varies markedly by '{seg}'{scope}: highest for "
                              f"'{hi_k}' ({hi_v:.2f}) and lowest for '{lo_k}' ({lo_v:.2f}) — a "
                              f"{100 * spread:.0f}% relative gap.",
                              importance=0.45 + min(spread, 1.0) * 0.4,
                              columns=[seg, measure], chart_id=cid)
        self._probe("segments", _run)

    def two_way_segments(self) -> None:
        """A measure across TWO dimensions at once → grouped bar (the 'cross-tab'
        richness a flat by-group chart can't show)."""
        def _run():
            measure = self.measures[0] if self.measures else None
            small = [s for s in self.segment_cols if self.df[s].nunique(dropna=True) <= 6]
            if not measure or len(small) < 2:
                return
            seg1, seg2 = small[0], small[1]
            agg = self._agg_for(measure)
            word = "Total" if agg == "sum" else "Average"
            g = self.df.groupby([seg1, seg2], dropna=True)[measure].agg(agg).reset_index().dropna()
            if g.empty:
                return
            g[measure] = g[measure].round(4)
            g[seg1] = g[seg1].astype(str)
            g[seg2] = g[seg2].astype(str)
            cid = self._chart(f"{measure} by {seg1} and {seg2}", "grouped_bar",
                              g.to_dict("records"), x=seg1, y=measure, series=seg2,
                              title=f"{word} {measure} by {seg1} and {seg2}", y_label=f"{word.lower()} {measure}")
            top = g.loc[g[measure].idxmax()]
            self._add("segment",
                      f"Combining '{seg1}' and '{seg2}', {word.lower()} '{measure}' peaks for "
                      f"{seg1}='{top[seg1]}', {seg2}='{top[seg2]}' ({top[measure]:.2f}) — "
                      f"the interaction matters, not either dimension alone.",
                      importance=0.72, columns=[seg1, seg2, measure], chart_id=cid)
        self._probe("two_way_segments", _run)

    def cohorts(self) -> None:
        """Quartile the primary measure and profile the top vs bottom cohort across
        several other metrics → a radar 'fingerprint' of what high performers look like."""
        def _run():
            if len(self.measures) < 3:
                return
            measure = self.measures[0]
            others = [m for m in self.measures[1:] if self.df[m].nunique() > 1][:5]
            if len(others) < 2:
                return
            try:
                q = pd.qcut(self.df[measure], 4, labels=["Bottom 25%", "Q2", "Q3", "Top 25%"],
                            duplicates="drop")
            except ValueError:
                return
            means = self.df.groupby(q, observed=True)[others].mean()
            if "Top 25%" not in means.index or "Bottom 25%" not in means.index:
                return
            # Normalize each metric 0..1 across cohorts so a radar compares fairly.
            norm = (means - means.min()) / (means.max() - means.min() + 1e-9)
            rows = []
            for cohort in ("Bottom 25%", "Top 25%"):
                for metric in others:
                    rows.append({"metric": metric, "cohort": cohort,
                                 "value": round(float(norm.loc[cohort, metric]), 3)})
            cid = self._chart(f"Top vs bottom {measure} cohort profile", "radar", rows,
                              x="metric", y="value", series="cohort",
                              title=f"Profile: top vs bottom '{measure}' quartile")
            # Headline the metric with the biggest top-vs-bottom gap.
            gaps = (means.loc["Top 25%"] - means.loc["Bottom 25%"]).abs()
            drv = gaps.idxmax()
            self._add("cohort",
                      f"The top 25% by '{measure}' differ most from the bottom 25% on '{drv}' "
                      f"({means.loc['Top 25%', drv]:.2f} vs {means.loc['Bottom 25%', drv]:.2f}), "
                      f"pointing to it as a defining trait of the strongest cohort.",
                      importance=0.78, columns=[measure, drv], chart_id=cid)
        self._probe("cohorts", _run)

    def crosstabs(self) -> None:
        """Composition of one category within another → stacked bar."""
        def _run():
            small = [s for s in self.segment_cols if self.df[s].nunique(dropna=True) <= 8]
            if len(small) < 2:
                return
            seg1, seg2 = small[0], small[1]
            ct = self.df.groupby([seg1, seg2], dropna=True).size().reset_index(name="count")
            if ct.empty:
                return
            ct[seg1] = ct[seg1].astype(str)
            ct[seg2] = ct[seg2].astype(str)
            cid = self._chart(f"Composition of {seg2} within {seg1}", "stacked_bar",
                              ct.to_dict("records"), x=seg1, y="count", series=seg2,
                              title=f"How {seg2} composition shifts across {seg1}")
            self._add("crosstab",
                      f"The mix of '{seg2}' shifts across '{seg1}' groups, revealing structural "
                      f"imbalances in how the two dimensions co-occur.",
                      importance=0.5, columns=[seg1, seg2], chart_id=cid)
        self._probe("crosstabs", _run)

    def categories(self) -> None:
        def _run():
            for col in self.segment_cols[:3]:
                vc = self.df[col].value_counts(dropna=True)
                if vc.empty:
                    continue
                k = vc.shape[0]
                rows = [{col: str(kk), "count": int(v)} for kk, v in vc.head(_MAX_SEGMENTS).items()]
                # Vary the chart: pie/donut reads best for a few slices, bar for more.
                ctype = ("donut" if k <= 4 else "pie") if k <= 6 else "bar"
                cid = self._chart(f"Composition of {col}", ctype, rows, x=col, y="count",
                                  title=f"Composition of {col}", y_label="count")
                top_share = 100 * vc.iloc[0] / vc.sum()
                self._add("category",
                          f"'{col}' spans {k} categories; '{vc.index[0]}' dominates at "
                          f"{top_share:.0f}% of records"
                          + (" (a notable imbalance)." if top_share > 60 else "."),
                          importance=0.3 + (0.15 if top_share > 60 else 0),
                          columns=[col], chart_id=cid)
        self._probe("categories", _run)

    def distributions(self) -> None:
        def _run():
            for col in self.measures[:2]:  # keep histograms from crowding the report
                s = self.df[col].dropna()
                if s.empty:
                    continue
                sample = s.sample(_HIST_SAMPLE, random_state=0) if len(s) > _HIST_SAMPLE else s
                cid = self._chart(f"Distribution of {col}", "histogram",
                                  [{col: float(v)} for v in sample], x=col,
                                  title=f"Distribution of {col}")
                skew = float(s.skew()) if len(s) > 2 else 0.0
                shape = ("right-skewed with a long upper tail" if skew > 0.5
                         else "left-skewed with a long lower tail" if skew < -0.5
                         else "roughly symmetric")
                self._add("distribution",
                          f"'{col}' spans {s.min():.2f}–{s.max():.2f} (mean {s.mean():.2f}, "
                          f"median {s.median():.2f}) and is {shape}.",
                          importance=0.32, columns=[col], chart_id=cid)
        self._probe("distributions", _run)

    def trends(self) -> None:
        def _run():
            measure = self.measures[0] if self.measures else None
            if not self.datetime or not measure:
                return
            tcol = self.datetime[0]
            ts = self.df[[tcol, measure]].copy()
            ts[tcol] = pd.to_datetime(ts[tcol], errors="coerce")
            ts = ts.dropna(subset=[tcol]).sort_values(tcol)
            if len(ts) < 4:
                return
            span = (ts[tcol].max() - ts[tcol].min()).days or 1
            freq = "D" if span <= 60 else "W" if span <= 400 else "ME"
            series = ts.set_index(tcol)[measure].resample(freq).mean().dropna()
            if len(series) < 3:
                return
            rows = [{"period": k.date().isoformat(), measure: round(float(v), 4)} for k, v in series.items()]
            cid = self._chart(f"{measure} over time", "line", rows, x="period", y=measure,
                              title=f"{measure} over time")
            first, last = series.iloc[0], series.iloc[-1]
            pct = 100 * (last - first) / (abs(first) + 1e-9)
            direction = "trended upward" if pct > 5 else "trended downward" if pct < -5 else "stayed roughly flat"
            self._add("trend",
                      f"Over the observed period, average '{measure}' {direction} "
                      f"({pct:+.0f}% from the first to the last interval).",
                      importance=0.7, columns=[tcol, measure], chart_id=cid)
        self._probe("trends", _run)

    def outliers(self) -> None:
        def _run():
            col = self.measures[0] if self.measures else None
            if not col:
                return
            s = self.df[col].dropna()
            if len(s) < 8:
                return
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr <= 0:
                return
            lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            out = int(((s < lo) | (s > hi)).sum())
            if out == 0:
                return
            self._add("quality",
                      f"'{col}' has {out} outlier(s) ({100 * out / len(s):.1f}% of values) beyond "
                      f"the [{lo:.2f}, {hi:.2f}] IQR fence — worth checking before modeling.",
                      importance=0.4 + min(out / len(s), 0.2), columns=[col])
        self._probe("outliers", _run)

    # -- finalize ------------------------------------------------------------ #
    def finalize(self) -> AnalysisResult:
        # Goal steering: lift every finding that involves a goal-named column above
        # the generic ones, so the top-N kept are the relevant ones (and unrelated
        # high-variance findings get trimmed out rather than filling the report).
        if self.focus:
            for f in self._findings:
                if set(f.columns) & self.focus:
                    f.importance += 0.45
        ranked = sorted(self._findings, key=lambda f: f.importance, reverse=True)
        ranked = ranked[: settings.ANALYSIS_MAX_FINDINGS]
        keep: list[str] = []
        for f in ranked:
            if f.chart_id and f.chart_id in self._charts and f.chart_id not in keep:
                keep.append(f.chart_id)
        keep = keep[: settings.ANALYSIS_MAX_CHARTS]
        charts = {cid: self._charts[cid] for cid in keep}
        for f in ranked:
            if f.chart_id not in charts:
                f.chart_id = None
        return AnalysisResult(findings=ranked, charts=charts, scope_note=self.scope_note)


def _is_numeric(col: dict) -> bool:
    return str(col.get("dtype", "")).lower() in ("integer", "float")
