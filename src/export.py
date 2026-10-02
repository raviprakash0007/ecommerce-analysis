from pathlib import Path

import pandas as pd

from .config import EXPORT_DIR, EXPORT_FILES

ANOMALY_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "availability", "anomaly_score",
]

HIDDEN_GEM_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "engagement_score",
]

BREAKOUT_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "high_review_propensity",
]


def build_top_anomalies(eda_df, top_n=50):
    """Sabse zyada anomaly score wale products. Model nahi chala to khali table."""
    if "anomaly_score" not in eda_df.columns:
        return pd.DataFrame()
    return (
        eda_df.sort_values("anomaly_score", ascending=False)[ANOMALY_COLS]
        .head(top_n)
        .copy()
    )


def build_hidden_gems(eda_df, top_n=50):
    """In-stock, high rating (top 15%) aur low reviews (bottom 35%) wale products."""
    high_rating_cutoff = float(eda_df["rating_score_imputed"].quantile(0.85))
    low_review_cutoff = int(eda_df["reviews_count"].quantile(0.35))

    return (
        eda_df[
            (eda_df["availability"] == "in_stock")
            & (eda_df["rating_score_imputed"] >= high_rating_cutoff)
            & (eda_df["reviews_count"] <= low_review_cutoff)
        ][HIDDEN_GEM_COLS]
        .sort_values(
            ["rating_score_imputed", "reviews_count", "engagement_score"],
            ascending=[False, True, False],
        )
        .head(top_n)
        .copy()
    )


def build_breakout_candidates(eda_df, top_n=50):
    """Abhi low-review, lekin model ke hisaab se high-review jaise products."""
    if not {"high_review_flag", "high_review_propensity"}.issubset(eda_df.columns):
        return pd.DataFrame()

    cutoff = eda_df["high_review_propensity"].quantile(0.90)
    return (
        eda_df[
            (eda_df["high_review_flag"] == 0)
            & (eda_df["high_review_propensity"] >= cutoff)
        ][BREAKOUT_COLS]
        .sort_values(
            ["high_review_propensity", "rating_score_imputed", "reviews_count"],
            ascending=[False, False, False],
        )
        .head(top_n)
        .copy()
    )


def build_summary_note(eda_df):
    """executive_summary.txt ka chhota text."""
    lines = [
        "E-Commerce notebook export summary",
        f"Rows: {len(eda_df)}",
        f"Sources: {eda_df['source'].nunique()}",
        f"Categories: {eda_df['category'].nunique()}",
    ]
    if "anomaly_flag" in eda_df.columns:
        lines.append(f"Anomalies: {(eda_df['anomaly_flag'] == 'Anomalous').sum()}")
    if "high_review_propensity" in eda_df.columns:
        lines.append(f"High-review cutoff: {int(eda_df['reviews_count'].quantile(0.75))}")
    return "\n".join(lines) + "\n"


def export_all(eda_df, benchmark_df=None, strategic_products=None,
               export_dir=EXPORT_DIR, summary_text=None):

    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        EXPORT_FILES["benchmark"]: benchmark_df,
        EXPORT_FILES["anomalies"]: build_top_anomalies(eda_df),
        EXPORT_FILES["hidden_gems"]: build_hidden_gems(eda_df),
        EXPORT_FILES["breakout"]: build_breakout_candidates(eda_df),
        EXPORT_FILES["strategic"]: strategic_products,
    }

    manifest_rows = []
    for filename, table in exports.items():
        # Khali ya missing table save nahi hoti
        if table is None or table.empty:
            continue
        out_path = export_dir / filename
        table.to_csv(out_path, index=False)
        manifest_rows.append({"file": filename, "rows": len(table), "path": str(out_path)})

    # Summary text
    summary_path = export_dir / EXPORT_FILES["summary"]
    note = build_summary_note(eda_df)
    if summary_text:
        note += "\n" + summary_text.strip() + "\n"
    summary_path.write_text(note, encoding="utf-8")
    manifest_rows.append({
        "file": EXPORT_FILES["summary"],
        "rows": note.count("\n"),
        "path": str(summary_path),
    })

    return pd.DataFrame(manifest_rows, columns=["file", "rows", "path"])