import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display

try:
    import ipywidgets as widgets
except ImportError:  
    widgets = None

ALL = "All"

GROUP_OPTIONS = ["brand", "category", "source", "availability", "price_tier_within_currency"]
METRIC_OPTIONS = [
    "Product count", "Average rating", "Average discount",
    "Median price", "Average engagement",
]

TABLE_COLS = [
    "title", "brand", "source", "category", "currency", "price_current",
    "rating_score_imputed", "reviews_count", "discount_pct_filled",
    "availability", "price_tier_within_currency", "engagement_score",
]

STYLES = """
<style>
.slice-kpi-grid { display:grid; grid-template-columns:repeat(3, minmax(180px, 1fr)); gap:12px; margin:8px 0 18px 0; }
.slice-kpi-card { border:1px solid #e5e7eb; border-radius:12px; background:#fafafa; padding:12px 14px; }
.slice-kpi-label { font-size:12px; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; }
.slice-kpi-value { font-size:28px; font-weight:700; color:#223b61; margin-top:6px; }
.slice-status { margin:10px 0 14px 0; padding:10px 12px; border-left:4px solid #f59e0b; background:#fff7ed; color:#7c2d12; font-size:14px; }
.slice-table-wrap { max-height:520px; overflow:auto; border:1px solid #e5e7eb; border-radius:10px; margin-top:8px; }
.slice-table { border-collapse:collapse; width:100%; font-size:13px; }
.slice-table th, .slice-table td { padding:8px 10px; border-bottom:1px solid #e5e7eb; text-align:left; vertical-align:top; }
.slice-table th { background:#f8fafc; position:sticky; top:0; z-index:1; }
.slice-section-title { margin:16px 0 8px 0; font-size:24px; font-weight:700; color:#111827; }
</style>
"""


def _fmt(value, decimals=2, integer=False):
    if integer:
        return f"{int(round(value)):,}"
    return f"{value:,.{decimals}f}"


def _tier_options(eda_df):
    """Price tier ke options (categorical ho ya plain text, dono chalega)."""
    col = eda_df["price_tier_within_currency"].dropna()
    if hasattr(col, "cat"):
        return [str(x) for x in col.cat.categories.tolist()]
    return sorted(col.astype(str).unique().tolist())


