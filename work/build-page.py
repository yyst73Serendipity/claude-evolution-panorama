"""
构建 Claude 演进全景单文件网页：读取结构化时间线数据，校验日期与字段，并生成内嵌样式、脚本和数据的 HTML。
"""

from __future__ import annotations

import html
import json
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "work" / "timeline-data.json"
OUTPUT_PATH = ROOT / "outputs" / "claude-evolution-panorama.html"
REFERENCE_SOURCES = [
    ("Claude 订阅价格", "Claude 官方", "https://claude.com/pricing"),
    ("Claude API 定价", "Claude Platform Docs", "https://platform.claude.com/docs/en/about-claude/pricing"),
    ("模型弃用与退役", "Claude Platform Docs", "https://platform.claude.com/docs/en/about-claude/model-deprecations"),
]
REQUIRED_FIELDS = {
    "date",
    "precision",
    "category",
    "title",
    "summary",
    "delta",
    "optimization",
    "availability",
    "significance",
    "sourceLabel",
    "sourceUrl",
}


def load_and_validate_data() -> dict:
    """读取时间线数据，并在构建前校验边界日期、字段和官方 HTTPS 来源。"""
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cutoff = date.fromisoformat(data["cutoff"])
    events = data.get("events", [])
    if not events:
        raise ValueError("时间线数据为空")

    previous_date = date.min
    for index, event in enumerate(events, start=1):
        missing = REQUIRED_FIELDS - event.keys()
        if missing:
            raise ValueError(f"第 {index} 条事件缺少字段：{sorted(missing)}")
        event_date = date.fromisoformat(event["date"])
        if event_date > cutoff:
            raise ValueError(f"事件晚于截止日期：{event['date']} {event['title']}")
        if event_date < previous_date:
            raise ValueError(f"事件未按日期升序排列：{event['date']} {event['title']}")
        previous_date = event_date

        source = urlparse(event["sourceUrl"])
        if source.scheme != "https" or source.netloc not in {
            "www.anthropic.com",
            "anthropic.com",
            "claude.com",
            "www.claude.com",
            "support.claude.com",
            "platform.claude.com",
        }:
            raise ValueError(f"来源不是允许的官方 HTTPS 域名：{event['sourceUrl']}")
    return data


