"""
PRAT Orders & Products - KPI analysis and dashboard
Usage:  python prat_dashboard.py [orders.xlsx] [products.xlsx] [output_dir]
Outputs: dashboard.png, individual charts in charts/, kpis.csv
Requires: pandas, openpyxl, matplotlib, seaborn
"""
import sys, os, re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ORDERS = sys.argv[1] if len(sys.argv) > 1 else "Exercice_PRAT_Orders.xlsx"
PRODUCTS = sys.argv[2] if len(sys.argv) > 2 else "Exercice_PRAT_Products.xlsx"
OUT = sys.argv[3] if len(sys.argv) > 3 else "."
os.makedirs(os.path.join(OUT, "charts"), exist_ok=True)

sns.set_theme(style="whitegrid", font="DejaVu Sans")
PAL = sns.color_palette("deep")
GRADE_ORDER = ["Platinum", "Gold", "Silver", "Bronze", "Iron", "Not graded"]
GRADE_COL = {"Platinum": "#7f8c9b", "Gold": "#e0a800", "Silver": "#b0b7bf",
             "Bronze": "#b8733a", "Iron": "#5a5a5a", "Not graded": "#d9d9d9"}

# ------------------------------------------------------------------ 1. LOAD & CLEAN
o = pd.read_excel(ORDERS)
p = pd.read_excel(PRODUCTS)
o.columns = ["date", "lab", "ptype", "host", "product", "grade", "unit_cost",
             "qty", "country", "legal", "gender", "birth_year"]
p.columns = ["lab", "ptype", "title", "virus", "grade", "shipping"]

def fix_text(s):
    """Repair mojibake (e.g. 'CÃ´te d'Ivoire' -> "Côte d'Ivoire"), strip whitespace."""
    if not isinstance(s, str):
        return s
    try:
        s = s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return re.sub(r"\s+", " ", s).strip()

for df in (o, p):
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].map(fix_text)

short_country = {"United States of America (the)": "USA",
                 "United Kingdom of Great Britain and Northern Ireland (the)": "UK",
                 "Netherlands (the)": "Netherlands", "Czech Republic (the)": "Czech Republic"}
o["country"] = o["country"].replace(short_country)
o["legal"] = o["legal"].replace({
    "University and other higher education organisations": "University",
    "Other Industrial and/or profit Private organisation": "Other private / industry",
    "Other organisation not fitting in one of the above categories": "Other",
    "Small or Medium Enterprise": "SME", "Public research organisation": "Public research org",
    "University / Higher ed": "University"})
o["grade"] = o["grade"].fillna("Not graded")
p["grade"] = p["grade"].fillna("Not graded")
o["host"] = o["host"].fillna("Not specified")
p["ptype"] = p["ptype"].str.replace(" Product", "", regex=False)
short_type = {"Antibody or Hybridoma": "Antibody", "Detection Kit": "Det. Kit"}
o["ptype"] = o["ptype"].replace(short_type)
p["ptype"] = p["ptype"].replace(short_type)
p["shipping"] = p["shipping"].fillna("Not specified").replace({"- 20°C": "-20°C", "+ 4°C": "+4°C"})

o["revenue"] = o["unit_cost"] * o["qty"]          # ASSUMPTION: revenue = announced cost x quantity
o["year"] = o["date"].dt.year
o["month"] = o["date"].dt.to_period("M").dt.to_timestamp()
o["age"] = o["year"] - o["birth_year"]            # age at order time
o["age_group"] = pd.cut(o["age"], [0, 29, 39, 49, 59, 120],
                        labels=["<30", "30-39", "40-49", "50-59", "60+"])
n_dupes = int(o.duplicated().sum())               # same user/product/date: kept (repeat orders)

# Link orders to catalogue (join on product title)
cat = p.drop_duplicates("title")
m = o.merge(cat[["title", "virus", "shipping"]], left_on="product", right_on="title", how="left")
match_rate = m["title"].notna().mean()