def launch_dashboard(eda_df):
    """
    Dashboard banake dikhata hai. Widgets ka dict return karta hai
    (test ya customization ke liye).
    """
    if widgets is None:
        print("ipywidgets is not available in this environment. Run: pip install ipywidgets")
        return None

    df = eda_df.copy()
    if "has_discount" not in df.columns:
        df["has_discount"] = (df["discount_pct_filled"] > 0).astype(int)

    # ---- Widgets -----------------------------------------------------------
    wide = widgets.Layout(width="23%")
    compact = widgets.Layout(width="17%")

    def dropdown(label, column, layout):
        return widgets.Dropdown(
            options=[ALL] + sorted(df[column].dropna().unique().tolist()),
            value=ALL, description=label, layout=layout,
        )

    source_w = dropdown("Source:", "source", wide)
    category_w = dropdown("Category:", "category", wide)
    currency_w = dropdown("Currency:", "currency", wide)
    availability_w = dropdown("Avail:", "availability", wide)
    tier_w = widgets.Dropdown(
        options=[ALL] + _tier_options(df), value=ALL,
        description="Price tier:", layout=compact,
    )
    group_w = widgets.Dropdown(
        options=GROUP_OPTIONS, value="brand", description="Group by:", layout=compact
    )
    metric_w = widgets.Dropdown(
        options=METRIC_OPTIONS, value="Product count", description="Metric:", layout=compact
    )
    top_n_w = widgets.BoundedIntText(
        value=12, min=5, max=25, step=1, description="Top N:",
        layout=widgets.Layout(width="130px"),
    )
    min_reviews_w = widgets.IntSlider(
        value=0, min=0, max=int(df["reviews_count"].max()), step=25,
        description="Min reviews:", continuous_update=False,
        layout=widgets.Layout(width="95%"),
    )
    rating_w = widgets.FloatRangeSlider(
        value=[2.5, 5.0], min=2.5, max=5.0, step=0.1, description="Rating:",
        continuous_update=False, layout=widgets.Layout(width="95%"),
    )
    reset_btn = widgets.Button(
        description="Clear slicers", button_style="warning", icon="refresh",
        layout=widgets.Layout(width="170px", height="38px"),
    )

    status_html = widgets.HTML()
    kpi_html = widgets.HTML()
    chart_title_html = widgets.HTML()
    chart_out = widgets.Output()
    table_html = widgets.HTML()
    state = {"busy": False}

    # ---- Logic -------------------------------------------------------------
    def filtered_slice():
        out = df
        if source_w.value != ALL:
            out = out[out["source"] == source_w.value]
        if category_w.value != ALL:
            out = out[out["category"] == category_w.value]
        if currency_w.value != ALL:
            out = out[out["currency"] == currency_w.value]
        if availability_w.value != ALL:
            out = out[out["availability"] == availability_w.value]
        if tier_w.value != ALL:
            out = out[out["price_tier_within_currency"].astype(str) == tier_w.value]

        out = out[
            (out["reviews_count"] >= min_reviews_w.value)
            & (out["rating_score_imputed"] >= rating_w.value[0])
            & (out["rating_score_imputed"] <= rating_w.value[1])
        ]
        return out.copy()

    def kpi_cards(f):
        cards = [
            ("Rows", _fmt(len(f), integer=True)),
            ("Unique brands", _fmt(f["brand"].nunique(), integer=True)),
            ("Median price", _fmt(float(f["price_current"].median()))),
            ("Average rating", _fmt(float(f["rating_score_imputed"].mean()))),
            ("Discounted share %", _fmt(float(f["has_discount"].mean() * 100))),
            ("In-stock share %", _fmt(float(f["in_stock_flag"].mean() * 100))),
        ]
        html = "".join(
            f"<div class='slice-kpi-card'><div class='slice-kpi-label'>{label}</div>"
            f"<div class='slice-kpi-value'>{value}</div></div>"
            for label, value in cards
        )
        return f"<div class='slice-section-title'>Slice KPIs</div><div class='slice-kpi-grid'>{html}</div>"

    def ranked_table(f):
        g = group_w.value
        metric = metric_w.value
        if metric == "Product count":
            ranked = f.groupby(g).size().reset_index(name="metric_value")
        elif metric == "Average rating":
            ranked = f.groupby(g)["rating_score_imputed"].mean().reset_index(name="metric_value")
        elif metric == "Average discount":
            ranked = f.groupby(g)["discount_pct_filled"].mean().reset_index(name="metric_value")
        elif metric == "Median price":
            ranked = f.groupby(g)["price_current"].median().reset_index(name="metric_value")
        else:
            ranked = f.groupby(g)["engagement_score"].mean().reset_index(name="metric_value")

        ranked = (
            ranked.sort_values("metric_value", ascending=False)
            .head(int(top_n_w.value))
            .sort_values("metric_value")
        )
        ranked[g] = ranked[g].astype(str)
        ranked["metric_value"] = ranked["metric_value"].round(2)
        return ranked

    def draw_charts(f, ranked, group_label):
        g = group_w.value
        fig, axes = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [2.4, 1]})

        values = ranked["metric_value"].values
        labels = ranked[g].tolist()
        colors = ["#4c78a8"] if len(values) == 1 else sns.color_palette("viridis", n_colors=len(values))

        axes[0].barh(labels, values, color=colors)
        offset = max(values) * 0.015 if max(values) > 0 else 0.05
        for i, val in enumerate(values):
            text = f"{int(round(val)):,}" if abs(val - round(val)) < 1e-9 else f"{val:,.2f}"
            axes[0].text(val + offset, i, text, va="center", fontsize=10)
        axes[0].set_xlabel(metric_w.value)
        axes[0].set_ylabel(group_label)
        axes[0].grid(axis="x", alpha=0.25)
        axes[0].set_axisbelow(True)
        axes[0].set_title("Current slice ranking", fontsize=13)

        mix = f["availability"].value_counts().reindex(["in_stock", "limited", "out_of_stock"]).fillna(0)
        mix = mix[mix > 0]
        if mix.empty:
            axes[1].text(0.5, 0.5, "No availability mix to show", ha="center", va="center")
            axes[1].axis("off")
        else:
            _, _, autotexts = axes[1].pie(
                mix.values,
                labels=mix.index.str.replace("_", " "),
                autopct="%1.1f%%",
                startangle=90,
                colors=["#4c78a8", "#f58518", "#54a24b"][: len(mix)],
                wedgeprops={"width": 0.45, "edgecolor": "white"},
            )
            for t in autotexts:
                t.set_fontsize(10)
            axes[1].set_title("Availability mix", fontsize=13)

        sns.despine(left=False, bottom=False)
        plt.tight_layout()
        plt.show()

    def products_table(f):
        cols = [c for c in TABLE_COLS if c in f.columns]
        table = (
            f[cols]
            .sort_values(["engagement_score", "reviews_count"], ascending=[False, False])
            .head(20)
            .reset_index(drop=True)
            .copy()
        )
        for col in ["price_current", "rating_score_imputed", "discount_pct_filled", "engagement_score"]:
            if col in table.columns:
                table[col] = table[col].round(2)
        return (
            "<div class='slice-section-title'>Top products in the current slice</div>"
            "<div class='slice-table-wrap'>"
            + table.to_html(index=False, classes="slice-table")
            + "</div>"
        )

    def render(_=None):
        if state["busy"]:
            return

        f = filtered_slice()
        chart_out.clear_output(wait=True)

        if f.empty:
            status_html.value = "<div class='slice-status'>No products match the current slicer combination.</div>"
            kpi_html.value = chart_title_html.value = table_html.value = ""
            return

        status_html.value = (
            f"<div class='slice-status'>Showing <b>{len(f):,}</b> rows, "
            f"<b>{f['brand'].nunique():,}</b> brands, and price median "
            f"<b>{_fmt(float(f['price_current'].median()))}</b> for the current slice.</div>"
        )
        kpi_html.value = kpi_cards(f)

        ranked = ranked_table(f)
        group_label = group_w.value.replace("_", " ").title()
        chart_title_html.value = (
            f"<div class='slice-section-title'>{metric_w.value} by {group_label}</div>"
        )
        with chart_out:
            draw_charts(f, ranked, group_label)

        table_html.value = products_table(f)

    def reset(_):
        state["busy"] = True  # reset ke dauran baar-baar render na ho
        source_w.value = category_w.value = currency_w.value = ALL
        availability_w.value = tier_w.value = ALL
        group_w.value = "brand"
        metric_w.value = "Product count"
        top_n_w.value = 12
        min_reviews_w.value = 0
        rating_w.value = (2.5, 5.0)
        state["busy"] = False
        render()

    controls = [
        source_w, category_w, currency_w, availability_w, tier_w,
        group_w, metric_w, top_n_w, min_reviews_w, rating_w,
    ]
    for control in controls:
        control.observe(render, names="value")
    reset_btn.on_click(reset)

    # ---- Layout ------------------------------------------------------------
    display(widgets.HTML(STYLES))
    display(widgets.HBox([source_w, category_w, currency_w, availability_w]))
    display(widgets.HBox([tier_w, group_w, metric_w, top_n_w]))
    display(widgets.VBox([min_reviews_w, rating_w]))
    display(reset_btn)
    display(status_html, kpi_html, chart_title_html, chart_out, table_html)

    render()

    return {
        "filters": {
            "source": source_w, "category": category_w, "currency": currency_w,
            "availability": availability_w, "price_tier": tier_w,
        },
        "group": group_w,
        "metric": metric_w,
        "top_n": top_n_w,
        "min_reviews": min_reviews_w,
        "rating": rating_w,
        "reset": reset_btn,
    }