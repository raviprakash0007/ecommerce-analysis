import numpy as np
import pandas as pd

# (column, weight, invert)  invert=True matlab: value jitni kam, score utna acha
SCORE_COMPONENTS = [
    ("avg_rating", 0.25, False),
    ("avg_engagement", 0.25, False),
    ("in_stock_share", 0.20, False),
    ("avg_review_propensity", 0.15, False),
    ("avg_discount", 0.10, False),
    ("anomaly_share", 0.15, True),
]

ROUND_COLS = [
    "median_price", "avg_rating", "avg_reviews", "avg_discount",
    "avg_engagement", "in_stock_share", "anomaly_share",
    "avg_review_propensity", "benchmark_score",
]

GROUP_COLS = ["source", "category"]


def build_benchmark(eda_df):
    """
    Source x category pockets ka benchmark table banata hai.

    Zaroori: pehle build_features() chalna chahiye.
    Optional (pehle chalne chahiye, warna un components ka score 0 rahega):
      - run_anomaly()    -> anomaly_flag
      - run_propensity() -> high_review_propensity

    Returns: benchmark_df (benchmark_score ke saath)
    """
    benchmark_df = (
        eda_df.groupby(GROUP_COLS)
        .agg(
            products=("product_count", "sum"),
            median_price=("price_current", "median"),
            avg_rating=("rating_score_imputed", "mean"),
            avg_reviews=("reviews_count", "mean"),
            avg_discount=("discount_pct_filled", "mean"),
            avg_engagement=("engagement_score", "mean"),
            in_stock_share=("in_stock_flag", "mean"),
        )
        .reset_index()
    )

    # Anomaly share (agar anomaly model chala ho)
    if "anomaly_flag" in eda_df.columns:
        anomaly_share = (
            eda_df.assign(anomaly_binary=(eda_df["anomaly_flag"] == "Anomalous").astype(int))
            .groupby(GROUP_COLS)["anomaly_binary"]
            .mean()
            .reset_index(name="anomaly_share")
        )
        benchmark_df = benchmark_df.merge(anomaly_share, on=GROUP_COLS, how="left")
    else:
        benchmark_df["anomaly_share"] = np.nan

    # Review propensity (agar propensity model chala ho)
    if "high_review_propensity" in eda_df.columns:
        propensity = (
            eda_df.groupby(GROUP_COLS)["high_review_propensity"]
            .mean()
            .reset_index(name="avg_review_propensity")
        )
        benchmark_df = benchmark_df.merge(propensity, on=GROUP_COLS, how="left")
    else:
        benchmark_df["avg_review_propensity"] = np.nan

    # Shares ko percent mein badlo
    benchmark_df["in_stock_share"] = benchmark_df["in_stock_share"] * 100
    benchmark_df["anomaly_share"] = benchmark_df["anomaly_share"] * 100

    benchmark_df["benchmark_score"] = _weighted_score(benchmark_df)

    benchmark_df[ROUND_COLS] = benchmark_df[ROUND_COLS].round(2)
    return benchmark_df


def _weighted_score(benchmark_df):
    """Har component ka z-score nikaal kar weight ke saath jodta hai."""
    score = pd.Series(0.0, index=benchmark_df.index)

    for col, weight, invert in SCORE_COMPONENTS:
        series = benchmark_df[col].astype(float)

        # Component available nahi ya sab pockets same hain -> score mein 0 jodo
        if series.notna().sum() <= 1 or np.isclose(series.std(ddof=0), 0):
            scaled = pd.Series(0.0, index=benchmark_df.index)
        else:
            scaled = (series - series.mean()) / series.std(ddof=0)

        if invert:
            scaled = -scaled
        score += weight * scaled.fillna(0)

    return score


def benchmark_pivot(benchmark_df):
    """Category x source heatmap table (benchmark_score)."""
    return benchmark_df.pivot(index="category", columns="source", values="benchmark_score")


def strongest_pockets(benchmark_df, top_n=15):
    """Sabse mazboot source-category pockets."""
    return (
        benchmark_df.sort_values(["benchmark_score", "products"], ascending=[False, False])
        .head(top_n)
        .reset_index(drop=True)
    )


def weakest_pockets(benchmark_df, top_n=10):
    """Sabse kamzor source-category pockets."""
    return (
        benchmark_df.sort_values(["benchmark_score", "products"], ascending=[True, False])
        .head(top_n)
        .reset_index(drop=True)
    )


def benchmark_readout(strongest, weakest):
    """Notebook ke 'Benchmark readout' ka text."""
    top = strongest.iloc[0]
    risk = weakest.iloc[0]
    lines = [
        "Benchmark readout:",
        f"- The strongest source-category pocket is `{top['source']} | {top['category']}` "
        f"with benchmark score {top['benchmark_score']:.2f}.",
        f"- The weakest pocket is `{risk['source']} | {risk['category']}` "
        f"with score {risk['benchmark_score']:.2f}.",
        "- Use the heatmap to compare pockets structurally, and use the scatter to spot "
        "combinations with healthy stock but weak engagement or vice versa.",
    ]
    return "\n".join(lines)


def run_benchmark(eda_df, top_strong=15, top_weak=10):
    """
    Section 11 ke saare tables ek dict mein (notebook ke liye).
    Keys: benchmark_df, pivot, strongest, weakest, readout
    """
    benchmark_df = build_benchmark(eda_df)
    strong = strongest_pockets(benchmark_df, top_strong)
    weak = weakest_pockets(benchmark_df, top_weak)
    return {
        "benchmark_df": benchmark_df,
        "pivot": benchmark_pivot(benchmark_df),
        "strongest": strong,
        "weakest": weak,
        "readout": benchmark_readout(strong, weak),
    }