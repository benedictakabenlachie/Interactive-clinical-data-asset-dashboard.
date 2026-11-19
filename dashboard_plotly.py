"""Clinical data traceability dashboard (pandas + Plotly).
Run:  pip install pandas plotly openpyxl  &&  python dashboard_plotly.py
Reads clinical_data_asset_inventory.xlsx (sheet 'Inventory') and writes dashboard_plotly.html. All data are synthetic."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

df = pd.read_excel("clinical_data_asset_inventory.xlsx", sheet_name="Inventory")
n = len(df)
df["Duplicate"] = df.duplicated("Content hash", keep=False)
kpi = {
    "Total assets": n,
    "% available": round((df["Status"] == "Available").mean() * 100, 1),
    "Missing / inaccessible": int((df["Status"] != "Available").sum()),
    "Duplicated records": int(df.duplicated("Content hash").sum()),
    "No owner": int(df["Owner"].isna().sum()),
    "Documentation score %": round(((df["Documentation"] == "Complete").sum() + 0.5 * (df["Documentation"] == "Partial").sum()) / n * 100, 1),
}
fig = make_subplots(rows=3, cols=6, specs=[[{"type": "indicator"}] * 6, [{"type": "xy", "colspan": 3}, None, None, {"type": "domain", "colspan": 3}, None, None], [{"type": "table", "colspan": 6}, None, None, None, None, None]],
                    row_heights=[0.15, 0.4, 0.45], subplot_titles=("", "", "", "", "", "", "Asset status by stage", "Documentation completeness"))
for i, (k, v) in enumerate(kpi.items()):
    fig.add_trace(go.Indicator(mode="number", value=v, title={"text": k, "font": {"size": 13}}), row=1, col=i + 1)
order = ["Source data", "SDTM datasets", "Analysis (ADaM + SAS)", "Statistical outputs", "Clinical evidence"]
colors = {"Available": "#1A8C93", "Inaccessible": "#F2A541", "Missing": "#C8553D"}
ct = pd.crosstab(df["Stage"], df["Status"]).reindex(order).fillna(0)
for status in ct.columns:
    fig.add_trace(go.Bar(x=ct.index, y=ct[status], name=status, marker_color=colors.get(status)), row=2, col=1)
dc = df["Documentation"].value_counts()
fig.add_trace(go.Pie(labels=dc.index, values=dc.values, hole=0.55, marker_colors=["#1A8C93", "#F2A541", "#C8553D"]), row=2, col=4)
ex = df[(df["Status"] != "Available") | df["Duplicate"] | df["Owner"].isna()]
fig.add_trace(go.Table(header=dict(values=["ID", "Asset", "Stage", "Status", "Owner", "Duplicate"]),
                       cells=dict(values=[ex["Asset ID"], ex["Asset"], ex["Stage"], ex["Status"], ex["Owner"].fillna("(none)"), ex["Duplicate"]])), row=3, col=1)
fig.update_layout(barmode="stack", title="GLUCOTRACK-X (fictional): clinical data traceability", height=900, template="plotly_white")
fig.write_html("dashboard_plotly.html")
print(kpi)
