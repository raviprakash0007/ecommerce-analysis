import pandas as pd


def headline_stats(eda_df, benchmark_df=None, strategic_products=None):
 
    stats = {}

  
    source_engagement = (
        eda_df.groupby("source")["engagement_score"].mean().sort_values(ascending=False)
    )
    if not source_engagement.empty:
        stats["top_source"] = source_engagement.index[0]
        stats["top_source_engagement"] = float(source_engagement.iloc[0])

   
    category_rating = (
        eda_df.groupby("category")["rating_score_imputed"].mean().sort_values(ascending=False)
    )
    if not category_rating.empty:
        stats["top_category"] = category_rating.index[0]
        stats["top_category_rating"] = float(category_rating.iloc[0])

    
    brand_reviews = eda_df.groupby("brand")["reviews_count"].sum().sort_values(ascending=False)
    if not brand_reviews.empty:
        stats["most_reviewed_brand"] = brand_reviews.index[0]
        stats["most_reviewed_brand_reviews"] = int(brand_reviews.iloc[0])

    
    if "anomaly_flag" in eda_df.columns:
        anomaly_share = (
            eda_df.assign(anomaly_binary=(eda_df["anomaly_flag"] == "Anomalous").astype(int))
            .groupby("source")["anomaly_binary"]
            .mean()
            .sort_values(ascending=False)
        )
        if not anomaly_share.empty:
            stats["anomaly_source"] = anomaly_share.index[0]

   
    if benchmark_df is not None and not benchmark_df.empty:
        pocket = benchmark_df.sort_values("benchmark_score", ascending=False).iloc[0]
        stats["best_pocket_source"] = pocket["source"]
        stats["best_pocket_category"] = pocket["category"]
        stats["best_pocket_score"] = float(pocket["benchmark_score"])

   
    if strategic_products is not None and not strategic_products.empty:
        product = strategic_products.iloc[0]
        stats["top_product_title"] = product["title"]
        stats["top_product_source"] = product["source"]

    if "cluster" in eda_df.columns:
        cluster_summary = (
            eda_df.groupby("cluster")["rating_score_imputed"]
            .mean()
            .sort_values(ascending=False)
        )
        if not cluster_summary.empty:
            stats["best_cluster"] = cluster_summary.index[0]
            stats["best_cluster_rating"] = float(cluster_summary.iloc[0])

    return stats


def build_summary(eda_df, benchmark_df=None, strategic_products=None):
    """
    Executive summary ka markdown text banata hai.

    Notebook mein:   display(Markdown(build_summary(...)))
    main.py mein:    print(build_summary(...))
    """
    s = headline_stats(eda_df, benchmark_df, strategic_products)

    lines = ["### Headline Findings"]

    if "top_source" in s:
        lines.append(
            f"- **Marketplace leader by engagement:** {_title(s['top_source'])} "
            f"with average engagement score {s['top_source_engagement']:.2f}"
        )
    if "top_category" in s:
        lines.append(
            f"- **Highest-rated category:** {s['top_category']} "
            f"with average rating {s['top_category_rating']:.2f}"
        )
    if "most_reviewed_brand" in s:
        lines.append(
            f"- **Most review-rich brand:** {s['most_reviewed_brand']} "
            f"with {s['most_reviewed_brand_reviews']:,} total reviews"
        )
    if "anomaly_source" in s:
        lines.append(f"- **Most anomaly-heavy source:** {_title(s['anomaly_source'])}")
    if "best_pocket_source" in s:
        lines.append(
            f"- **Strongest source-category pocket:** {_title(s['best_pocket_source'])} | "
            f"{s['best_pocket_category']} with benchmark score {s['best_pocket_score']:.2f}"
        )
    if "top_product_title" in s:
        lines.append(
            f"- **Top strategic product candidate:** {s['top_product_title']} "
            f"from {_title(s['top_product_source'])}"
        )
    if "best_cluster" in s:
        lines.append(
            f"- **Best-rated segment:** Cluster {s['best_cluster']} "
            f"with average rating {s['best_cluster_rating']:.2f}"
        )

    lines.extend([
        "",
        "### Strategic Priorities",
        "- Prioritize in-stock, high-rating, under-reviewed products for visibility, merchandising, or promotion.",
        "- Audit the highest-anomaly sources and source-category pockets first to catch pricing or catalog irregularities.",
        "- Reuse wording patterns associated with high-engagement listings where they fit the category and marketplace context.",
        "- Track benchmark-pocket movement across future scrapes to monitor improvement or deterioration over time.",
        "",
        "### Project Notes",
        "- The dataset is a scraped catalog snapshot rather than a transactional sales dataset.",
        "- Review volume reflects public social proof and should not be treated as a direct sales measure.",
        "- The clustering, anomaly detection, and propensity modeling layers are exploratory decision-support tools.",
    ])

    return "\n".join(lines)


def _title(value):
    """Source ka naam title-case mein (NaN/None par safe)."""
    return str(value).title() if pd.notna(value) else "N/A"