import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from ..config import RANDOM_STATE

ANOMALY_FEATURES = [
    "price_current",
    "discount_pct_filled",
    "rating_score_imputed",
    "reviews_count",
    "title_length",
    "description_length",
    "price_rank_within_currency",
    "engagement_score",
]

# export.py ke cutoffs ke saath same rakhna
HIGH_RATING_QUANTILE = 0.85
LOW_REVIEW_QUANTILE = 0.35

TOP_ANOMALY_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "discount_pct_filled", "rating_score_imputed", "reviews_count",
    "availability", "anomaly_score",
]

HIDDEN_GEM_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "price_tier_within_currency", "engagement_score",
]


def run_anomaly(eda_df, contamination=0.05):
    """
    Unusual listings dhoondta hai aur hidden-gem candidates nikaalta hai.

    Adds to eda_df: anomaly_flag ('Anomalous'/'Typical'), anomaly_score (zyada = zyada unusual)

    Returns:
        (eda_df, anomaly_summary, top_anomalies, hidden_gems)
    """
    df = eda_df.copy()

    X = df[ANOMALY_FEATURES]
    X_ready = StandardScaler().fit_transform(
        SimpleImputer(strategy="median").fit_transform(X)
    )

    model = IsolationForest(
        n_estimators=300, contamination=contamination, random_state=RANDOM_STATE
    )
    labels = model.fit_predict(X_ready)

    df["anomaly_flag"] = np.where(labels == -1, "Anomalous", "Typical")
    df["anomaly_score"] = (-model.decision_function(X_ready)).round(4)

    anomaly_summary = _anomaly_summary(df)
    top_anomalies = (
        df.sort_values("anomaly_score", ascending=False)[TOP_ANOMALY_COLS]
        .head(15)
        .reset_index(drop=True)
    )
    hidden_gems = find_hidden_gems(df, top_n=20)

    return df, anomaly_summary, top_anomalies, hidden_gems


def _anomaly_summary(df):
    summary = (
        df.groupby("source")
        .agg(
            products=("product_count", "sum"),
            anomalies=("anomaly_flag", lambda s: int((s == "Anomalous").sum())),
            anomaly_share_pct=("anomaly_flag", lambda s: round(float((s == "Anomalous").mean() * 100), 2)),
            avg_price=("price_current", "mean"),
            avg_rating=("rating_score_imputed", "mean"),
        )
        .reset_index()
        .sort_values("anomaly_share_pct", ascending=False)
        .reset_index(drop=True)
    )
    summary[["avg_price", "avg_rating"]] = summary[["avg_price", "avg_rating"]].round(2)
    return summary


def find_hidden_gems(df, top_n=20):
    """In-stock, high rating (top 15%) aur low reviews (bottom 35%) wale products."""
    high_rating_cutoff = float(df["rating_score_imputed"].quantile(HIGH_RATING_QUANTILE))
    low_review_cutoff = int(df["reviews_count"].quantile(LOW_REVIEW_QUANTILE))

    return (
        df[
            (df["availability"] == "in_stock")
            & (df["rating_score_imputed"] >= high_rating_cutoff)
            & (df["reviews_count"] <= low_review_cutoff)
        ]
        .sort_values(
            ["rating_score_imputed", "reviews_count", "engagement_score"],
            ascending=[False, True, False],
        )[HIDDEN_GEM_COLS]
        .head(top_n)
        .reset_index(drop=True)
    )


def anomaly_readout(eda_df):
    """Notebook ke 'Anomaly readout' ka text."""
    count = int((eda_df["anomaly_flag"] == "Anomalous").sum())
    high_rating_cutoff = float(eda_df["rating_score_imputed"].quantile(HIGH_RATING_QUANTILE))
    low_review_cutoff = int(eda_df["reviews_count"].quantile(LOW_REVIEW_QUANTILE))
    return "\n".join([
        "Anomaly readout:",
        f"- The model flagged {count} products as unusual out of {len(eda_df)} total rows.",
        f"- The strict hidden-gem filter uses rating >= {high_rating_cutoff:.2f} and reviews <= {low_review_cutoff}.",
        "- Use the anomaly table for audit-style inspection and the hidden-gem table for discovery-style storytelling.",
    ])