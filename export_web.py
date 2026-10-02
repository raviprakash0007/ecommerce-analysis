import json
from pathlib import Path

from src.config import DATA_PATH
from src.data_loader import load_data
from src.features import build_features
from src.models.segmentation import run_segmentation
from src.models.anomaly import run_anomaly
from src.models.propensity import run_propensity
from src.opportunity import run_opportunity

OUT_FILE = Path(__file__).resolve().parent / "website" / "data" / "data.js"

COLUMNS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "availability", "price_tier_within_currency", "engagement_score",
    "cluster", "pc1", "pc2", "anomaly_flag", "anomaly_score",
    "high_review_propensity", "opportunity_score",
    "scrape_day", "scrape_hour", "days_since_latest_scrape",
]


def build_payload(csv_path):
    """CSV se poora pipeline chalakar {'products', 'ml', 'missing'} dict return karta hai."""
    df = load_data(csv_path)  # columns validate bhi yahin hote hain
    eda_df = build_features(df)
    eda_df, _, silhouette = run_segmentation(eda_df, return_artifacts=True)
    eda_df, *_ = run_anomaly(eda_df)
    eda_df, metrics, _, art = run_propensity(eda_df, return_artifacts=True)
    eda_df["opportunity_score"] = run_opportunity(eda_df)["strategic_df"]["opportunity_score"]

    out = eda_df[[c for c in COLUMNS if c in eda_df.columns]].copy()
    for col in out.columns:
        if str(out[col].dtype) == "category":
            out[col] = out[col].astype(str)
    out = out.round(3).astype(object).where(out.notna(), None)

    miss = (df.isna().mean() * 100).round(2).sort_values(ascending=False)
    imp = art["importance"]
    return {
        "products": out.to_dict(orient="records"),
        "ml": {
            "confusion": art["confusion_matrix"].values.tolist(),
            "importance": {"feature": imp["feature"].tolist(), "importance": imp["importance"].round(4).tolist()},
            "y_test": [int(v) for v in art["y_test"]],
            "y_proba": [round(float(v), 4) for v in art["y_proba"]],
            "silhouette": silhouette.to_dict("records"),
            "metrics": metrics.to_dict("records"),
        },
        "missing": {"cols": miss.index.tolist(), "pct": miss.tolist()},
    }


def main():
    p = build_payload(DATA_PATH)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        "window.PRODUCTS = " + json.dumps(p["products"], ensure_ascii=False) + ";\n"
        "window.ML = " + json.dumps(p["ml"]) + ";\n"
        "window.MISSING = " + json.dumps(p["missing"]) + ";\n",
        encoding="utf-8",
    )
    print(f"Saved {len(p['products']):,} products + ML + missingness to {OUT_FILE}")


if __name__ == "__main__":
    main()