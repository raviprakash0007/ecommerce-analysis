import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns



def show_plot(fig, height=500, width=1400):
   
    import plotly.io as pio
    from IPython.display import HTML, Image, display

    fig.update_layout(height=height, template="plotly_white")
    config = {"responsive": True, "displaylogo": False}

    try:
        png_bytes = pio.to_image(fig, format="png", width=width, height=height, scale=2)
        display(Image(data=png_bytes))
        return
    except Exception:
        pass

    try:
        fig.show(renderer=pio.renderers.default, config=config)
        return
    except Exception:
        pass

    display(HTML(fig.to_html(full_html=False, include_plotlyjs=True, config=config)))


def _finish(fig, show):
    plt.tight_layout()
    if show:
        plt.show()
    return fig


def _style_axis(ax, title, xlabel, ylabel, grid_axis="both"):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=grid_axis, alpha=0.25)
    ax.set_axisbelow(True)



def plot_visual_audit(tables, show=True):
   
    missing_df = tables["missing_df"]
    source_missing = tables["source_missing"]
    category_source_counts = tables["category_source_counts"]
    availability_mix = tables["availability_mix"]

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    colors = sns.color_palette("magma", n_colors=len(missing_df))
    axes[0, 0].bar(missing_df["column"], missing_df["missing_pct"], color=colors)
    for idx, row in missing_df.iterrows():
        axes[0, 0].text(idx, row["missing_pct"] + 1, f"{int(row['missing_rows'])}",
                        ha="center", va="bottom", fontsize=9)
    _style_axis(axes[0, 0], "Missingness by column (%)", "Column", "Missing %", "y")
    axes[0, 0].tick_params(axis="x", rotation=40)

    if not source_missing.empty:
        sns.heatmap(source_missing, annot=True, fmt=".1f", cmap="RdYlBu_r",
                    linewidths=0.4, ax=axes[0, 1])
        axes[0, 1].set_title("Missingness by source for key fields (%)")
        axes[0, 1].set_xlabel("Field")
        axes[0, 1].set_ylabel("Source")
    else:
        axes[0, 1].axis("off")

    sns.heatmap(category_source_counts, annot=True, fmt="d", cmap="viridis",
                linewidths=0.4, ax=axes[1, 0])
    axes[1, 0].set_title("Product count by category and source")
    axes[1, 0].set_xlabel("Source")
    axes[1, 0].set_ylabel("Category")

    availability_mix.plot(kind="bar", stacked=True, colormap="viridis",
                          ax=axes[1, 1], width=0.75)
    _style_axis(axes[1, 1], "Availability mix by source (%)", "Source", "Share %", "y")
    axes[1, 1].tick_params(axis="x", rotation=20)
    axes[1, 1].legend(title="Availability", loc="upper left", bbox_to_anchor=(1.02, 1.0))

    return _finish(fig, show)



def plot_price_vs_rating(eda_df, show=True):
   
    currencies = sorted(eda_df["currency"].dropna().unique().tolist())
    fig, axes = plt.subplots(1, len(currencies), figsize=(6 * len(currencies), 6), sharey=True)
    if len(currencies) == 1:
        axes = [axes]

    for ax, currency in zip(axes, currencies):
        subset = eda_df[eda_df["currency"] == currency]
        sns.scatterplot(
            data=subset, x="price_current", y="rating_score_imputed",
            hue="category", size="reviews_size", sizes=(20, 600), alpha=0.65,
            palette="tab10", ax=ax, legend=(currency == currencies[-1]),
        )
        ax.set_xscale("log")
        ax.set_ylim(2.4, 5.05)
        _style_axis(ax, f"Currency = {currency}", "price_current", "rating_score_imputed")

    handles, labels = axes[-1].get_legend_handles_labels()
    if handles:
        axes[-1].legend(handles, labels, bbox_to_anchor=(1.02, 1.0),
                        loc="upper left", title="category / reviews_size")
    fig.suptitle("Price vs rating by currency (bubble size = review volume)", y=1.02, fontsize=18)
    return _finish(fig, show)


def plot_discount_penetration(penetration, show=True):
    fig = plt.figure(figsize=(12, 6))
    sns.heatmap(penetration, annot=True, fmt=".1f", cmap="magma", linewidths=0.4)
    plt.title("Discount penetration by category and source (%)")
    plt.xlabel("Source")
    plt.ylabel("Category")
    return _finish(fig, show)


def plot_brand_engagement(brand_rank, min_products=8, show=True):
   
    span = brand_rank["avg_rating"].max() - brand_rank["avg_rating"].min() + 1e-9
    colors = plt.cm.viridis((brand_rank["avg_rating"] - brand_rank["avg_rating"].min()) / span)

    fig = plt.figure(figsize=(12, 8))
    plt.barh(brand_rank["brand"], brand_rank["avg_engagement"], color=colors)
    for _, row in brand_rank.iterrows():
        plt.text(row["avg_engagement"] + 0.2, row["brand"], f"{int(row['products'])}",
                 va="center", fontsize=10)
    plt.title(f"Most engaging brands (minimum {min_products} products; label = product count)")
    plt.xlabel("avg_engagement")
    plt.ylabel("brand")
    plt.grid(axis="x", alpha=0.25)
    plt.gca().set_axisbelow(True)
    return _finish(fig, show)