def make_stat_bars(counter: Counter, total: int) -> str:
    """把分类统计生成为带数值标签的静态横向条形图。"""
    rows = []
    for category, count in counter.most_common():
        width = count / total * 100
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label"><span>{html.escape(category)}</span><strong>{count}</strong></div>
              <div class="bar-track" aria-hidden="true"><span style="width:{width:.2f}%"></span></div>
            </div>"""
        )
    return "\n".join(rows)


def make_year_distribution(year_counter: Counter) -> str:
    """生成年份分布卡片，为时间跨度提供第一眼概览。"""
    maximum = max(year_counter.values())
    cards = []
    for year in sorted(year_counter):
        count = year_counter[year]
        cards.append(
            f"""
            <button class="year-block" type="button" data-year-jump="{year}" aria-label="筛选 {year} 年，共 {count} 条事件">
              <span class="year-block__value">{count}</span>
              <span class="year-block__bar" style="--height:{max(18, count / maximum * 100):.1f}%" aria-hidden="true"></span>
              <span class="year-block__label">{year}</span>
            </button>"""
        )
    return "\n".join(cards)


def make_source_index(events: list[dict]) -> str:
    """按首次出现顺序生成去重后的官方来源索引。"""
    seen = set()
    items = []
    for title, label, url in REFERENCE_SOURCES:
        seen.add(url)
        items.append(
            f'''<li><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(title)}</a><span>{html.escape(label)}</span></li>'''
        )
    for event in reversed(events):
        url = event["sourceUrl"]
        if url in seen:
            continue
        seen.add(url)
        items.append(
            f"""<li><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(event['title'])}</a><span>{html.escape(event['sourceLabel'])}</span></li>"""
        )
    return "\n".join(items)


def build_html(data: dict) -> str:
    """将校验后的数据注入独立页面模板，并生成静态专题区与动态时间线。"""
    events = data["events"]
    cutoff = data["cutoff"]
    category_counter = Counter(event["category"] for event in events)
    year_counter = Counter(event["date"][:4] for event in events)
    unique_sources = {event["sourceUrl"] for event in events} | {item[2] for item in REFERENCE_SOURCES}
    timeline_json = json.dumps(events, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    last_checked = data.get("lastChecked", "尚未执行自动检查")
    category_options = "\n".join(
        f'<option value="{html.escape(category, quote=True)}">{html.escape(category)}（{count}）</option>'
        for category, count in category_counter.most_common()
    )
    year_options = "\n".join(
        f'<option value="{year}">{year}（{year_counter[year]}）</option>' for year in sorted(year_counter)
    )

    document = r'''<!--
本文件是 Claude 模型、产品、订阅计划与开发者生态的中文演进全景网页，由项目构建脚本自动生成。
-->
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="description" content="Claude 从 Constitutional AI、Claude 1 到 Claude 5.5、Cowork 与 Claude Code 的完整中文演进时间线。">
  <title>Claude 演进全景｜2022—2026</title>
  <style>
    :root {
      color-scheme: light;
      --page:#f5f1e9;
      --surface:#fffdf8;
      --surface-2:#eee8dc;
      --ink:#211f1b;
      --muted:#6d675e;
      --line:#d8d0c2;
      --accent:#cc6b3c;
      --accent-deep:#8b3f22;
      --accent-soft:#f6dfd1;
      --navy:#26384a;
      --sage:#496d5b;
      --violet:#675178;
      --gold:#9a681f;
      --danger:#9f4335;
      --shadow:0 18px 45px rgba(61,45,28,.09);
      --radius:22px;
      --max:1200px;
    }
    html[data-theme="dark"] {
      color-scheme: dark;
      --page:#171613;
      --surface:#22201c;
      --surface-2:#2d2923;
      --ink:#f6f0e7;
      --muted:#bbb2a6;
      --line:#454039;
      --accent:#e28a5e;
      --accent-deep:#ffc2a4;
      --accent-soft:#42291f;
      --navy:#9fc4e3;
      --sage:#9bc5ac;
      --violet:#c0abd0;
      --gold:#e6ba73;
      --danger:#ef9d8e;
      --shadow:0 18px 45px rgba(0,0,0,.24);
    }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body {
      margin:0;
      background:
        radial-gradient(circle at 10% 5%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 30rem),
        var(--page);
      color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
      line-height:1.65;
    }
    a { color:var(--accent-deep); text-underline-offset:3px; }
    button,input,select { font:inherit; }
    button { color:inherit; }
    .skip-link { position:fixed; left:1rem; top:-5rem; z-index:100; background:var(--ink); color:var(--surface); padding:.7rem 1rem; border-radius:10px; }
    .skip-link:focus { top:1rem; }
    .topbar {
      position:sticky; top:0; z-index:40;
      display:flex; align-items:center; justify-content:space-between; gap:1rem;
      padding:.65rem max(1rem,calc((100% - var(--max))/2));
      background:color-mix(in srgb,var(--page) 88%,transparent);
      border-bottom:1px solid color-mix(in srgb,var(--line) 75%,transparent);
      backdrop-filter:blur(14px);
    }
    .brand { display:flex; align-items:center; gap:.65rem; font-weight:800; text-decoration:none; color:var(--ink); }
    .brand-mark { width:1.8rem; height:1.8rem; border-radius:50%; display:grid; place-items:center; background:var(--accent); color:#fff; font-size:.78rem; }
    .topnav { display:flex; align-items:center; gap:.2rem; overflow-x:auto; scrollbar-width:none; }
    .topnav a { white-space:nowrap; padding:.4rem .62rem; color:var(--muted); text-decoration:none; border-radius:8px; font-size:.86rem; }
    .topnav a:hover,.topnav a:focus-visible { background:var(--surface-2); color:var(--ink); }
    .icon-button { border:1px solid var(--line); background:var(--surface); border-radius:999px; padding:.42rem .7rem; cursor:pointer; white-space:nowrap; }
    .container { width:min(calc(100% - 2rem),var(--max)); margin-inline:auto; }
    .hero { padding:clamp(4rem,9vw,8rem) 0 3rem; }
    .eyebrow { display:inline-flex; align-items:center; gap:.45rem; padding:.35rem .7rem; border:1px solid color-mix(in srgb,var(--accent) 35%,var(--line)); border-radius:999px; color:var(--accent-deep); background:color-mix(in srgb,var(--accent-soft) 68%,transparent); font-size:.82rem; font-weight:750; letter-spacing:.04em; }
    .hero h1 { max-width:900px; margin:1.25rem 0 .9rem; font-size:clamp(2.5rem,7vw,6.2rem); line-height:.96; letter-spacing:-.055em; }
    .hero h1 em { color:var(--accent); font-style:normal; }
    .hero-lead { max-width:810px; margin:0; color:var(--muted); font-size:clamp(1.05rem,2vw,1.32rem); }
    .hero-meta { display:flex; flex-wrap:wrap; gap:.7rem; margin-top:1.5rem; }
    .meta-pill { padding:.55rem .78rem; background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:0 6px 18px rgba(61,45,28,.05); font-size:.9rem; }
    .hero-actions { display:flex; flex-wrap:wrap; gap:.8rem; margin-top:2rem; }
    .button { display:inline-flex; align-items:center; justify-content:center; gap:.4rem; min-height:44px; padding:.65rem 1rem; border-radius:12px; border:1px solid var(--line); background:var(--surface); color:var(--ink); text-decoration:none; cursor:pointer; font-weight:700; }
    .button--primary { background:var(--ink); border-color:var(--ink); color:var(--surface); }
    .button:hover { transform:translateY(-1px); box-shadow:0 8px 20px rgba(61,45,28,.08); }
    .section { padding:4.5rem 0; scroll-margin-top:4rem; }
    .section--tint { background:color-mix(in srgb,var(--surface-2) 52%,transparent); border-block:1px solid color-mix(in srgb,var(--line) 70%,transparent); }
    .section-head { display:grid; grid-template-columns:minmax(0,1fr) minmax(250px,.55fr); gap:2rem; align-items:end; margin-bottom:2rem; }
    .kicker { color:var(--accent-deep); font-size:.78rem; font-weight:850; letter-spacing:.1em; text-transform:uppercase; }
    h2 { margin:.35rem 0 0; font-size:clamp(1.9rem,4vw,3.2rem); line-height:1.08; letter-spacing:-.035em; }
    h3 { line-height:1.25; }
    .section-intro { color:var(--muted); margin:0; }
    .stat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
    .stat-card { min-height:160px; padding:1.25rem; border:1px solid var(--line); border-radius:var(--radius); background:var(--surface); box-shadow:var(--shadow); }
    .stat-card strong { display:block; margin-bottom:.35rem; font-size:clamp(2rem,4vw,3.2rem); line-height:1; letter-spacing:-.04em; color:var(--accent-deep); }
    .stat-card span { color:var(--muted); }
    .overview-grid { display:grid; grid-template-columns:1fr 1.6fr; gap:1rem; margin-top:1rem; }
    .panel { padding:1.25rem; border:1px solid var(--line); border-radius:var(--radius); background:var(--surface); box-shadow:var(--shadow); }
    .panel h3 { margin-top:0; }
    .bar-row + .bar-row { margin-top:.7rem; }
    .bar-label { display:flex; justify-content:space-between; gap:1rem; font-size:.88rem; }
    .bar-track { height:7px; margin-top:.3rem; border-radius:999px; background:var(--surface-2); overflow:hidden; }
    .bar-track span { display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,var(--accent),#e9a46e); }
    .year-chart { display:grid; grid-template-columns:repeat(5,1fr); min-height:245px; align-items:end; gap:.6rem; padding-top:1rem; }
    .year-block { position:relative; display:grid; grid-template-rows:auto 150px auto; align-items:end; gap:.45rem; height:100%; padding:.5rem; border:0; border-radius:12px; background:transparent; cursor:pointer; }
    .year-block:hover,.year-block:focus-visible { background:var(--surface-2); }
    .year-block__value { font-weight:800; text-align:center; }
    .year-block__bar { align-self:end; display:block; height:var(--height); min-height:18px; border-radius:9px 9px 3px 3px; background:linear-gradient(180deg,var(--accent),color-mix(in srgb,var(--accent) 45%,var(--navy))); }
    .year-block__label { font-size:.8rem; color:var(--muted); text-align:center; }
    .phase-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:.8rem; }
    .phase-card { position:relative; padding:1.1rem; border-radius:18px; background:var(--surface); border:1px solid var(--line); }
    .phase-card::before { content:""; display:block; width:2.2rem; height:5px; margin-bottom:1rem; border-radius:9px; background:var(--accent); }
    .phase-card small { color:var(--accent-deep); font-weight:800; }
    .phase-card h3 { margin:.3rem 0 .55rem; font-size:1.08rem; }
    .phase-card p { margin:0; color:var(--muted); font-size:.88rem; }
    .toolbar { position:sticky; top:3.5rem; z-index:30; display:grid; grid-template-columns:1.5fr repeat(3,minmax(130px,.6fr)) auto; gap:.7rem; padding:.85rem; margin-bottom:1rem; border:1px solid var(--line); border-radius:18px; background:color-mix(in srgb,var(--surface) 93%,transparent); box-shadow:var(--shadow); backdrop-filter:blur(14px); }
    .control { display:grid; gap:.25rem; }
    .control label { font-size:.72rem; color:var(--muted); font-weight:750; }
    .control input,.control select { width:100%; min-height:42px; padding:.55rem .65rem; border:1px solid var(--line); border-radius:10px; background:var(--page); color:var(--ink); }
    .toolbar-actions { display:flex; align-items:end; gap:.4rem; }
    .tool-button { min-height:42px; padding:.55rem .75rem; border:1px solid var(--line); border-radius:10px; background:var(--surface); cursor:pointer; }
    .result-line { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin:1.2rem 0 1rem; color:var(--muted); font-size:.9rem; }
    .timeline { position:relative; display:grid; gap:1rem; }
    .timeline::before { content:""; position:absolute; left:108px; top:0; bottom:0; width:1px; background:var(--line); }
    .year-heading { position:relative; display:grid; grid-template-columns:90px 1fr; gap:2.4rem; align-items:center; margin-top:1.5rem; }
    .year-heading h3 { margin:0; font-size:2rem; letter-spacing:-.04em; }
    .year-heading span { color:var(--muted); font-size:.88rem; }
    .event { position:relative; display:grid; grid-template-columns:90px 1fr; gap:2.4rem; }
    .event::before { content:""; position:absolute; left:102px; top:1.55rem; width:13px; height:13px; border-radius:50%; border:3px solid var(--page); background:var(--category,var(--accent)); box-shadow:0 0 0 1px var(--line); }
    .event-date { padding-top:1.1rem; text-align:right; color:var(--muted); font-size:.8rem; font-variant-numeric:tabular-nums; }
    .event-card { border:1px solid var(--line); border-radius:18px; background:var(--surface); overflow:hidden; box-shadow:0 7px 20px rgba(61,45,28,.045); }
    .event-main { padding:1rem 1.05rem; }
    .event-meta { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin-bottom:.55rem; }
    .badge { display:inline-flex; align-items:center; padding:.2rem .52rem; border-radius:999px; background:color-mix(in srgb,var(--category,var(--accent)) 14%,transparent); color:var(--category,var(--accent-deep)); border:1px solid color-mix(in srgb,var(--category,var(--accent)) 28%,var(--line)); font-size:.72rem; font-weight:800; }
    .event-card h3 { margin:0; font-size:1.12rem; }
    .event-summary { margin:.5rem 0 0; color:var(--muted); }
    .event-card details { border-top:1px solid var(--line); }
    .event-card summary { padding:.68rem 1.05rem; cursor:pointer; color:var(--accent-deep); font-weight:750; font-size:.85rem; list-style-position:inside; }
    .event-details { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; padding:0 1.05rem 1rem; }
    .detail-item { padding:.75rem; border-radius:12px; background:var(--page); }
    .detail-item dt { margin-bottom:.22rem; font-size:.73rem; font-weight:850; color:var(--accent-deep); }
    .detail-item dd { margin:0; font-size:.86rem; color:var(--muted); }
    .source-link { grid-column:1/-1; display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.65rem .75rem; border-radius:12px; border:1px dashed var(--line); text-decoration:none; font-size:.82rem; }
    .empty-state { padding:3rem 1rem; text-align:center; border:1px dashed var(--line); border-radius:18px; color:var(--muted); }
    .family-road { display:grid; grid-template-columns:repeat(5,1fr); gap:.7rem; }
    .family { padding:1.1rem; border:1px solid var(--line); border-radius:18px; background:var(--surface); }
    .family-num { display:grid; place-items:center; width:2.5rem; height:2.5rem; border-radius:50%; background:var(--ink); color:var(--surface); font-size:1.1rem; font-weight:850; }
    .family h3 { margin:.8rem 0 .3rem; }
    .family p { margin:.25rem 0; color:var(--muted); font-size:.86rem; }
    .family-tags { display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.7rem; }
    .mini-tag { padding:.17rem .4rem; border-radius:6px; background:var(--surface-2); font-size:.72rem; }
    .callout { margin-top:1rem; padding:1.15rem; border-left:5px solid var(--accent); border-radius:0 16px 16px 0; background:var(--accent-soft); }
    .callout strong { color:var(--accent-deep); }
    .official-links { display:flex; flex-wrap:wrap; gap:.6rem; margin-top:1rem; }
    .official-links a { display:inline-flex; padding:.45rem .7rem; border:1px solid var(--line); border-radius:10px; background:var(--surface); text-decoration:none; font-size:.82rem; font-weight:750; }
    .product-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }
    .product-card { padding:1.25rem; border:1px solid var(--line); border-radius:20px; background:var(--surface); }
    .product-icon { display:grid; place-items:center; width:2.5rem; height:2.5rem; border-radius:11px; background:var(--surface-2); color:var(--accent-deep); font-weight:900; }
    .product-card h3 { margin:.8rem 0 .45rem; }
    .product-card p { color:var(--muted); margin:0; font-size:.9rem; }
    .product-card ul { margin:.8rem 0 0; padding-left:1.15rem; font-size:.84rem; }
    .product-card li + li { margin-top:.3rem; }
    .table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:18px; background:var(--surface); }
    table { width:100%; border-collapse:collapse; min-width:760px; }
    th,td { padding:.85rem .9rem; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
    th { background:var(--surface-2); font-size:.78rem; color:var(--muted); position:sticky; top:0; }
    td { font-size:.88rem; }
    tbody tr:last-child td { border-bottom:0; }
    .price { font-size:1rem; font-weight:850; color:var(--accent-deep); white-space:nowrap; }
    .plan-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; }
    .plan { position:relative; padding:1.1rem; border:1px solid var(--line); border-radius:18px; background:var(--surface); }
    .plan--accent { border-color:color-mix(in srgb,var(--accent) 55%,var(--line)); box-shadow:0 12px 35px color-mix(in srgb,var(--accent) 13%,transparent); }
    .plan h3 { margin:0; }
    .plan .price-big { margin:.55rem 0; font-size:1.55rem; font-weight:900; color:var(--accent-deep); }
    .plan p,.plan li { font-size:.83rem; color:var(--muted); }
    .plan ul { margin:.7rem 0 0; padding-left:1.1rem; }
    .migration-flow { display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; counter-reset:steps; }
    .migration-step { counter-increment:steps; padding:1rem; border-radius:16px; border:1px solid var(--line); background:var(--surface); }
    .migration-step::before { content:counter(steps); display:grid; place-items:center; width:1.8rem; height:1.8rem; border-radius:50%; background:var(--accent); color:#fff; font-weight:850; }
    .migration-step strong { display:block; margin:.6rem 0 .25rem; }
    .migration-step span { color:var(--muted); font-size:.84rem; }
    .insight-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; }
    .insight { padding:1.25rem; border-radius:20px; border:1px solid var(--line); background:var(--surface); }
    .insight b { display:block; color:var(--accent-deep); font-size:.78rem; letter-spacing:.08em; }
    .insight h3 { margin:.35rem 0; }
    .insight p { margin:0; color:var(--muted); }
    .notes { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
    .notes ul { margin:0; padding-left:1.2rem; }
    .source-index { columns:2; column-gap:2rem; margin:0; padding-left:1.3rem; }
    .source-index li { break-inside:avoid; margin-bottom:.65rem; padding-right:1rem; }
    .source-index a { font-size:.86rem; }
    .source-index span { display:block; color:var(--muted); font-size:.72rem; }
    footer { padding:2.5rem 0 4rem; color:var(--muted); border-top:1px solid var(--line); font-size:.85rem; }
    .back-top { position:fixed; right:1rem; bottom:1rem; z-index:20; width:44px; height:44px; border:1px solid var(--line); border-radius:50%; background:var(--surface); box-shadow:var(--shadow); cursor:pointer; opacity:0; pointer-events:none; transition:opacity .2s; }
    .back-top.is-visible { opacity:1; pointer-events:auto; }
    :focus-visible { outline:3px solid color-mix(in srgb,var(--accent) 55%,transparent); outline-offset:2px; }
    [hidden] { display:none !important; }
    @media (max-width:1000px) {
      .topnav a:nth-child(n+5) { display:none; }
      .stat-grid,.plan-grid { grid-template-columns:repeat(2,1fr); }
      .phase-grid,.family-road { grid-template-columns:repeat(3,1fr); }
      .toolbar { grid-template-columns:1fr 1fr 1fr; }
      .control--search { grid-column:1/-1; }
      .toolbar-actions { align-items:stretch; }
      .product-grid { grid-template-columns:repeat(2,1fr); }
    }
    @media (max-width:720px) {
      .topbar { padding-inline:1rem; }
      .topnav { display:none; }
      .section { padding:3.5rem 0; }
      .section-head { grid-template-columns:1fr; gap:.8rem; }
      .stat-grid,.overview-grid,.product-grid,.notes,.insight-grid { grid-template-columns:1fr; }
      .phase-grid,.family-road { grid-template-columns:1fr 1fr; }
      .toolbar { position:relative; top:auto; grid-template-columns:1fr 1fr; }
      .control--search,.toolbar-actions { grid-column:1/-1; }
      .toolbar-actions .tool-button { flex:1; }
      .timeline::before { left:9px; }
      .year-heading,.event { grid-template-columns:1fr; gap:.4rem; padding-left:27px; }
      .year-heading::before,.event::before { left:3px; top:1.25rem; }
      .event-date { padding:0; text-align:left; }
      .event-details { grid-template-columns:1fr; }
      .source-link { grid-column:auto; align-items:flex-start; flex-direction:column; gap:.25rem; }
      .migration-flow { grid-template-columns:1fr 1fr; }
      .source-index { columns:1; }
    }
    @media (max-width:460px) {
      .container { width:min(calc(100% - 1.1rem),var(--max)); }
      .hero { padding-top:3.1rem; }
      .hero h1 { font-size:2.55rem; }
      .stat-grid,.phase-grid,.family-road,.plan-grid,.migration-flow { grid-template-columns:1fr; }
      .toolbar { grid-template-columns:1fr; }
      .control--search,.toolbar-actions { grid-column:auto; }
      .year-chart { gap:.2rem; }
      .year-block { padding:.25rem; }
      .year-block__label { writing-mode:vertical-rl; justify-self:center; }
      .result-line { align-items:flex-start; flex-direction:column; }
    }
    @media print {
      .topbar,.toolbar,.hero-actions,.back-top,.tool-button { display:none !important; }
      body { background:#fff; color:#111; }
      .section { padding:1.5rem 0; break-inside:avoid; }
      .event-card details > * { display:block !important; }
      .event-card details summary { display:none !important; }
      .event-details { display:grid !important; }
      a { color:#111; text-decoration:none; }
    }
    @media (prefers-reduced-motion:reduce) {
      html { scroll-behavior:auto; }
      *,*::before,*::after { animation-duration:.01ms !important; transition-duration:.01ms !important; }
      .button:hover { transform:none; }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main">跳到主要内容</a>
  <header class="topbar">
    <a class="brand" href="#top"><span class="brand-mark" aria-hidden="true">C</span><span>Claude 演进全景</span></a>
    <nav class="topnav" aria-label="主要章节">
      <a href="#timeline">时间线</a><a href="#models">模型</a><a href="#products">产品</a><a href="#plans">订阅</a><a href="#api">API 价格</a><a href="#migration">迁移</a><a href="#sources">来源</a>
    </nav>
    <button class="icon-button" id="theme-toggle" type="button" aria-label="切换深色或浅色主题">◐ 主题</button>
  </header>

  <main id="main">
    <section class="hero container" id="top">
      <span class="eyebrow">官方资料驱动 · 截止 __CUTOFF__</span>
      <h1>从会聊天，<br>到能<em>持续交付工作</em></h1>
      <p class="hero-lead">一张网页梳理 Claude 从 Constitutional AI、Claude 1，到第五代模型、Claude Code、Cowork、MCP、办公创作与企业治理的完整演进。重点不是罗列版本，而是解释每次更新相对前代改变了什么。</p>
      <div class="hero-meta">
        <span class="meta-pill"><strong>__EVENT_COUNT__</strong> 条关键更新</span>
        <span class="meta-pill"><strong>__CATEGORY_COUNT__</strong> 个观察维度</span>
        <span class="meta-pill"><strong>__SOURCE_COUNT__</strong> 个官方来源页</span>
        <span class="meta-pill">范围：2022-12—__CUTOFF__</span>
        <span class="meta-pill">最后自动检查：__LAST_CHECKED__</span>
      </div>
      <div class="hero-actions"><a class="button button--primary" href="#timeline">进入可筛选时间线</a><a class="button" href="#models">查看模型谱系</a></div>
    </section>

    <section class="section section--tint" id="overview">
      <div class="container">
        <div class="section-head"><div><span class="kicker">At a glance</span><h2>四年间，Claude 的重心发生了三次迁移</h2></div><p class="section-intro">先建立“安全、长上下文”的模型身份，再扩张为应用与开发平台，最后把编码代理、桌面代理和办公成果整合成工作系统。</p></div>
        <div class="stat-grid">
          <article class="stat-card"><strong>__EVENT_COUNT__</strong><span>条经官方页面对应的关键事件</span></article>
          <article class="stat-card"><strong>1M</strong><span>上下文在 4.6 时代进入主力模型路线</span></article>
          <article class="stat-card"><strong>5.5</strong><span>截至截止日的最新主线家族代际</span></article>
          <article class="stat-card"><strong>3 层</strong><span>模型、成品应用、开发与智能体平台</span></article>
        </div>
        <div class="overview-grid">
          <article class="panel"><h3>更新类别分布</h3>__STAT_BARS__</article>
          <article class="panel"><h3>按年份查看关键节点</h3><div class="year-chart" role="img" aria-label="各年份时间线事件数量，按钮可直接筛选对应年份">__YEAR_DISTRIBUTION__</div></article>
        </div>
      </div>
    </section>

    <section class="section container" id="phases">
      <div class="section-head"><div><span class="kicker">Five phases</span><h2>五个阶段，看清演进主线</h2></div><p class="section-intro">同一年可能同时推进模型、安全、应用和商业化；阶段划分用于理解战略重心，而不是把产品线硬切开。</p></div>
      <div class="phase-grid">
        <article class="phase-card"><small>2022—2023</small><h3>奠基与走向市场</h3><p>Constitutional AI、Claude 1/2、100K/200K 上下文和首个 Pro 计划。</p></article>
        <article class="phase-card"><small>2024</small><h3>模型家族化</h3><p>Opus / Sonnet / Haiku 分层，Artifacts、Projects、Tool Use、Computer Use 与 MCP 成形。</p></article>
        <article class="phase-card"><small>2025</small><h3>推理与编码代理</h3><p>Extended Thinking、Claude 4、Claude Code、Research、Integrations 与 Max。</p></article>
        <article class="phase-card"><small>2026 H1</small><h3>桌面代理与长时工作</h3><p>Cowork、Dispatch、Computer Use 产品化，4.6—4.8 加速，Fable / Mythos 开启第五代。</p></article>
        <article class="phase-card"><small>2026 H2</small><h3>统一工作成果平台</h3><p>5/5.5 家族、办公套件、Design、Dashboards、Motion 与 Code Review GA。</p></article>
      </div>
    </section>

    <section class="section section--tint" id="timeline">
      <div class="container">
        <div class="section-head"><div><span class="kicker">Interactive timeline</span><h2>逐条查阅：时间、变化、优化与适用范围</h2></div><p class="section-intro">搜索会匹配标题、摘要、变化、优化、适用范围和战略意义。展开卡片即可看到“相对前一阶段改变了什么”。</p></div>
        <form class="toolbar" id="filters" role="search">
          <div class="control control--search"><label for="query">全文搜索</label><input id="query" type="search" placeholder="例如：上下文、Claude Code、MCP、Team…" autocomplete="off"></div>
          <div class="control"><label for="year-filter">年份</label><select id="year-filter"><option value="">全部年份（__EVENT_COUNT__）</option>__YEAR_OPTIONS__</select></div>
          <div class="control"><label for="category-filter">类别</label><select id="category-filter"><option value="">全部类别</option>__CATEGORY_OPTIONS__</select></div>
          <div class="control"><label for="sort-order">排序</label><select id="sort-order"><option value="asc">从早到晚</option><option value="desc">从晚到早</option></select></div>
          <div class="toolbar-actions"><button class="tool-button" id="toggle-details" type="button">展开全部</button><button class="tool-button" id="reset-filters" type="button">重置</button></div>
        </form>
        <div class="result-line"><strong id="result-count" aria-live="polite">正在载入时间线…</strong><span>每条记录均提供官方来源链接</span></div>
        <div class="timeline" id="timeline-list"></div>
        <div class="empty-state" id="empty-state" hidden>没有匹配结果。请缩短关键词或清除筛选。</div>
        <noscript><div class="empty-state">时间线筛选需要启用 JavaScript；下方模型、产品和价格专题仍可直接阅读。</div></noscript>
      </div>
    </section>

    <section class="section container" id="models">
      <div class="section-head"><div><span class="kicker">Model lineage</span><h2>模型谱系：从单一 Claude 到分层家族</h2></div><p class="section-intro">代际升级的核心不是只提高分数：上下文、思考方式、代理能力、延迟、单位任务成本和安全分发方式一直同步变化。</p></div>
      <div class="family-road">
        <article class="family"><span class="family-num">1</span><h3>Claude 1.x</h3><p>2023 · Claude / Instant 双层路线。</p><p>关键词：可控对话、100K 长上下文、轻量低价。</p><div class="family-tags"><span class="mini-tag">Claude 1</span><span class="mini-tag">Instant 1.2</span></div></article>
        <article class="family"><span class="family-num">2</span><h3>Claude 2.x</h3><p>2023 · 能力、安全与消费应用同步。</p><p>关键词：200K、低幻觉、工具使用 Beta。</p><div class="family-tags"><span class="mini-tag">Claude 2</span><span class="mini-tag">Claude 2.1</span></div></article>
        <article class="family"><span class="family-num">3</span><h3>Claude 3.x</h3><p>2024—2025 · 首个完整三档家族。</p><p>关键词：多模态、性价比分层、Extended Thinking。</p><div class="family-tags"><span class="mini-tag">Opus</span><span class="mini-tag">Sonnet</span><span class="mini-tag">Haiku</span><span class="mini-tag">3.7</span></div></article>
        <article class="family"><span class="family-num">4</span><h3>Claude 4.x</h3><p>2025—2026 · 为长期代理工作设计。</p><p>关键词：混合推理、Claude Code、1M 上下文、adaptive thinking。</p><div class="family-tags"><span class="mini-tag">4 / 4.1</span><span class="mini-tag">4.5</span><span class="mini-tag">4.6—4.8</span></div></article>
        <article class="family"><span class="family-num">5</span><h3>Claude 5.x</h3><p>2026 · 通用前沿、可信访问和高效主线并行。</p><p>关键词：Fable / Mythos、5.5 全家族、单位任务成本。</p><div class="family-tags"><span class="mini-tag">Fable</span><span class="mini-tag">Mythos</span><span class="mini-tag">Opus</span><span class="mini-tag">Sonnet</span><span class="mini-tag">Haiku</span></div></article>
      </div>
      <div class="callout"><strong>Fable 与 Mythos 不是 Opus / Sonnet / Haiku 的简单新档位。</strong> Fable 是面向广泛用户的第五代前沿通用路线；Mythos 与其共享基础模型，但针对经审核的网络安全、生命科学等可信研究场景，在权限和防护上采用差异化分发。普通用户选型仍主要围绕 Opus、Sonnet、Haiku。</div>
    </section>

    <section class="section section--tint" id="products">
      <div class="container">
        <div class="section-head"><div><span class="kicker">Product panorama</span><h2>产品全景：一个模型，六种工作界面</h2></div><p class="section-intro">Claude 的扩张方式不是不断增加独立聊天框，而是让相同模型通过成品应用、代码代理、桌面代理、API 和连接器进入不同工作现场。</p></div>
        <div class="product-grid">
          <article class="product-card"><span class="product-icon">A</span><h3>Claude 应用</h3><p>Web、iOS、Android 和 Desktop 中的通用助手入口。</p><ul><li>Projects、Research、Web Search、Memory</li><li>Artifacts、Docs、Slides、Design、Dashboards、Motion</li><li>Google Workspace 与连接器</li></ul></article>
          <article class="product-card"><span class="product-icon">&lt;/&gt;</span><h3>Claude Code</h3><p>从终端研究预览发展为软件工程代理与质量治理层。</p><ul><li>代码库理解、编辑、测试、提交与 PR</li><li>原生 IDE、远程委派和子代理</li><li>Code Review：Quick / Standard / Deep</li></ul></article>
          <article class="product-card"><span class="product-icon">W</span><h3>Cowork</h3><p>把 Claude Code 的代理架构带到非编码桌面工作。</p><ul><li>本地文件、浏览器与 GUI 操作</li><li>Dispatch 跨设备分派</li><li>Plugins、Skills 与企业私有市场</li></ul></article>
          <article class="product-card"><span class="product-icon">P</span><h3>Claude Platform / API</h3><p>模型、工具和代理能力的开发者底座。</p><ul><li>Tool Use、Prompt Caching、Batches</li><li>Web Search、Computer Use、Files / Skills API</li><li>Console 评测、Workspaces 与使用观测</li></ul></article>
          <article class="product-card"><span class="product-icon">M</span><h3>MCP 与连接器</h3><p>用开放协议统一模型访问工具和数据的方式。</p><ul><li>本地与远程 MCP Server</li><li>Integrations 和企业连接器</li><li>捐赠 AAIF，推动跨厂商生态</li></ul></article>
          <article class="product-card"><span class="product-icon">E</span><h3>企业与教育</h3><p>围绕身份、权限、治理、采购和组织学习扩展。</p><ul><li>Team、Enterprise、Education</li><li>SSO、SCIM、审计、数据保留与私有市场</li><li>K–12 教师与高等教育场景</li></ul></article>
        </div>
      </div>
    </section>

    <section class="section container" id="plans">
      <div class="section-head"><div><span class="kicker">Plans & commercialization</span><h2>订阅计划：从个人容量，到组织代理平台</h2></div><p class="section-intro">以下为美国公开页面、截至 __CUTOFF__ 的价格口径；实际价格、税费、可用模型和用量以账户地区与企业合同为准。</p></div>
      <div class="plan-grid">
        <article class="plan"><h3>Free</h3><div class="price-big">$0</div><p>Claude 基础入口，适合低频个人使用；用量、模型和高级功能受限。</p></article>
        <article class="plan plan--accent"><h3>Pro</h3><div class="price-big">$20/月</div><p>年付 $200（折合约 $17/月）。更高用量，覆盖主流个人生产力功能。</p></article>
        <article class="plan"><h3>Max</h3><div class="price-big">$100 / $200</div><p>5× 与 20× 两档月度容量，面向高频个人用户和代理工作流。</p></article>
        <article class="plan"><h3>Team</h3><div class="price-big">$20 起/席/月</div><p>Standard：年付 $20、月付 $25；Premium：年付 $100、月付 $125。</p></article>
        <article class="plan"><h3>Enterprise</h3><div class="price-big">$20/席/月 + 用量</div><p>自助公开口径起价，另按使用计费；更完整的管理、安全和支持能力。</p></article>
        <article class="plan"><h3>Education</h3><div class="price-big">定制报价</div><p>学校级部署、学习模式、校园治理和培训支持。</p></article>
        <article class="plan"><h3>历史：Pro</h3><div class="price-big">2023-09</div><p>第一次把 Claude 从免费研究产品明确转为个人订阅服务。</p></article>
        <article class="plan"><h3>历史：Max</h3><div class="price-big">2025-04</div><p>用“高容量而非功能解锁”服务 Claude Code 与高频专业用户。</p></article>
      </div>
      <div class="official-links"><a href="https://claude.com/pricing" target="_blank" rel="noopener noreferrer">核对 Claude 官方订阅价格 ↗</a></div>
    </section>

    <section class="section section--tint" id="api">
      <div class="container">
        <div class="section-head"><div><span class="kicker">API pricing snapshot</span><h2>当前 API 主线模型与标准价格</h2></div><p class="section-intro">单位为每百万 tokens 的标准输入 / 输出美元价格；不含 Batch、Prompt Caching、Fast mode、区域端点或云平台差异。</p></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>模型</th><th>定位</th><th>标准输入</th><th>标准输出</th><th>适合</th></tr></thead>
            <tbody>
              <tr><td><strong>Claude Fable 5.1</strong></td><td>前沿通用</td><td class="price">$10</td><td class="price">$50</td><td>最高能力研究、复杂多领域任务</td></tr>
              <tr><td><strong>Claude Mythos 5.1</strong></td><td>可信访问前沿模型</td><td class="price">$10</td><td class="price">$50</td><td>经审核的网络安全、生命科学研究</td></tr>
              <tr><td><strong>Claude Opus 5.5</strong></td><td>高端代理与复杂知识工作</td><td class="price">$4</td><td class="price">$20</td><td>长时编码代理、复杂分析、关键任务</td></tr>
              <tr><td><strong>Claude Sonnet 5.5</strong></td><td>主力平衡型</td><td class="price">$2</td><td class="price">$10</td><td>规模化编码、日常代理与办公交付</td></tr>
              <tr><td><strong>Claude Haiku 5.5</strong><br>≤100K 输入</td><td>低延迟、高吞吐</td><td class="price">$0.10</td><td class="price">$0.50</td><td>分类、压缩、客服、子代理</td></tr>
              <tr><td><strong>Claude Haiku 5.5</strong><br>&gt;100K 输入</td><td>长上下文小模型</td><td class="price">$0.50</td><td class="price">$2.50</td><td>低成本长文档与高吞吐代理</td></tr>
            </tbody>
          </table>
        </div>
        <div class="callout"><strong>选型原则：</strong>先按“完成一个任务的总成本”评估，而不是只看 token 单价。更强模型可能以更少重试、更短轨迹和更高一次成功率降低实际成本；高并发、窄任务则更适合 Haiku。</div>
        <div class="official-links"><a href="https://platform.claude.com/docs/en/about-claude/pricing" target="_blank" rel="noopener noreferrer">核对 Claude Platform 官方定价 ↗</a></div>
      </div>
    </section>

    <section class="section container" id="migration">
      <div class="section-head"><div><span class="kicker">Deprecation & migration</span><h2>模型会退役，迁移能力必须常态化</h2></div><p class="section-intro">Anthropic 采用“宣布弃用—迁移窗口—正式退役”的机制。旧模型可能仍在第三方云平台存在一段时间，但 Anthropic 自营 API 的时间表应单独跟踪。</p></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>旧路线</th><th>关键状态</th><th>建议迁移方向</th><th>主要变化</th></tr></thead>
          <tbody>
            <tr><td>Claude 1 / Instant</td><td>早期世代已退出主线</td><td>Haiku / Sonnet 新版本</td><td>更强指令遵循、多模态、工具与更成熟安全性</td></tr>
            <tr><td>Claude 2 / 2.1 / Claude 3 Sonnet</td><td>2025 进入弃用与退役流程</td><td>当期 Sonnet</td><td>从通用单模型迁移到家族化、代理优化模型</td></tr>
            <tr><td>Claude 3 Haiku / 3.5 Haiku</td><td>2025—2026 分批弃用</td><td>Haiku 4.5 / 5.5</td><td>更高吞吐、更低单位任务成本与更强代理能力</td></tr>
            <tr><td>Claude 4 / Sonnet 4 / Opus 4.1</td><td>2026 分批退役</td><td>5.x / 5.5 对应档</td><td>长时代理、速度、成本与安全分发全面升级</td></tr>
            <tr><td>Sonnet 4.5</td><td>2026-09-30 宣布弃用；计划 2026-11-30 退役</td><td>Sonnet 5.5</td><td>更快、单位任务成本更低，办公与视觉能力增强</td></tr>
          </tbody>
        </table>
      </div>
      <div class="official-links"><a href="https://platform.claude.com/docs/en/about-claude/model-deprecations" target="_blank" rel="noopener noreferrer">核对最新模型弃用与退役时间表 ↗</a></div>
      <div class="migration-flow" aria-label="建议的模型迁移流程">
        <article class="migration-step"><strong>建立清单</strong><span>记录模型 ID、区域、云平台、提示词、工具与业务负责人。</span></article>
        <article class="migration-step"><strong>固定评测</strong><span>用真实任务集比较成功率、轨迹长度、延迟和总成本。</span></article>
        <article class="migration-step"><strong>双跑灰度</strong><span>短期并行旧新模型，检查格式、拒答、工具参数和边界行为。</span></article>
        <article class="migration-step"><strong>监控切换</strong><span>在退役日前完成流量切换，并持续观察质量与费用漂移。</span></article>
      </div>
    </section>

    <section class="section section--tint" id="insights">
      <div class="container">
        <div class="section-head"><div><span class="kicker">Strategic shifts</span><h2>六个真正重要的转折</h2></div><p class="section-intro">把 86 条更新压缩成判断 Claude 路线的六个长期信号。</p></div>
        <div class="insight-grid">
          <article class="insight"><b>01 · 安全成为产品架构</b><h3>从 Constitutional AI 到分级可信访问</h3><p>安全从训练方法和宪法，演进为 Fable / Mythos、验证计划、管理员权限与数据治理。</p></article>
          <article class="insight"><b>02 · 长上下文成为长时工作</b><h3>100K 不是终点</h3><p>上下文窗口扩大只是基础；compaction、memory、持续线程和远程 Dispatch 才让模型真正持续工作。</p></article>
          <article class="insight"><b>03 · 中档模型反复改写旗舰定义</b><h3>Sonnet 把前沿能力快速大众化</h3><p>3.5 Sonnet 超越旧 Opus 后，Sonnet 一直承担能力下放、速度和成本平衡的主力角色。</p></article>
          <article class="insight"><b>04 · API 走向代理操作系统</b><h3>模型之外，工具层成为差异化</h3><p>Tool Use、MCP、Computer Use、Files、Skills 与搜索让开发平台从推理接口变成代理运行底座。</p></article>
          <article class="insight"><b>05 · Claude Code 是产品方法验证场</b><h3>先在代码里验证，再扩展到所有工作</h3><p>子代理、持续执行、权限、插件和观测先在编码场景成熟，再通过 Cowork 进入通用知识工作。</p></article>
          <article class="insight"><b>06 · 交付物替代聊天记录</b><h3>Artifacts 演化为成果平台</h3><p>Docs、Slides、Design、Dashboards 与 Motion 表明终点不是更长回答，而是可编辑、可协作、可持续更新的成果。</p></article>
        </div>
      </div>
    </section>

    <section class="section container" id="method">
      <div class="section-head"><div><span class="kicker">Method</span><h2>资料口径与阅读提醒</h2></div><p class="section-intro">本页优先使用 Anthropic、Claude、Claude Platform 和 Claude Help Center 官方页面。官方社交账号只作为发现线索，不用二手媒体替代原始发布。</p></div>
      <div class="notes">
        <article class="panel"><h3>收录原则</h3><ul><li>收录会改变能力、产品形态、商业计划、开发方式或迁移要求的更新。</li><li>同日模型与产品变化在必要时拆成两条，便于按类别筛选。</li><li>相对前代差异来自官方发布内容的结构化归纳，不等同于完整技术评测。</li><li>时间线自动更新至 <strong>__CUTOFF__</strong>；该日期之后的信息不在当前快照范围内。</li></ul></article>
        <article class="panel"><h3>不确定性与价格</h3><ul><li>“Beta / Research Preview / GA”按发布当日状态记录，后续状态可在新事件中更新。</li><li>模型 ID 日期、官方新闻页日期偶有一天差异；本页以公开新闻页展示日期为主。</li><li>订阅和 API 价格以美国公开网页为快照，地区、合同、缓存、批处理和云平台价格可能不同。</li><li>退役日期需以 Anthropic 最新 deprecations 页面复核后再执行生产迁移。</li></ul></article>
      </div>
    </section>

    <section class="section section--tint" id="sources">
      <div class="container">
        <div class="section-head"><div><span class="kicker">Official sources</span><h2>官方来源索引</h2></div><p class="section-intro">共 __SOURCE_COUNT__ 个去重来源页。索引按时间倒序，点击将在新窗口打开官方原文。</p></div>
        <ol class="source-index">__SOURCE_INDEX__</ol>
      </div>
    </section>
  </main>

  <footer><div class="container"><strong>Claude 演进全景</strong><br>整理截止 __CUTOFF__ · 以官方公开资料为主</div></footer>
  <button class="back-top" id="back-top" type="button" aria-label="返回页面顶部">↑</button>

  <script id="timeline-data" type="application/json">__TIMELINE_DATA__</script>
  <script>
    (() => {
      "use strict";
      const events = JSON.parse(document.getElementById("timeline-data").textContent);
      const list = document.getElementById("timeline-list");
      const empty = document.getElementById("empty-state");
      const count = document.getElementById("result-count");
      const query = document.getElementById("query");
      const year = document.getElementById("year-filter");
      const category = document.getElementById("category-filter");
      const sort = document.getElementById("sort-order");
      const reset = document.getElementById("reset-filters");
      const toggleDetails = document.getElementById("toggle-details");
      const themeToggle = document.getElementById("theme-toggle");
      const backTop = document.getElementById("back-top");
      let allExpanded = false;

      const colors = {
        "研究基础":"#8a6132", "模型":"#c35f35", "Claude 应用":"#365f83",
        "开发者/API":"#4d7560", "智能体/编码":"#675178", "订阅计划":"#9a681f",
        "企业与教育":"#347178", "安全与治理":"#9a4d43", "下线/迁移":"#7b665e"
      };

      // 用纯 DOM API 生成事件卡片，避免把来源数据直接拼接为可执行 HTML。
      function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
      }

      function createDetail(label, value) {
        const box = el("div", "detail-item");
        const dt = el("dt", "", label);
        const dd = el("dd", "", value);
        box.append(dt, dd);
        return box;
      }

      function createEventCard(event) {
        const row = el("article", "event");
        row.style.setProperty("--category", colors[event.category] || "var(--accent)");
        const dateNode = el("time", "event-date", event.date);
        dateNode.dateTime = event.date;
        const card = el("div", "event-card");
        const main = el("div", "event-main");
        const meta = el("div", "event-meta");
        meta.append(el("span", "badge", event.category));
        if (event.autoGenerated) meta.append(el("span", "badge", event.verification || "自动收录"));
        const title = el("h3", "", event.title);
        const summary = el("p", "event-summary", event.summary);
        main.append(meta, title, summary);

        const details = el("details");
        const detailsSummary = el("summary", "", "查看相对变化与详细信息");
        const detailGrid = el("dl", "event-details");
        detailGrid.append(
          createDetail("相对前一阶段", event.delta),
          createDetail("重点优化", event.optimization),
          createDetail("适用范围", event.availability),
          createDetail("为什么重要", event.significance)
        );
        const source = el("a", "source-link");
        source.href = event.sourceUrl;
        source.target = "_blank";
        source.rel = "noopener noreferrer";
        source.append(el("span", "", "官方来源：" + event.sourceLabel), el("span", "", "打开原文 ↗"));
        detailGrid.append(source);
        details.append(detailsSummary, detailGrid);
        card.append(main, details);
        row.append(dateNode, card);
        return row;
      }

      // 根据搜索与筛选条件重建按年份分组的时间线。
      function render() {
        const needle = query.value.trim().toLocaleLowerCase("zh-CN");
        const selectedYear = year.value;
        const selectedCategory = category.value;
        const filtered = events.filter((event) => {
          if (selectedYear && !event.date.startsWith(selectedYear)) return false;
          if (selectedCategory && event.category !== selectedCategory) return false;
          if (!needle) return true;
          return Object.values(event).join(" ").toLocaleLowerCase("zh-CN").includes(needle);
        }).sort((a, b) => sort.value === "asc" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));

        list.replaceChildren();
        let currentYear = "";
        for (const event of filtered) {
          const eventYear = event.date.slice(0, 4);
          if (eventYear !== currentYear) {
            currentYear = eventYear;
            const heading = el("div", "year-heading");
            heading.append(el("h3", "", currentYear), el("span", "", filtered.filter((item) => item.date.startsWith(currentYear)).length + " 条关键更新"));
            list.append(heading);
          }
          const card = createEventCard(event);
          card.querySelector("details").open = allExpanded;
          list.append(card);
        }
        count.textContent = `显示 ${filtered.length} / ${events.length} 条事件`;
        empty.hidden = filtered.length !== 0;
        list.hidden = filtered.length === 0;
        updateHash();
      }

      function updateHash() {
        const params = new URLSearchParams();
        if (query.value) params.set("q", query.value);
        if (year.value) params.set("year", year.value);
        if (category.value) params.set("category", category.value);
        if (sort.value !== "asc") params.set("sort", sort.value);
        history.replaceState(null, "", params.size ? `#timeline?${params}` : "#timeline");
      }

      function loadHash() {
        const marker = "#timeline?";
        if (!location.hash.startsWith(marker)) return;
        const params = new URLSearchParams(location.hash.slice(marker.length));
        query.value = params.get("q") || "";
        year.value = params.get("year") || "";
        category.value = params.get("category") || "";
        sort.value = params.get("sort") || "asc";
      }

      [query, year, category, sort].forEach((control) => control.addEventListener(control === query ? "input" : "change", render));
      reset.addEventListener("click", () => {
        query.value = ""; year.value = ""; category.value = ""; sort.value = "asc"; allExpanded = false;
        toggleDetails.textContent = "展开全部"; render(); query.focus();
      });
      toggleDetails.addEventListener("click", () => {
        allExpanded = !allExpanded;
        document.querySelectorAll(".event-card details").forEach((detail) => { detail.open = allExpanded; });
        toggleDetails.textContent = allExpanded ? "收起全部" : "展开全部";
      });
      document.querySelectorAll("[data-year-jump]").forEach((button) => button.addEventListener("click", () => {
        year.value = button.dataset.yearJump; render(); document.getElementById("timeline").scrollIntoView();
      }));

      const savedTheme = localStorage.getItem("claude-panorama-theme");
      if (savedTheme) document.documentElement.dataset.theme = savedTheme;
      themeToggle.addEventListener("click", () => {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        localStorage.setItem("claude-panorama-theme", next);
      });
      backTop.addEventListener("click", () => window.scrollTo({top:0, behavior:"smooth"}));
      window.addEventListener("scroll", () => backTop.classList.toggle("is-visible", window.scrollY > 800), {passive:true});

      loadHash();
      render();
    })();
  </script>
</body>
</html>
'''

    replacements = {
        "__CUTOFF__": cutoff,
        "__EVENT_COUNT__": str(len(events)),
        "__CATEGORY_COUNT__": str(len(category_counter)),
        "__SOURCE_COUNT__": str(len(unique_sources)),
        "__STAT_BARS__": make_stat_bars(category_counter, len(events)),
        "__YEAR_DISTRIBUTION__": make_year_distribution(year_counter),
        "__YEAR_OPTIONS__": year_options,
        "__CATEGORY_OPTIONS__": category_options,
        "__SOURCE_INDEX__": make_source_index(events),
        "__TIMELINE_DATA__": timeline_json,
        "__LAST_CHECKED__": last_checked,
    }
    for marker, value in replacements.items():
        document = document.replace(marker, value)
    return document


def main() -> None:
    """执行完整构建并输出生成结果摘要。"""
    data = load_and_validate_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = build_html(data)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"已生成：{OUTPUT_PATH}")
    print(f"事件数：{len(data['events'])}；文件大小：{OUTPUT_PATH.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
