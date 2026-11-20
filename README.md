# PRAT Virus Catalogue: Orders Analysis & Dashboard

Python analysis of a virus biobank catalogue and its customer orders. `prat_dashboard.py` cleans the raw Excel data, links orders to the catalogue, computes 18 KPIs and generates a one-page dashboard plus 16 individual charts.

![Dashboard](outputs/dashboard.png)

## Datasets

| File | Content | Size |
|---|---|---|
| `Exercice_PRAT_Orders.xlsx` | Customer enquiries (May 2016 to Sep 2021): date, provider lab, product type, host, product title, grading, announced cost, quantity, country, organisation type, gender, birth year | 340 rows |
| `Exercice_PRAT_Products.xlsx` | Catalogue: provider lab, product type, title, virus, grading, shipping conditions | 462 rows (456 unique titles) |

## Quick start

```bash
pip install pandas openpyxl matplotlib seaborn
python scripts/prat_dashboard.py data/Exercice_PRAT_Orders.xlsx data/Exercice_PRAT_Products.xlsx outputs
```

Arguments are optional and positional: orders file, products file, output folder. Defaults are the two file names above in the current directory, and the current directory for output. The command above writes everything into `outputs/`.

**Outputs (in `outputs/`):** `dashboard.png`, `kpis.csv` and `charts/*.png`. KPIs are also printed to the console.

## What the script does

1. **Load and clean**
   - Renames columns to short names.
   - Repairs garbled text (e.g. `CÃ´te d'Ivoire` becomes `Côte d'Ivoire`) and trims whitespace.
   - Shortens labels (e.g. `United States of America (the)` becomes `USA`, `Small or Medium Enterprise` becomes `SME`, `Antibody or Hybridoma` becomes `Antibody`).
   - Fills missing grading with `Not graded` and missing host or shipping with `Not specified`.
   - Derives revenue (cost x quantity), year, month, age at order and age group.
2. **Check quality:** counts exact duplicate rows (12, kept as repeat orders) and joins orders to the catalogue on product title (100% match).
3. **Compute KPIs** and save them to `kpis.csv`.
4. **Plot** 16 charts individually (`charts/`) and assemble them into the dashboard.

## KPIs (`outputs/kpis.csv`)

| KPI | Value |
|---|---|
| Total orders | 340 |
| Total units ordered | 382 |
| Total revenue (cost x quantity) | about EUR 351k |
| Average / median order value | EUR 1,033 / EUR 500 |
| Distinct products ordered / catalogue size | 143 / 456 |
| Catalogue coverage | 31% |
| Countries served | 48 |
| Revenue share of top 10 products | 42% |
| Revenue share of top lab (Lab A) | 49% |
| Share of orders from non-academic organisations (SME + industry) | 21% |
| Share of orders on graded products | 67% |
| Orders growth, Jan-Sep 2021 vs Jan-Sep 2020 | +5% |
| Repeat-order share (estimated) | 69% |
| Orders-to-catalogue match rate | 100% |

The file also includes average units per order and an estimated count of distinct users.

## Main findings

- **Growth then plateau:** orders rose from 21 in 2016 to 99 in 2020; 2021 (to end of September) has 90.
- **Virus products drive revenue:** 65% of revenue from 36% of orders (about EUR 1,885 per order). Antibodies and nucleic acids are frequent but cheap (about EUR 250 to 390 per order).
- **Catalogue and demand mismatch:** virus products are 48% of the catalogue but 36% of orders; nucleic acids and services are ordered more than their catalogue share.
- **Concentration:** about 51 products (36% of those ordered) generate 80% of revenue, while 69% of the catalogue was never ordered.
- **Customers:** Germany, France and the USA lead. Universities and public research organisations place 74% of orders; SMEs pay the most per order.
- **Logistics:** dry ice is the most common shipping condition among ordered products.

## Charts (`outputs/charts/`)

| File | Chart |
|---|---|
| `01_trend.png` | Monthly orders and revenue (3-month average) |
| `02_year.png` | Orders per year |
| `03_lab.png` | Orders and revenue by provider lab |
| `04_type_revenue.png` | Revenue by product type |
| `05_type_aov.png` | Average order value by product type |
| `06_country.png` | Top 10 countries |
| `07_segment.png` | Customer segments (donut) |
| `08_segment_aov.png` | Average order value by segment |
| `09_grade.png` | Orders by product grading |
| `10_catalogue_vs_demand.png` | Catalogue mix vs orders mix |
| `11_pareto.png` | Revenue concentration (Pareto) |
| `12_top_products.png` | Top 10 most-ordered products |
| `13_age_gender.png` | Orders by age group and gender |
| `14_shipping.png` | Shipping conditions of ordered products |
| `15_heatmap.png` | Revenue: product type x lab |
| `16_boxplot.png` | Order value distribution (log scale) |

## Repository structure

```
.
├── scripts/
│   └── prat_dashboard.py
├── data/
│   ├── Exercice_PRAT_Orders.xlsx
│   └── Exercice_PRAT_Products.xlsx
├── outputs/
│   ├── dashboard.png
│   ├── kpis.csv
│   └── charts/
└── README.md
```

## Assumptions and limitations

- **Revenue** is announced academic cost x quantity; there are no invoiced amounts.
- **Distinct users and repeat-order share** are estimated from country, organisation type, gender and birth year, because there is no user ID.
- **Duplicates** are kept as repeat orders; remove them in the cleaning step if they are entry errors.
- **2021 is partial** (data ends 28 Sep 2021), so growth compares the same Jan-Sep window.
- Gender and birth year are used in aggregate only.

## Tech stack

Python, pandas, openpyxl, matplotlib, seaborn.

## Author

Your Name: add your LinkedIn or contact link here.
