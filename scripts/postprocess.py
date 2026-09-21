#!/usr/bin/env python3
"""
Post-processing of NOOA bolus review output.
Generates proper HTML reports with Plotly glucose charts from YAML data.

Usage:
    python3 scripts/postprocess.py                          # auto-detect latest
    python3 scripts/postprocess.py generated/260914_2227    # explicit directory
"""
import sys
import re
import json
from datetime import datetime
from pathlib import Path

import yaml
import markdown as md
import plotly.graph_objects as go

TARGET_LOW = 80
TARGET_HIGH = 180

PERIOD_LABELS = {
    "breakfast": "Petit-déjeuner",
    "lunch": "Déjeuner",
    "snack": "Goûter",
    "dinner": "Dîner",
    "night": "Nuit",
}

DAY_COLORS = [
    "#1a5276", "#2980b9", "#5dade2", "#85c1e9",
    "#aed6f1", "#d4e6f1", "#eaf2f8",
]

CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 1000px;
    margin: 40px auto;
    padding: 20px;
    background-color: #f8f9fa;
    color: #333;
    line-height: 1.6;
}
.container {
    background: white;
    border-radius: 8px;
    padding: 32px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
h1 {
    color: #007acc;
    border-bottom: 2px solid #007acc;
    padding-bottom: 16px;
    margin-bottom: 24px;
}
h2 { color: #0056b3; margin-top: 32px; }
h3 { color: #495057; margin-top: 24px; }
h4 { color: #6c757d; margin-top: 20px; }
p { margin-bottom: 12px; }
ul, ol { margin-bottom: 12px; padding-left: 24px; }
li { margin-bottom: 4px; }
nav.breadcrumb {
    margin-bottom: 16px;
    font-size: 14px;
    color: #666;
}
nav.breadcrumb a { color: #007acc; text-decoration: none; }
nav.breadcrumb a:hover { text-decoration: underline; }
.meta {
    color: #666;
    font-size: 14px;
    margin-bottom: 24px;
    padding: 8px 12px;
    background: #f8f9fa;
    border-radius: 4px;
}
.chart-section { margin: 24px 0; }
.chart-legend-note {
    text-align: center;
    font-size: 13px;
    color: #888;
    margin-top: 8px;
}
.conclusion-card {
    background: #e8f4fd;
    border-left: 4px solid #007acc;
    padding: 16px 20px;
    border-radius: 0 6px 6px 0;
    margin: 24px 0;
}
.conclusion-card h2 { color: #007acc; margin-top: 0; }
table.summary {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 14px;
}
table.summary th {
    background: #007acc;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
}
table.summary td {
    padding: 6px 10px;
    border-bottom: 1px solid #e9ecef;
}
table.summary tr:nth-child(even) { background: #f8f9fa; }
table.summary tr:hover { background: #e8f4fd; }
td.warn { color: #dc3545; font-weight: 600; }
td.ok { color: #28a745; }
.period-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    margin: 24px 0;
}
.period-card {
    display: block;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    text-decoration: none;
    color: #333;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.period-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    border-color: #007acc;
}
.period-card h3 { margin: 0 0 8px 0; color: #007acc; }
.period-card .recommendation { font-size: 14px; margin-bottom: 4px; }
.period-card .confidence { font-size: 13px; color: #888; }
.footer {
    text-align: center;
    color: #666;
    font-size: 13px;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #dee2e6;
}
"""


def find_latest_generated_dir():
    gen_root = Path("generated")
    if not gen_root.exists():
        print("No generated/ directory found")
        sys.exit(1)
    dirs = sorted(
        [d for d in gen_root.iterdir() if d.is_dir() and re.match(r"\d{6}_\d{4}$", d.name)],
        key=lambda d: d.name,
        reverse=True,
    )
    if not dirs:
        print("No generated run directories found")
        sys.exit(1)
    return dirs[0]


def discover_periods(gen_dir):
    periods = []
    for d in sorted(gen_dir.iterdir()):
        if d.is_dir():
            m = re.match(r"^(\d+)_(.+)$", d.name)
            if m:
                periods.append((m.group(1), m.group(2), d))
    return periods


def load_yaml(filepath):
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_text(filepath):
    if not filepath.exists():
        return ""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def render_markdown(text):
    return md.markdown(text, extensions=["extra", "sane_lists"])


def parse_time(time_str):
    t = datetime.strptime(str(time_str), "%H:%M:%S")
    return datetime(2000, 1, 1, t.hour, t.minute, t.second)


def _find_bg_at_time(bg_readings, time_str):
    """Find the closest BG reading to a given time."""
    target = parse_time(time_str)
    best_val = None
    best_delta = None
    for r in bg_readings:
        rt = parse_time(r["time"])
        delta = abs((rt - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_val = r["value"]
    return best_val


def build_glucose_chart(bg_detailed, insulin_data, period_name):
    fig = go.Figure()

    fig.add_hrect(
        y0=TARGET_LOW, y1=TARGET_HIGH,
        fillcolor="rgba(0, 180, 0, 0.07)",
        line_width=0,
    )

    # Index BG readings by date for correction bolus lookup
    bg_by_date = {}
    days_bg = bg_detailed.get("days_bg_data", [])
    for i, day in enumerate(days_bg):
        date_label = day["date"]
        readings = day.get("bg_readings", [])
        bg_by_date[date_label] = readings
        if not readings:
            continue
        times = [parse_time(r["time"]) for r in readings]
        values = [r["value"] for r in readings]
        color = DAY_COLORS[i] if i < len(DAY_COLORS) else DAY_COLORS[-1]
        fig.add_trace(go.Scatter(
            x=times, y=values,
            mode="lines",
            name=date_label,
            legendgroup=date_label,
            line=dict(color=color, width=3 if i == 0 else 1.5),
            hovertemplate=f"{date_label}<br>%{{x|%H:%M}}<br>%{{y}} mg/dL<extra></extra>",
        ))

    days_ins = insulin_data.get("days_data", [])
    for i, day in enumerate(days_ins):
        date_label = day["date"]
        for bolus in day.get("bolus_events", []):
            t = parse_time(bolus["time"])
            bg = bolus.get("bg_input", 0)
            carb = bolus.get("carb_input", 0)
            ins = bolus.get("insulin_delivered", 0)
            ic = bolus.get("ic_ratio", 0)
            fig.add_trace(go.Scatter(
                x=[t], y=[bg],
                mode="markers+text",
                legendgroup=date_label,
                marker=dict(symbol="triangle-up", size=14, color="#e74c3c",
                            line=dict(width=1, color="white")),
                text=[f"{carb:.0f}g"],
                textposition="top center",
                textfont=dict(size=10),
                showlegend=False,
                hovertemplate=(
                    f"{date_label}<br>%{{x|%H:%M}}<br>"
                    f"Glucides: {carb:.0f}g<br>"
                    f"Insuline: {ins:.2f}U<br>"
                    f"Ratio I:C: {ic:.0f}<br>"
                    f"Glyc: {bg} mg/dL<extra></extra>"
                ),
            ))
        for corr in day.get("correction_boluses", []):
            t = parse_time(corr["time"])
            ins = corr.get("insulin_delivered", 0)
            bg_at_corr = _find_bg_at_time(bg_by_date.get(date_label, []), corr["time"])
            y_val = bg_at_corr if bg_at_corr is not None else TARGET_HIGH
            fig.add_trace(go.Scatter(
                x=[t], y=[y_val],
                mode="markers+text",
                legendgroup=date_label,
                marker=dict(symbol="diamond", size=10, color="#f39c12",
                            line=dict(width=1, color="white")),
                text=[f"{ins:.1f}U"],
                textposition="top center",
                textfont=dict(size=10),
                showlegend=False,
                hovertemplate=(
                    f"Correction {date_label}<br>%{{x|%H:%M}}<br>"
                    f"Insuline: {ins:.1f}U<extra></extra>"
                ),
            ))

    fig.add_hline(y=TARGET_LOW, line_dash="dash",
                  line_color="rgba(231,76,60,0.4)")
    fig.add_hline(y=TARGET_HIGH, line_dash="dash",
                  line_color="rgba(243,156,18,0.4)")

    label = PERIOD_LABELS.get(period_name, period_name.capitalize())
    fig.update_layout(
        title=dict(text=f"Courbe de Glycémie — {label}", font=dict(size=16)),
        xaxis=dict(title="Heure", tickformat="%H:%M", gridcolor="#eee"),
        yaxis=dict(title="Glycémie (mg/dL)", range=[40, 350], gridcolor="#eee"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=30, t=60, b=60),
        height=450,
    )

    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    highlight_js = """
<script>
(function() {
    var gd = document.querySelector('.plotly-graph-div');
    if (!gd) return;
    var origWidths = null;
    var lockedGroup = null;

    function saveOriginals() {
        if (origWidths) return;
        origWidths = gd.data.map(function(t) {
            return t.line ? t.line.width : null;
        });
    }

    function restore() {
        if (!origWidths) return;
        var opacities = gd.data.map(function() { return 1; });
        var widths = origWidths.slice();
        Plotly.restyle(gd, {opacity: opacities, 'line.width': widths});
        lockedGroup = null;
    }

    function highlight(group) {
        saveOriginals();
        var opacities = [];
        var widths = [];
        gd.data.forEach(function(t, i) {
            if (!t.legendgroup) {
                opacities.push(1);
                widths.push(origWidths[i]);
            } else if (t.legendgroup === group) {
                opacities.push(1);
                widths.push(4);
            } else {
                opacities.push(0.12);
                widths.push(origWidths[i]);
            }
        });
        Plotly.restyle(gd, {opacity: opacities, 'line.width': widths});
    }

    gd.on('plotly_click', function(data) {
        var clickedGroup = data.points[0].data.legendgroup;
        if (!clickedGroup) return;
        if (lockedGroup === clickedGroup) {
            restore();
        } else {
            highlight(clickedGroup);
            lockedGroup = clickedGroup;
        }
    });

    // Double-click anywhere resets
    gd.querySelector('.plotarea').addEventListener('dblclick', function(e) {
        e.stopPropagation();
        if (lockedGroup) restore();
    });
})();
</script>
"""
    return chart_html + highlight_js


def build_summary_table(insulin_data):
    days = insulin_data.get("days_data", [])
    if not days:
        return ""
    rows = []
    for day in days:
        date = day["date"]
        bg = day.get("bg_summary", {})
        boluses = day.get("bolus_events", [])
        total_carbs = sum(b.get("carb_input", 0) for b in boluses)
        total_ins = sum(b.get("insulin_delivered", 0) for b in boluses)
        ic = boluses[0].get("ic_ratio", "") if boluses else ""
        start = bg.get("start_bg", "")
        finish = bg.get("finish_bg", "")
        mn = bg.get("min_bg", "")
        mx = bg.get("max_bg", "")
        hypo = bg.get("under_80_count", 0)
        hyper = bg.get("over_200_count", 0)
        n_corr = len(day.get("correction_boluses", []))

        hypo_cls = ' class="warn"' if hypo > 0 else ' class="ok"'
        hyper_cls = ' class="warn"' if hyper > 0 else ' class="ok"'

        rows.append(
            f"<tr><td>{date}</td><td>{total_carbs:.0f}g</td><td>{total_ins:.2f}U</td>"
            f"<td>{ic}</td><td>{start}</td><td>{finish}</td>"
            f"<td>{mn}</td><td>{mx}</td>"
            f"<td{hypo_cls}>{hypo}</td><td{hyper_cls}>{hyper}</td>"
            f"<td>{n_corr}</td></tr>"
        )

    return (
        '<table class="summary"><thead><tr>'
        "<th>Date</th><th>Glucides</th><th>Insuline</th><th>I:C</th>"
        "<th>Début</th><th>Fin</th><th>Min</th><th>Max</th>"
        "<th>&lt;80</th><th>&gt;200</th><th>Corr.</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def build_period_html(period_dir, period_name, period_prefix, gen_dir):
    bg_detailed = load_yaml(period_dir / "bg_detailed.yaml")
    insulin_data = load_yaml(period_dir / "insuline_data_7days.yml")
    llm_text = read_text(period_dir / "llm_analysis.md")
    conclusion_text = read_text(period_dir / "conclusion.md")

    label = PERIOD_LABELS.get(period_name, period_name.capitalize())
    meta = insulin_data.get("metadata", bg_detailed.get("metadata", {}))
    date_range = meta.get("date_range", "")
    total_days = meta.get("total_days", "")

    chart_html = ""
    if bg_detailed:
        chart_html = build_glucose_chart(bg_detailed, insulin_data, period_name)

    table_html = build_summary_table(insulin_data)
    analysis_html = render_markdown(llm_text) if llm_text else ""
    conclusion_html = render_markdown(conclusion_text) if conclusion_text else ""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} — Analyse I:C</title>
<style>{CSS}</style>
</head>
<body>
<nav class="breadcrumb"><a href="index.html">Index</a> &rsaquo; {label}</nav>
<div class="container">
<h1>{label} — Analyse du Ratio I:C</h1>
<div class="meta">Période: {date_range} &middot; {total_days} jours de données</div>

<section class="chart-section">
<h2>Courbe de Glycémie</h2>
{chart_html}
<div class="chart-legend-note">
&#9650; rouge = bolus repas &middot; &#9670; orange = correction &middot; bande verte = cible 80–180 mg/dL
</div>
</section>

<section>
<h2>Résumé par Jour</h2>
{table_html}
</section>

<div class="conclusion-card">
{conclusion_html}
</div>

<section class="analysis-section">
{analysis_html}
</section>

<div class="footer">
Généré par postprocess.py &middot; {datetime.now().strftime("%d/%m/%Y à %H:%M")}
</div>
</div>
</body>
</html>"""


def build_index_html(gen_dir, periods, summary_data):
    run_id = gen_dir.name
    all_conclusions = read_text(gen_dir / "all_conclusions.md")
    conclusions_html = render_markdown(all_conclusions) if all_conclusions else ""

    cards = []
    summary = summary_data.get("summary", {})
    for prefix, name, period_dir in periods:
        label = PERIOD_LABELS.get(name, name.capitalize())
        html_file = f"{prefix}_{name}.html"
        info = summary.get(name.capitalize(), {})
        rec = info.get("primary_recommendation", "").replace("_", " ").capitalize()
        conf = info.get("confidence", None)
        conf_str = f"{conf*100:.0f}%" if conf is not None else ""
        cards.append(
            f'<a href="{html_file}" class="period-card">'
            f"<h3>{label}</h3>"
            f'<div class="recommendation">{rec or "—"}</div>'
            f'<div class="confidence">Confiance: {conf_str or "—"}</div>'
            f"</a>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analyse I:C — {run_id}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<h1>Analyse des Ratios I:C</h1>
<div class="meta">Run: {run_id} &middot; {len(periods)} périodes analysées</div>

<div class="period-grid">
{"".join(cards)}
</div>

<section>
<h2>Conclusions</h2>
{conclusions_html}
</section>

<div class="footer">
Généré par postprocess.py &middot; {datetime.now().strftime("%d/%m/%Y à %H:%M")}
</div>
</div>
</body>
</html>"""


def postprocess(gen_dir):
    """Main post-processing logic. Can be called from nooa_bolus_review.py."""
    gen_dir = Path(gen_dir)
    if not gen_dir.is_dir():
        print(f"Directory not found: {gen_dir}")
        sys.exit(1)

    periods = discover_periods(gen_dir)
    if not periods:
        print(f"No period subdirectories found in {gen_dir}")
        sys.exit(1)

    summary_files = list(gen_dir.glob("analysis_summary_*.yaml"))
    summary_data = load_yaml(summary_files[0]) if summary_files else {}

    print(f"Post-processing {gen_dir.name}: {len(periods)} periods")

    for prefix, name, period_dir in periods:
        html = build_period_html(period_dir, name, prefix, gen_dir)
        out = gen_dir / f"{prefix}_{name}.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  {out.name}")

    index_html = build_index_html(gen_dir, periods, summary_data)
    index_path = gen_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  {index_path.name}")

    print(f"Done. Open {index_path}")


def main():
    if len(sys.argv) > 1:
        gen_dir = Path(sys.argv[1])
    else:
        gen_dir = find_latest_generated_dir()
    postprocess(gen_dir)


if __name__ == "__main__":
    main()
