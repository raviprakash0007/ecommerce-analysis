import numpy as np
import pandas as pd


def source_commercial_summary(eda_df):
    """Source x currency ke hisaab se commercial summary."""
    summary = (
        eda_df.groupby(["source", "currency"])
        .agg(
            products=("product_count", "sum"),
            median_price=("price_current", "median"),
            avg_rating=("rating_score_imputed", "mean"),
            avg_reviews=("reviews_count", "mean"),
            discounted_share=("has_discount", "mean"),
            avg_discount=("discount_pct_filled", "mean"),
            in_stock_share=("in_stock_flag", "mean"),
        )
        .reset_index()
    )

    for col in ["median_price", "avg_rating", "avg_reviews", "avg_discount"]:
        summary[col] = summary[col].round(2)
    summary["discounted_share"] = (summary["discounted_share"] * 100).round(1)
    summary["in_stock_share"] = (summary["in_stock_share"] * 100).round(1)

    return summary.sort_values(
        ["discounted_share", "avg_rating"], ascending=[False, False]
    ).reset_index(drop=True)


def discount_penetration(eda_df):
    """Category x source heatmap table: kitne % products par discount hai."""
    return (
        eda_df.pivot_table(
            index="category", columns="source", values="has_discount", aggfunc="mean"
        )
        .fillna(0)
        .mul(100)
        .round(1)
    )


def brand_engagement_rank(eda_df, min_products=8, top_n=15):
    """
    Sabse engaging brands (kam se kam `min_products` products wale).
    Plot ke liye ascending order mein return hota hai (barh mein top brand upar aaye).
    """
    ranked = (
        eda_df.groupby("brand")
        .agg(
            products=("product_count", "sum"),
            avg_rating=("rating_score_imputed", "mean"),
            total_reviews=("reviews_count", "sum"),
            avg_engagement=("engagement_score", "mean"),
        )
        .query("products >= @min_products")
        .sort_values(["avg_engagement", "total_reviews"], ascending=[False, False])
        .head(top_n)
        .reset_index()
    )
    return ranked.sort_values("avg_engagement").reset_index(drop=True)


def category_rating(eda_df):
    """Category ke hisaab se average rating (high se low)."""
    return (
        eda_df.groupby("category")["rating_score_imputed"]
        .mean()
        .sort_values(ascending=False)
    )


def commercial_readout(source_summary, cat_rating, brand_rank):
    """Notebook ke 'Commercial readout' ka text."""
    top_discount = source_summary.sort_values("discounted_share", ascending=False).iloc[0]
    top_brand = brand_rank.sort_values("avg_engagement", ascending=False).iloc[0]

    lines = [
        "Commercial readout:",
        f"- {top_discount['source']} shows the highest discounted share at {top_discount['discounted_share']}%.",
        f"- {cat_rating.index[0]} has the highest average rating at {cat_rating.iloc[0]:.2f}.",
        f"- {top_brand['brand']} leads the brand engagement ranking with an average engagement score of {top_brand['avg_engagement']:.2f}.",
        "- The price-vs-rating view should be read within each currency panel, not across currencies.",
    ]
    return "\n".join(lines)


def run_commercial(eda_df, min_products=8, top_n=15):
    """
    Section 5 ke saare tables ek dict mein.
    Keys: eda_df, source_summary, discount_penetration, brand_rank,
          category_rating, readout
    Note: eda_df wapas isliye milta hai kyunki `has_discount` aur `reviews_size`
    missing hon to yahan ban jate hain.
    """
    eda_df = _ensure_columns(eda_df)

    source_summary = source_commercial_summary(eda_df)
    penetration = discount_penetration(eda_df)
    brand_rank = brand_engagement_rank(eda_df, min_products, top_n)
    cat_rating = category_rating(eda_df)

    return {
        "eda_df": eda_df,
        "source_summary": source_summary,
        "discount_penetration": penetration,
        "brand_rank": brand_rank,
        "category_rating": cat_rating,
        "readout": commercial_readout(source_summary, cat_rating, brand_rank),
    }


def _ensure_columns(eda_df):
    """Zaroori helper columns na hon to bana do (original df ko chhue bina)."""
    missing = [c for c in ["has_discount", "reviews_size"] if c not in eda_df.columns]
    if not missing:
        return eda_df

    eda_df = eda_df.copy()
    if "has_discount" in missing:
        eda_df["has_discount"] = (eda_df["discount_pct_filled"] > 0).astype(int)
    if "reviews_size" in missing:
        eda_df["reviews_size"] = eda_df["reviews_count"].clip(
            lower=10, upper=eda_df["reviews_count"].quantile(0.95)
        )
    return eda_df