def plot_text_signals(res, show=True):
    top_unigrams = res["top_unigrams"]
    top_bigrams = res["top_bigrams"]
    overindexed = res["overindexed_terms"]
    style = res["style_summary"]

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    axes[0, 0].barh(top_unigrams["term"], top_unigrams["frequency"],
                    color=sns.color_palette("crest", n_colors=max(len(top_unigrams), 1)))
    _style_axis(axes[0, 0], "Most common title unigrams", "Frequency", "", "x")

    axes[0, 1].barh(top_bigrams["term"], top_bigrams["frequency"],
                    color=sns.color_palette("flare", n_colors=max(len(top_bigrams), 1)))
    _style_axis(axes[0, 1], "Most common title bigrams", "Frequency", "", "x")

    axes[1, 0].barh(overindexed["term"], overindexed["engagement_lift"],
                    color=sns.color_palette("viridis", n_colors=max(len(overindexed), 1)))
    axes[1, 0].axvline(1.0, linestyle="--", color="#7c7c7c", linewidth=1)
    _style_axis(axes[1, 0], "Terms over-indexed in high-engagement titles",
                "Lift vs low-engagement titles", "", "x")

    if not style.empty:
        sns.scatterplot(data=style, x="avg_title_words", y="avg_engagement",
                        size="products", hue="source", palette="viridis",
                        sizes=(80, 700), alpha=0.85, ax=axes[1, 1])
        for _, row in style.iterrows():
            axes[1, 1].text(row["avg_title_words"] + 0.03, row["avg_engagement"] + 0.01,
                            row["category"], fontsize=8)
        sns.move_legend(axes[1, 1], "lower right", frameon=True, title="Source")
    _style_axis(axes[1, 1], "Title verbosity vs engagement by source-category mix",
                "Average title word count", "Average engagement score")

    return _finish(fig, show)



def plot_benchmark(bench, show=True):
    benchmark_df = bench["benchmark_df"]
    strongest = bench["strongest"]

    fig, axes = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={"width_ratios": [1.3, 1]})
    sns.heatmap(bench["pivot"], annot=True, fmt=".2f", cmap="RdYlGn", center=0,
                linewidths=0.5, ax=axes[0])
    axes[0].set_title("Benchmark score by source and category")
    axes[0].set_xlabel("Source")
    axes[0].set_ylabel("Category")

    sns.scatterplot(data=benchmark_df, x="in_stock_share", y="avg_engagement",
                    hue="source", size="products", sizes=(80, 700),
                    palette="viridis", alpha=0.85, ax=axes[1])
    for _, row in strongest.head(10).iterrows():
        axes[1].text(row["in_stock_share"] + 0.3, row["avg_engagement"] + 0.03,
                     row["category"], fontsize=8)
    _style_axis(axes[1], "Stock health vs engagement by source-category pocket",
                "In-stock share %", "Average engagement score")
    sns.move_legend(axes[1], "lower right", frameon=True, title="Source")

    return _finish(fig, show)



def plot_freshness(fresh, show=True):
    if not fresh["available"]:
        print(fresh["readout"])
        return None

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    sns.barplot(data=fresh["day_counts"], x="scrape_day", y="products",
                hue="scrape_day", palette="viridis", legend=False, ax=axes[0, 0])
    _style_axis(axes[0, 0], "Products by scrape day", "Scrape day", "Product count", "y")
    axes[0, 0].tick_params(axis="x", rotation=30)

    sns.heatmap(fresh["hour_heatmap"], cmap="mako", linewidths=0.3, ax=axes[0, 1])
    axes[0, 1].set_title("Scrape activity by source and hour")
    axes[0, 1].set_xlabel("Scrape hour")
    axes[0, 1].set_ylabel("Source")

    sns.boxplot(data=fresh["box_data"], x="source", y="days_since_latest_scrape",
                hue="source", palette="Set2", legend=False, ax=axes[1, 0])
    _style_axis(axes[1, 0], "Freshness distribution by source", "Source",
                "Days since latest scrape")
    axes[1, 0].tick_params(axis="x", rotation=20)

    sns.heatmap(fresh["recency_mix"], annot=True, fmt=".1f", cmap="YlGnBu",
                linewidths=0.3, ax=axes[1, 1])
    axes[1, 1].set_title("Recency mix by source (%)")
    axes[1, 1].set_xlabel("Recency bucket")
    axes[1, 1].set_ylabel("Source")

    return _finish(fig, show)



def plot_opportunity_map(opp, show=True):
    strategic_df = opp["strategic_df"]

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    sns.scatterplot(data=strategic_df, x="propensity_for_opportunity", y="engagement_score",
                    hue="cluster_label", size="opportunity_score", sizes=(20, 400),
                    alpha=0.70, palette="viridis", ax=axes[0])
    axes[0].axvline(opp["x_ref"], linestyle="--", color="#7c7c7c", linewidth=1)
    axes[0].axhline(opp["y_ref"], linestyle="--", color="#7c7c7c", linewidth=1)
    for _, row in opp["top_labels"].iterrows():
        axes[0].text(row["high_review_propensity"] + 0.003, row["engagement_score"] + 0.03,
                     row["brand"], fontsize=8)
    _style_axis(axes[0], "Opportunity map: review propensity vs engagement",
                "Predicted high-review propensity", "Engagement score")
    sns.move_legend(axes[0], "lower right", frameon=True, title="Cluster")

    sns.barplot(data=opp["source_opportunity"], x="avg_opportunity", y="source",
                hue="source", palette="viridis", legend=False, ax=axes[1])
    _style_axis(axes[1], "Average opportunity score by source",
                "Average opportunity score", "Source", "x")

    return _finish(fig, show)