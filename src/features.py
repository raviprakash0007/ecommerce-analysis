import numpy as np
import pandas as pd


def build_features(df):
 
    eda_df = df.copy()


    eda_df["price_original_filled"] = eda_df["price_original"].fillna(eda_df["price_current"])
    eda_df["discount_pct_filled"] = eda_df["discount_pct"].fillna(0)
    eda_df["has_discount"] = (eda_df["discount_pct_filled"] > 0).astype(int)
    eda_df["discount_amount"] = (
        eda_df["price_original_filled"] - eda_df["price_current"]
    ).clip(lower=0)
    eda_df["price_log1p"] = np.log1p(eda_df["price_current"])

   
    rating_median = eda_df["rating_score"].median()
    eda_df["rating_score_imputed"] = eda_df["rating_score"].fillna(rating_median)
    eda_df["rating_missing_flag"] = eda_df["rating_score"].isna().astype(int)
    eda_df["reviews_log1p"] = np.log1p(eda_df["reviews_count"])

   
    eda_df["reviews_size"] = eda_df["reviews_count"].clip(
        lower=10, upper=eda_df["reviews_count"].quantile(0.95)
    )

    eda_df["engagement_score"] = eda_df["rating_score_imputed"] * np.log1p(
        eda_df["reviews_count"]
    )


    title = _text_series(eda_df, "title")
    description = _text_series(eda_df, "description")
    eda_df["title_length"] = title.str.len()
    eda_df["title_word_count"] = title.str.split().str.len()
    eda_df["description_length"] = description.str.len()

   
    eda_df["in_stock_flag"] = (eda_df["availability"] == "in_stock").astype(int)
    eda_df["limited_flag"] = (eda_df["availability"] == "limited").astype(int)

  
    eda_df["product_count"] = 1


    eda_df["price_rank_within_currency"] = eda_df.groupby("currency")[
        "price_current"
    ].rank(pct=True)

    eda_df["price_tier_within_currency"] = pd.cut(
        eda_df["price_rank_within_currency"],
        bins=[0, 0.25, 0.50, 0.75, 1.00],
        labels=["Budget", "Mid-range", "Premium", "Luxury"],
        include_lowest=True,
    )

    eda_df["discount_depth"] = pd.cut(
        eda_df["discount_pct_filled"],
        bins=[-0.01, 0, 10, 20, 100],
        labels=["No discount", "Low", "Medium", "High"],
        include_lowest=True,
    )

 
    if "scraped_at" in eda_df.columns and eda_df["scraped_at"].notna().any():
        latest_scrape = eda_df["scraped_at"].max()
        eda_df["days_since_latest_scrape"] = (
            (latest_scrape - eda_df["scraped_at"]).dt.total_seconds() / 86400
        ).round(2)
        eda_df["scrape_day"] = eda_df["scraped_at"].dt.day_name()
        eda_df["scrape_hour"] = eda_df["scraped_at"].dt.hour

    return eda_df


def feature_preview(eda_df, n=10):
    """Engineered features ka chhota preview table."""
    cols = [
        "title", "brand", "source", "currency", "price_current",
        "price_original_filled", "discount_pct_filled", "has_discount",
        "discount_amount", "rating_score_imputed", "rating_missing_flag",
        "reviews_count", "price_tier_within_currency", "discount_depth",
        "engagement_score",
    ]
    return eda_df[[c for c in cols if c in eda_df.columns]].head(n)


def feature_health(eda_df):
    """Engineered features mein missing % ka health check."""
    features = [
        "discount_pct_filled", "has_discount", "discount_amount",
        "rating_score_imputed", "price_tier_within_currency",
        "discount_depth", "engagement_score",
    ]
    return pd.DataFrame({
        "feature": features,
        "missing_pct": [round(float(eda_df[f].isna().mean() * 100), 2) for f in features],
    })


def _text_series(df, col):
   
    if col not in df.columns:
        return pd.Series("", index=df.index)
    return df[col].fillna("").astype(str)