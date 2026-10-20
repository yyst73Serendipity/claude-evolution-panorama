"""
自动检查 Anthropic 与 Claude 官方来源，把新发布和受监控页面变更合并进时间线，并保留可审计的自动收录标记。
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import os
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "work" / "timeline-data.json"
CONFIG_PATH = ROOT / "work" / "source-config.json"
STATE_PATH = ROOT / "work" / "source-state.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
OFFICIAL_HOSTS = {
    "anthropic.com",
    "www.anthropic.com",
    "claude.com",
    "www.claude.com",
    "support.claude.com",
    "platform.claude.com",
}
RELEASE_SIGNALS = (
    "introducing", "introduce", "launch", "available", "availability", "release", "released",
    "new claude", "now works", "generally available", "beta", "preview", "update", "upgrade",
    "claude opus", "claude sonnet", "claude haiku", "claude fable", "claude mythos",
)


class MetadataParser(HTMLParser):
    """提取页面 title、meta、JSON-LD 和稳定可见文本。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.ignored_depth = 0
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.json_ld_parts: list[str] = []
        self.in_json_ld = False
        self.visible_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self.in_title = True
        if tag in {"script", "style", "svg", "noscript"}:
            self.ignored_depth += 1
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.in_json_ld = True
            self.json_ld_parts = []
        if tag == "meta":
            key = values.get("property") or values.get("name")
            content = values.get("content", "").strip()
            if key and content:
                self.meta[key.lower()] = content
        if tag == "time" and values.get("datetime"):
            self.meta.setdefault("time:datetime", values["datetime"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "script" and self.in_json_ld:
            self.in_json_ld = False
        if tag in {"script", "style", "svg", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_json_ld:
            self.json_ld_parts.append(data)
        if self.ignored_depth == 0:
            text = " ".join(data.split())
            if text:
                self.visible_parts.append(text)


def canonical_url(url: str) -> str:
    """移除查询参数、片段和尾部斜杠，生成用于去重的官方页面地址。"""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def parse_sitemap(xml_text: str) -> list[dict[str, str]]:
    """解析带或不带 XML 命名空间的 sitemap URL 条目。"""
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] not in {"url", "sitemap"}:
            continue
        values: dict[str, str] = {"url": "", "lastmod": ""}
        for child in node:
            name = child.tag.rsplit("}", 1)[-1]
            if name == "loc":
                values["url"] = (child.text or "").strip()
            elif name == "lastmod":
                values["lastmod"] = (child.text or "").strip()[:10]
        if values["url"]:
            items.append(values)
    return items


def extract_json_dates(value: object) -> list[str]:
    """递归提取 JSON-LD 中的发布日期字段。"""
    dates: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"datePublished", "dateCreated"} and isinstance(item, str):
                dates.append(item[:10])
            else:
                dates.extend(extract_json_dates(item))
    elif isinstance(value, list):
        for item in value:
            dates.extend(extract_json_dates(item))
    return dates


def parse_page_metadata(page: str, url: str) -> dict[str, str]:
    """从官方页面提取标题、描述、发布日期及用于稳定变更检测的正文摘要。"""
    parser = MetadataParser()
    parser.feed(page)
    raw_title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or " ".join(parser.title_parts)
    title = re.sub(r"\s*[|–—-]\s*(Anthropic|Claude)\s*$", "", raw_title, flags=re.IGNORECASE).strip()
    description = (
        parser.meta.get("og:description")
        or parser.meta.get("twitter:description")
        or parser.meta.get("description")
        or ""
    ).strip()
    dates: list[str] = []
    if parser.json_ld_parts:
        try:
            dates.extend(extract_json_dates(json.loads("".join(parser.json_ld_parts))))
        except json.JSONDecodeError:
            pass
    for key in ("article:published_time", "date", "time:datetime"):
        value = parser.meta.get(key)
        if value:
            dates.append(value[:10])
    valid_dates = [item for item in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", item)]
    visible = " ".join(parser.visible_parts)
    visible = re.sub(r"\s+", " ", html_module.unescape(visible)).strip()
    return {
        "url": canonical_url(url),
        "title": title or urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title(),
        "description": description,
        "date": valid_dates[0] if valid_dates else "",
        "stableText": visible[:100_000],
    }


def classify_event(text: str) -> str:
    """依据具体产品关键词将官方更新归入现有九类。"""
    normalized = text.casefold()
    if "api" in normalized and any(keyword in normalized for keyword in ("pricing", "price", "cost")):
        return "开发者/API"
    rules = (
        ("下线/迁移", ("deprecat", "retire", "sunset", "migration")),
        ("智能体/编码", ("claude code", "code review", "cowork", "computer use", "dispatch", "agent")),
        ("订阅计划", ("pricing", "price", "plan", "subscription", "pro plan", "max plan", "team plan")),
        ("企业与教育", ("enterprise", "education", "university", "school", "teacher")),
        ("安全与治理", ("constitution", "safety", "security", "responsible scaling", "verification program")),
        ("开发者/API", ("api", "console", "mcp", "model context protocol", "sdk", "tool use", "prompt caching", "batch")),
        ("模型", ("model", "opus", "sonnet", "haiku", "fable", "mythos", "extended thinking", "context window")),
        ("Claude 应用", ("claude.ai", "claude app", "artifacts", "projects", "research", "integrations", "google docs", "slides", "dashboards", "motion", "design")),
    )
    for category, keywords in rules:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "Claude 应用"


def clean_summary(description: str, title: str) -> str:
    """把页面元描述压缩成一段保守摘要。"""
    summary = re.sub(r"\s+", " ", html_module.unescape(description)).strip()
    if not summary:
        summary = f"官方发布“{title}”，具体能力、范围与限制请以原文为准。"
    if len(summary) > 360:
        summary = summary[:357].rstrip() + "…"
    return summary


def make_event(metadata: dict[str, str], source_label: str, category: str | None = None) -> dict:
    """把官方页面元数据转换为明确标注“自动收录”的时间线事件。"""
    title = metadata["title"].strip()
    summary = clean_summary(metadata.get("description", ""), title)
    inferred_category = category or classify_event(f"{title} {summary}")
    return {
        "date": metadata["date"],
        "precision": "day",
        "category": inferred_category,
        "title": title,
        "summary": summary,
        "delta": "自动更新器确认官方新增或修改了此发布信息；相对前代的量化变化应以链接中的官方原文为准。",
        "optimization": "依据官方标题与摘要自动归类，未对原文未明确说明的性能提升作推断。",
        "availability": "请查看官方原文中的计划、地区、平台、Beta/GA 状态与开放范围。",
        "significance": "该条目来自官方来源并由自动化流程收录；分析字段采用保守表述，避免把非官方推断写成事实。",
        "sourceLabel": source_label,
        "sourceUrl": canonical_url(metadata["url"]),
        "autoGenerated": True,
        "verification": "自动收录",
    }


def merge_events(existing: list[dict], candidates: list[dict], cutoff: str) -> tuple[list[dict], int]:
    """按规范化 URL 去重，只接纳不晚于截止日期且晚于现有时间线的新事件。"""
    known = {canonical_url(event["sourceUrl"]) for event in existing}
    latest_existing = max((event["date"] for event in existing), default="0001-01-01")
    added = 0
    merged = list(existing)
    for event in candidates:
        url = canonical_url(event["sourceUrl"])
        event_date = event.get("date", "")
        if url in known or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
            continue
        if event_date > cutoff or event_date <= latest_existing:
            continue
        event["sourceUrl"] = url
        merged.append(event)
        known.add(url)
        added += 1
    merged.sort(key=lambda item: (item["date"], item["title"]))
    return merged, added


def atomic_write_json(path: Path, value: dict) -> None:
    """先写同目录临时文件再替换，避免中断导致 JSON 损坏。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_update(data_path: Path, state_path: Path, data: dict, state: dict) -> None:
    """原子写入时间线与监控状态。"""
    atomic_write_json(data_path, data)
    atomic_write_json(state_path, state)


def fetch_text(url: str, user_agent: str, retries: int = 3) -> str:
    """仅抓取允许的官方 HTTPS 页面，并对短暂网络错误有限重试。"""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise ValueError(f"拒绝访问非官方来源：{url}")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read(5_000_000).decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("无法完成官方页面请求")


def discover_sitemap_items(source: dict, user_agent: str) -> list[dict[str, str]]:
    """展开 sitemap index，并筛选配置允许的官方文章路径。"""
    pending = [source["sitemap"]]
    visited: set[str] = set()
    discovered: list[dict[str, str]] = []
    while pending and len(visited) < 20:
        sitemap_url = pending.pop(0)
        if sitemap_url in visited:
            continue
        visited.add(sitemap_url)
        for item in parse_sitemap(fetch_text(sitemap_url, user_agent)):
            parsed = urlparse(item["url"])
            if parsed.path.endswith(".xml") or "sitemap" in parsed.path.casefold():
                if parsed.hostname in source["allowedHosts"]:
                    pending.append(item["url"])
                continue
            if parsed.hostname not in source["allowedHosts"]:
                continue
            if any(parsed.path.startswith(prefix) for prefix in source["pathPrefixes"]):
                discovered.append(item)
    return discovered


def is_relevant_release(metadata: dict[str, str], required_keywords: list[str]) -> bool:
    """过滤教程和一般企业新闻，仅保留具有发布信号的 Claude 相关页面。"""
    text = f"{metadata['title']} {metadata['description']}".casefold()
    return any(keyword.casefold() in text for keyword in required_keywords) and any(signal in text for signal in RELEASE_SIGNALS)


def content_hash(text: str) -> str:
    """对归一化可见文本计算摘要，降低格式和空白变化产生的噪声。"""
    normalized = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", text)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def append_changelog(events: list[dict], checked_at: str) -> None:
    """把自动新增事件追加到可审计的更新日志顶部。"""
    if not events:
        return
    existing = CHANGELOG_PATH.read_text(encoding="utf-8") if CHANGELOG_PATH.exists() else "# 更新日志\n\n"
    lines = [f"## {checked_at[:10]} 自动更新", ""]
    lines.extend(f"- **{event['date']} · {event['category']}**：[{event['title']}]({event['sourceUrl']})" for event in events)
    block = "\n".join(lines) + "\n\n"
    if existing.startswith("# 更新日志\n"):
        existing = existing[len("# 更新日志\n"):].lstrip("\n")
    CHANGELOG_PATH.write_text("# 更新日志\n\n" + block + existing, encoding="utf-8")


def run_update(today: str | None = None) -> int:
    """执行发现、页面监控、合并和状态持久化，返回新增事件数。"""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {"knownUrls": [], "pageHashes": {}}
    timezone = ZoneInfo(config.get("timezone", "Asia/Shanghai"))
    now = datetime.now(timezone)
    current_date = today or now.date().isoformat()
    checked_at = now.isoformat(timespec="seconds")
    previous_cutoff = data.get("cutoff", "0001-01-01")
    candidates: list[dict] = []
    known_urls = set(state.get("knownUrls", [])) | {canonical_url(item["sourceUrl"]) for item in data["events"]}

    for source in config["discoverySources"]:
        for item in discover_sitemap_items(source, config["userAgent"]):
            url = canonical_url(item["url"])
            if url in known_urls:
                continue
            try:
                metadata = parse_page_metadata(fetch_text(url, config["userAgent"]), url)
            except (ValueError, urllib.error.URLError, ET.ParseError) as error:
                print(f"警告：无法读取 {url}：{error}")
                continue
            metadata["date"] = metadata["date"] or item.get("lastmod", "")
            known_urls.add(url)
            if metadata["date"] <= previous_cutoff or metadata["date"] > current_date:
                continue
            if is_relevant_release(metadata, source["requiredKeywords"]):
                candidates.append(make_event(metadata, source["name"]))

    page_hashes = dict(state.get("pageHashes", {}))
    for page_config in config["monitoredPages"]:
        url = canonical_url(page_config["url"])
        page = fetch_text(url, config["userAgent"])
        metadata = parse_page_metadata(page, url)
        digest = content_hash(metadata["stableText"])
        old_digest = page_hashes.get(url)
        page_hashes[url] = digest
        known_urls.add(url)
        if old_digest and old_digest != digest:
            metadata.update({
                "date": current_date,
                "title": f"{page_config['name']}发生更新",
                "description": f"自动监控检测到“{page_config['name']}”官方页面的稳定可见内容发生变化。页面已重新抓取；具体条款、价格或时间表以官方原文为准。",
            })
            candidates.append(make_event(metadata, page_config["label"], page_config["category"]))

    merged, added = merge_events(data["events"], candidates, current_date)
    accepted_urls = {canonical_url(event["sourceUrl"]) for event in merged}
    added_events = [event for event in merged if canonical_url(event["sourceUrl"]) not in {canonical_url(item["sourceUrl"]) for item in data["events"]}]
    data["events"] = merged
    if added:
        data["cutoff"] = current_date
        data["lastChecked"] = checked_at
    state = {
        "lastChecked": checked_at,
        "knownUrls": sorted(known_urls | accepted_urls),
        "pageHashes": page_hashes,
    }
    write_update(DATA_PATH, STATE_PATH, data, state)
    append_changelog(added_events, checked_at)
    print(f"检查完成：候选 {len(candidates)} 条，新增 {added} 条，时间线共 {len(merged)} 条。")
    return added


def main() -> None:
    """解析命令行参数并运行自动更新。"""
    parser = argparse.ArgumentParser(description="自动检查并更新 Claude 演进全景数据")
    parser.add_argument("--today", help="测试或补跑使用的北京时间日期，格式 YYYY-MM-DD")
    args = parser.parse_args()
    run_update(args.today)


if __name__ == "__main__":
    main()