# ------------------------------------------------------------------ 2. KPIs
tot_rev = o["revenue"].sum()
by_user_key = o.groupby(["country", "legal", "gender", "birth_year"])  # proxy for a "user"
kpis = {
    "Total enquiries (orders)": len(o),
    "Total units ordered": int(o["qty"].sum()),
    "Total revenue (EUR, cost x qty)": tot_rev,
    "Average order value (EUR)": o["revenue"].mean(),
    "Median order value (EUR)": o["revenue"].median(),
    "Avg units per order": o["qty"].mean(),
    "Distinct products ordered": o["product"].nunique(),
    "Catalogue size (products)": p["title"].nunique(),
    "Catalogue coverage (% products ordered)": o["product"].nunique() / p["title"].nunique(),
    "Countries served": o["country"].nunique(),
    "Estimated distinct users (proxy)": by_user_key.ngroups,
    "Repeat-order share (orders from users with >1 order)": (by_user_key["revenue"].transform("size") > 1).mean(),
    "Share of revenue from top 10 products": o.groupby("product")["revenue"].sum().nlargest(10).sum() / tot_rev,
    "Share of revenue from top lab": o.groupby("lab")["revenue"].sum().max() / tot_rev,
    "Share of orders from non-academic orgs": o["legal"].isin(["SME", "Other private / industry"]).mean(),
    "Share of orders on graded products": (o["grade"] != "Not graded").mean(),
    "Orders YoY growth 2020->2021 (YTD Sep)": np.nan,
    "Orders-to-catalogue match rate (title join)": match_rate,
}
yr = o.groupby("year").size()
# 2021 data stops end-Sep: compare same Jan-Sep window
ytd = lambda y: ((o["year"] == y) & (o["date"].dt.month <= 9)).sum()
kpis["Orders YoY growth 2020->2021 (YTD Sep)"] = ytd(2021) / ytd(2020) - 1
kp = pd.Series(kpis, name="value")
kp.to_csv(os.path.join(OUT, "kpis.csv"))
print(kp.to_string(float_format=lambda x: f"{x:,.2f}"))
print(f"\nData period: {o['date'].min():%Y-%m-%d} -> {o['date'].max():%Y-%m-%d} | duplicate rows: {n_dupes}")

# ------------------------------------------------------------------ 3. CHART FUNCTIONS
def f_trend(ax):
    mm = o.groupby("month").agg(orders=("qty", "size"), revenue=("revenue", "sum"))
    mm = mm.reindex(pd.date_range(mm.index.min(), mm.index.max(), freq="MS"), fill_value=0)
    ax.bar(mm.index, mm["orders"], width=25, color=PAL[0], alpha=.85, label="Orders")
    ax.set_ylabel("Orders / month")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(mm.index, mm["revenue"].rolling(3, min_periods=1).mean(), color=PAL[3], lw=2, label="Revenue (3-mo avg)")
    ax2.set_ylabel("Revenue EUR")
    ax.set_title("Monthly orders & revenue trend")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)

def f_year(ax):
    d = o.groupby("year").agg(orders=("qty", "size"), revenue=("revenue", "sum"))
    ax.bar(d.index.astype(str), d["orders"], color=PAL[0])
    for i, v in enumerate(d["orders"]): ax.text(i, v + 1, v, ha="center", fontsize=8)
    ax.set_title("Orders per year (2021 = to end Sep)"); ax.set_ylabel("Orders")

def f_lab(ax):
    d = o.groupby("lab").agg(orders=("qty", "size"), revenue=("revenue", "sum"), aov=("revenue", "mean"))
    x = np.arange(len(d)); w = .38
    ax.bar(x - w/2, d["orders"], w, color=PAL[0], label="Orders")
    ax.set_xticks(x); ax.set_xticklabels("Lab " + d.index); ax.set_ylabel("Orders")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.bar(x + w/2, d["revenue"] / 1000, w, color=PAL[2], label="Revenue (k EUR)")
    ax2.set_ylabel("Revenue k EUR")
    ax.set_ylim(0, d["orders"].max() * 1.3); ax2.set_ylim(0, d["revenue"].max() / 1000 * 1.3)
    ax.set_title("Orders & revenue by provider lab")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8)

def f_type_rev(ax):
    d = o.groupby("ptype").agg(orders=("qty", "size"), revenue=("revenue", "sum")).sort_values("revenue")
    ax.barh(d.index, d["revenue"] / 1000, color=PAL[1])
    for i, (r, n) in enumerate(zip(d["revenue"], d["orders"])):
        ax.text(r / 1000 + 1, i, f"{r/tot_rev:.0%}  ({n} orders)", va="center", fontsize=8)
    ax.set_xlim(0, d["revenue"].max() / 1000 * 1.35)
    ax.set_title("Revenue by product type (k EUR)")

