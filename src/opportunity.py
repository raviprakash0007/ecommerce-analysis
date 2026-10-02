import pandas as pd


WEIGHTS = {
    "rating_rank": 0.28,
    "propensity_rank": 0.24,
    "review_gap_rank": 0.18,
    "in_stock_flag": 0.15,
    "discount_rank": 0.10,
    "anomaly_rank": 0.10, 
}

PRODUCT_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "propensity_for_opportunity", "anomaly_penalty", "cluster_label",
    "engagement_score", "opportunity_score",
]


def build_opportunity(eda_df, top_n=25):
   
    strategic_df = eda_df.copy()

  
    strategic_df["propensity_for_opportunity"] = (
        strategic_df["high_review_propensity"]
        if "high_review_propensity" in strategic_df.columns
        else 0.5
    )
    strategic_df["anomaly_penalty"] = (
        strategic_df["anomaly_score"] if "anomaly_score" in strategic_df.columns else 0.0
    )
    strategic_df["cluster_label"] = (
        strategic_df["cluster"] if "cluster" in strategic_df.columns else "0"
    )

   
    strategic_df["rating_rank"] = strategic_df["rating_score_imputed"].rank(pct=True)
    strategic_df["propensity_rank"] = strategic_df["propensity_for_opportunity"].rank(pct=True)
    strategic_df["discount_rank"] = strategic_df["discount_pct_filled"].rank(pct=True)
   
    strategic_df["review_gap_rank"] = 1 - strategic_df["reviews_count"].rank(pct=True)
    strategic_df["anomaly_rank"] = strategic_df["anomaly_penalty"].rank(pct=True)

    strategic_df["opportunity_score"] = (
        WEIGHTS["rating_rank"] * strategic_df["rating_rank"]
        + WEIGHTS["propensity_rank"] * strategic_df["propensity_rank"]
        + WEIGHTS["review_gap_rank"] * strategic_df["review_gap_rank"]
        + WEIGHTS["in_stock_flag"] * strategic_df["in_stock_flag"]
        + WEIGHTS["discount_rank"] * strategic_df["discount_rank"]
        - WEIGHTS["anomaly_rank"] * strategic_df["anomaly_rank"]
    ).round(4)

    strategic_products = top_strategic_products(strategic_df, top_n)
    return strategic_df, strategic_products


def top_strategic_products(strategic_df, top_n=25):

    rating_median = strategic_df["rating_score_imputed"].median()

    return (
        strategic_df[
            (strategic_df["availability"] == "in_stock")
            & (strategic_df["rating_score_imputed"] >= rating_median)
        ]
        .sort_values(
            ["opportunity_score", "propensity_for_opportunity", "rating_score_imputed"],
            ascending=[False, False, False],
        )[PRODUCT_COLS]
        .head(top_n)
        .reset_index(drop=True)
        .rename(columns={
            "propensity_for_opportunity": "high_review_propensity",
            "anomaly_penalty": "anomaly_score",
        })
    )


def source_opportunity_summary(strategic_df):
  
    summary = (
        strategic_df.groupby("source")
        .agg(
            avg_opportunity=("opportunity_score", "mean"),
            avg_propensity=("propensity_for_opportunity", "mean"),
            avg_anomaly=("anomaly_penalty", "mean"),
            products=("product_count", "sum"),
        )
        .reset_index()
        .sort_values("avg_opportunity", ascending=False)
        .reset_index(drop=True)
    )
    cols = ["avg_opportunity", "avg_propensity", "avg_anomaly"]
    summary[cols] = summary[cols].round(3)
    return summary


def map_reference_lines(strategic_df):
  
    return (
        float(strategic_df["propensity_for_opportunity"].median()),
        float(strategic_df["engagement_score"].median()),
    )


def opportunity_readout(source_opportunity, strategic_products):
   
    lines = ["Opportunity readout:"]

    if not source_opportunity.empty:
        best_source = source_opportunity.iloc[0]
        lines.append(
            f"- `{best_source['source']}` has the highest average opportunity score "
            f"at {best_source['avg_opportunity']:.3f}."
        )
    if not strategic_products.empty:
        best_product = strategic_products.iloc[0]
        lines.append(
            f"- The top product candidate in this scoring system is "
            f"`{best_product['title']}` with score {best_product['opportunity_score']:.3f}."
        )
    lines.append(
        "- This score favors strong ratings, breakout-like review propensity, low current "
        "review saturation, in-stock status, and lower anomaly risk."
    )
    return "\n".join(lines)


def run_opportunity(eda_df, top_n=25):
   
    strategic_df, strategic_products = build_opportunity(eda_df, top_n)
    source_opp = source_opportunity_summary(strategic_df)
    x_ref, y_ref = map_reference_lines(strategic_df)

    return {
        "strategic_df": strategic_df,
        "strategic_products": strategic_products,
        "source_opportunity": source_opp,
        "x_ref": x_ref,
        "y_ref": y_ref,
        "top_labels": strategic_products.head(12).copy(),
        "readout": opportunity_readout(source_opp, strategic_products),
    }