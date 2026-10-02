import numpy as np
import pandas as pd

DAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

RECENCY_BINS = [-0.01, 2, 5, 9, np.inf]
RECENCY_LABELS = ["0-2 days", "2-5 days", "5-9 days", "9+ days"]


def has_scrape_data(eda_df):
  
    required = ["scraped_at", "days_since_latest_scrape", "scrape_day", "scrape_hour"]
    if not all(c in eda_df.columns for c in required):
        return False
    return bool(eda_df["scraped_at"].notna().any())


def freshness_summary(eda_df):
    
    summary = (
        eda_df.groupby("source")
        .agg(
            products=("product_count", "sum"),
            oldest_scrape=("scraped_at", "min"),
            latest_scrape=("scraped_at", "max"),
            avg_days_from_latest=("days_since_latest_scrape", "mean"),
            median_days_from_latest=("days_since_latest_scrape", "median"),
        )
        .reset_index()
        .sort_values("avg_days_from_latest")
        .reset_index(drop=True)
    )
    cols = ["avg_days_from_latest", "median_days_from_latest"]
    summary[cols] = summary[cols].round(2)
    return summary


def scrape_day_counts(eda_df):
    """Har din (Monday-Sunday) kitne products scrape hue."""
    counts = (
        eda_df["scrape_day"]
        .value_counts()
        .reindex(DAY_ORDER)
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    counts.columns = ["scrape_day", "products"]
    return counts


def source_hour_heatmap(eda_df):
    """Source x hour (0-23) scrape activity table."""
    return (
        eda_df.groupby(["source", "scrape_hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=range(24), fill_value=0)
    )


def freshness_box_data(eda_df):
    """Boxplot ke liye source aur days_since_latest_scrape."""
    return eda_df[["source", "days_since_latest_scrape"]].copy()


def recency_mix(eda_df):
    """Source ke hisaab se recency buckets ka share (%)."""
    recency_category = pd.cut(
        eda_df["days_since_latest_scrape"],
        bins=RECENCY_BINS,
        labels=RECENCY_LABELS,
        include_lowest=True,
    )
    return (
        pd.crosstab(eda_df["source"], recency_category, normalize="index")
        .reindex(columns=RECENCY_LABELS, fill_value=0)
        .fillna(0)
        * 100
    ).round(1)


def freshness_readout(summary):
    """Notebook ke 'Freshness readout' ka text."""
    freshest = summary.sort_values("avg_days_from_latest").iloc[0]
    stalest = summary.sort_values("avg_days_from_latest", ascending=False).iloc[0]

    lines = [
        "Freshness readout:",
        f"- `{freshest['source']}` has the freshest average capture window at "
        f"{freshest['avg_days_from_latest']:.2f} days from the latest scrape.",
        f"- `{stalest['source']}` is the stalest on average at "
        f"{stalest['avg_days_from_latest']:.2f} days.",
        "- Use the hour heatmap and recency mix to decide whether observed marketplace "
        "differences may partly reflect capture timing rather than pure catalog behavior.",
    ]
    return "\n".join(lines)


def run_freshness(eda_df):

    if not has_scrape_data(eda_df):
        return {
            "available": False,
            "summary": pd.DataFrame(),
            "day_counts": pd.DataFrame(),
            "hour_heatmap": pd.DataFrame(),
            "box_data": pd.DataFrame(),
            "recency_mix": pd.DataFrame(),
            "readout": "No usable scraped_at field is available for freshness analysis.",
        }

    summary = freshness_summary(eda_df)
    return {
        "available": True,
        "summary": summary,
        "day_counts": scrape_day_counts(eda_df),
        "hour_heatmap": source_hour_heatmap(eda_df),
        "box_data": freshness_box_data(eda_df),
        "recency_mix": recency_mix(eda_df),
        "readout": freshness_readout(summary),
    }