def f_type_aov(ax):
    d = o.groupby("ptype")["revenue"].mean().sort_values()
    ax.barh(d.index, d.values, color=PAL[4])
    for i, v in enumerate(d.values): ax.text(v + 20, i, f"{v:,.0f}", va="center", fontsize=8)
    ax.set_xlim(0, d.max() * 1.15)
    ax.set_title("Average order value by product type (EUR)")

def f_country(ax):
    d = o["country"].value_counts().head(10).sort_values()
    ax.barh(d.index, d.values, color=PAL[0])
    for i, v in enumerate(d.values): ax.text(v + .3, i, v, va="center", fontsize=8)
    ax.set_title(f"Top 10 countries by orders ({o['country'].nunique()} total)")

def f_legal(ax):
    d = o["legal"].value_counts()
    ax.pie(d.values, labels=None, autopct="%1.0f%%", startangle=90, colors=PAL, pctdistance=.8,
           wedgeprops=dict(width=.45, edgecolor="white"), textprops=dict(fontsize=8))
    ax.legend(d.index, loc="upper center", bbox_to_anchor=(.5, -.02), ncol=2, fontsize=8, frameon=False)
    ax.set_title("Customer segment (legal status)")

def f_seg_rev(ax):
    d = o.groupby("legal")["revenue"].mean().sort_values()
    ax.barh(d.index, d.values, color=PAL[5])
    for i, v in enumerate(d.values): ax.text(v + 10, i, f"{v:,.0f}", va="center", fontsize=8)
    ax.set_xlim(0, d.max() * 1.15)
    ax.set_title("Average order value by segment (EUR)")

def f_grade(ax):
    d = o["grade"].value_counts().reindex(GRADE_ORDER).dropna()
    ax.bar(d.index, d.values, color=[GRADE_COL[g] for g in d.index], edgecolor="grey")
    for i, v in enumerate(d.values): ax.text(i, v + 1, int(v), ha="center", fontsize=8)
    ax.set_title("Orders by product grading"); ax.tick_params(axis="x", labelrotation=30)

def f_cat_vs_orders(ax):
    c = p["ptype"].value_counts(); od = o["ptype"].value_counts()
    d = pd.DataFrame({"Catalogue share": c / c.sum(), "Orders share": od / od.sum()}).fillna(0)
    d = d.sort_values("Catalogue share")
    d.plot.barh(ax=ax, color=[PAL[7], PAL[0]], width=.75)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_title("Catalogue mix vs demand mix"); ax.legend(fontsize=8); ax.set_ylabel("")

def f_pareto(ax):
    d = o.groupby("product")["revenue"].sum().sort_values(ascending=False)
    cum = d.cumsum() / d.sum() * 100
    ax.plot(range(1, len(d) + 1), cum.values, color=PAL[3], lw=2)
    ax.axhline(80, ls="--", color="grey", lw=1)
    n80 = int((cum < 80).sum() + 1)
    ax.axvline(n80, ls="--", color="grey", lw=1)
    ax.text(n80 + 2, 40, f"{n80} products ({n80/len(d):.0%})\n= 80% of revenue", fontsize=8)
    ax.set_xlabel("Products ranked by revenue"); ax.set_ylabel("Cumulative % revenue")
    ax.set_title("Pareto: revenue concentration")

def f_top_products(ax):
    d = o.groupby("product").size().sort_values().tail(10)
    labels = [t if len(t) < 45 else t[:42] + "..." for t in d.index]
    ax.barh(labels, d.values, color=PAL[2])
    ax.set_title("Top 10 most-ordered products"); ax.tick_params(axis="y", labelsize=7)

def f_age_gender(ax):
    d = o.groupby(["age_group", "gender"], observed=True).size().unstack(fill_value=0)
    d.plot.bar(ax=ax, color=[PAL[3], PAL[0]], width=.8)
    ax.set_title("Orders by age group & gender"); ax.set_xlabel(""); ax.tick_params(axis="x", labelrotation=0)
    ax.legend(fontsize=8)

def f_ship(ax):
    d = m["shipping"].value_counts()
    ax.bar(d.index, d.values, color=PAL[9]); ax.tick_params(axis="x", labelrotation=25)
    ax.set_title(f"Shipping conditions of ordered products\n(matched {match_rate:.0%} of orders to catalogue)")

def f_heat(ax):
    d = o.pivot_table(index="ptype", columns="lab", values="revenue", aggfunc="sum", fill_value=0) / 1000
    sns.heatmap(d, annot=True, fmt=".0f", cmap="YlGnBu", cbar=False, ax=ax)
    ax.set_title("Revenue (k EUR): product type x lab"); ax.set_xlabel("Lab"); ax.set_ylabel("")

def f_box(ax):
    order = o.groupby("ptype")["revenue"].median().sort_values().index
    sns.boxplot(data=o, y="ptype", x="revenue", order=order, ax=ax, color=PAL[0], fliersize=2)
    ax.set_xscale("log"); ax.set_title("Order value distribution (log scale)"); ax.set_ylabel(""); ax.set_xlabel("EUR")

CHARTS = {"01_trend": f_trend, "02_year": f_year, "03_lab": f_lab, "04_type_revenue": f_type_rev,
          "05_type_aov": f_type_aov, "06_country": f_country, "07_segment": f_legal,
          "08_segment_aov": f_seg_rev, "09_grade": f_grade, "10_catalogue_vs_demand": f_cat_vs_orders,
          "11_pareto": f_pareto, "12_top_products": f_top_products, "13_age_gender": f_age_gender,
          "14_shipping": f_ship, "15_heatmap": f_heat, "16_boxplot": f_box}

# individual charts
for name, fn in CHARTS.items():
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fn(ax); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "charts", f"{name}.png"), dpi=130); plt.close(fig)

# ------------------------------------------------------------------ 4. DASHBOARD
fig = plt.figure(figsize=(22, 27), facecolor="#f5f6f8")
gs = fig.add_gridspec(7, 4, height_ratios=[.5, 1, 1, 1, 1, 1, 1], hspace=.5, wspace=.55)
fig.suptitle("PRAT Virus Catalogue - Orders Dashboard", fontsize=26, fontweight="bold", y=.975)
fig.text(.5, .957, f"Orders {o['date'].min():%b %Y} - {o['date'].max():%b %Y}  |  {len(o)} enquiries  |  "
         f"{p['title'].nunique()} catalogue products  |  revenue = announced academic cost x quantity",
         ha="center", fontsize=12, color="#555")

cards = [("Orders", f"{len(o):,}"), ("Revenue", f"€{tot_rev/1000:,.0f}k"), ("Avg order value", f"€{o['revenue'].mean():,.0f}"),
         ("Countries", f"{o['country'].nunique()}"), ("Catalogue coverage", f"{kpis['Catalogue coverage (% products ordered)']:.0%}"),
         ("Top-10 product share", f"{kpis['Share of revenue from top 10 products']:.0%}"),
         ("Orders YoY (YTD Sep)", f"{kpis['Orders YoY growth 2020->2021 (YTD Sep)']:+.0%}"),
         ("Repeat-order share", f"{kpis['Repeat-order share (orders from users with >1 order)']:.0%}")]
cgs = gs[0, :].subgridspec(2, 4, hspace=.3, wspace=.15)
for i, (t, v) in enumerate(cards):
    a = fig.add_subplot(cgs[i // 4, i % 4]); a.set_facecolor("white")
    a.set_xticks([]); a.set_yticks([]); a.grid(False)
    for s in a.spines.values(): s.set_color("#d0d4da")
    a.text(.5, .62, v, ha="center", va="center", fontsize=24, fontweight="bold", color="#1f4e79")
    a.text(.5, .18, t, ha="center", va="center", fontsize=11, color="#555")

layout = [
    (1, slice(0, 3), f_trend), (1, 3, f_year),
    (2, slice(0, 2), f_type_rev), (2, 2, f_type_aov), (2, 3, f_lab),
    (3, slice(0, 2), f_country), (3, 2, f_legal), (3, 3, f_seg_rev),
    (4, slice(0, 2), f_pareto), (4, slice(2, 4), f_top_products),
    (5, slice(0, 2), f_cat_vs_orders), (5, 2, f_grade), (5, 3, f_age_gender),
    (6, slice(0, 2), f_heat), (6, 2, f_box), (6, 3, f_ship),
]
for r, c, fn in layout:
    ax = fig.add_subplot(gs[r, c]); fn(ax)
    ax.title.set_fontsize(11)
fig.savefig(os.path.join(OUT, "dashboard.png"), dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)
print("\nSaved dashboard.png, kpis.csv and charts/ in", os.path.abspath(OUT))
