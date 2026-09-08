#!/usr/bin/env python3
"""Assemble the captured Ucuzabilet homepage into a self-contained local copy."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / ".capture"
SOURCE_HTML = CAPTURE / "source-homepage.html"
CDP_MANIFEST = CAPTURE / "cdp-resources.json"
NETWORK_MANIFEST = CAPTURE / "network-resources.json"
CDP_FILES = CAPTURE / "cdp-resources"
NETWORK_FILES = CAPTURE / "network-resources"
PAGE_ASSET_DIRS = [CAPTURE / "browser-assets", CAPTURE / "browser-assets-campaign"]
MANUAL_RESOURCE_DIR = CAPTURE / "manual-resources"
CSS_DEPENDENCY_DIR = CAPTURE / "css-dependencies"
COMPONENT_DIR = Path(__file__).resolve().parent / "components"
OUTPUT_ASSETS = ROOT / "assets"
BASE_URL = "https://www.ucuzabilet.com/"
STATIC_ALIASES = {
    "https://www.ucuzabilet.com/resources/ub/js/v2/libs/utils.js": "resources/ub/js/v2/libs/utils.js",
    "https://www.ucuzabilet.com/special-days-list": "special-days-list",
    "https://www.ucuzabilet.com/firebase-messaging-sw.js?v=1.4.6": "firebase-messaging-sw.js",
}


CSS_URL_RE = re.compile(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", re.IGNORECASE)
CSS_IMPORT_RE = re.compile(
    r"(@import\s+(?:url\(\s*)?[\"']?)([^\"')\s;]+)([\"']?\s*\)?\s*;)",
    re.IGNORECASE,
)
HTML_ATTR_RE = re.compile(
    r"(?P<prefix>\b(?:src|href|poster|data-src|data-original|data-lazy-src|data-background|data-bg)\s*=\s*[\"'])"
    r"(?P<url>[^\"']+)"
    r"(?P<suffix>[\"'])",
    re.IGNORECASE,
)
HTML_SRCSET_RE = re.compile(
    r"(?P<prefix>\b(?:srcset|data-srcset)\s*=\s*[\"'])(?P<value>[^\"']+)(?P<suffix>[\"'])",
    re.IGNORECASE,
)


def safe_name(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    candidate = unquote(Path(parsed.path).name) or fallback
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    return (candidate or fallback)[:100]


def copy_captures() -> tuple[dict[str, str], list[dict[str, object]]]:
    """Copy captured files into assets and return URL-to-local-path mappings."""
    if OUTPUT_ASSETS.exists():
        shutil.rmtree(OUTPUT_ASSETS)
    OUTPUT_ASSETS.mkdir(parents=True)

    url_map: dict[str, str] = {}
    records: list[dict[str, object]] = []

    def register(url: str, local: str) -> None:
        # The source markup sometimes contains literal spaces while the browser's
        # resource URL uses percent encoding. Keep both spellings addressable.
        url_map[url] = local
        url_map[unquote(url)] = local

    cdp = json.loads(CDP_MANIFEST.read_text(encoding="utf-8"))
    for item in cdp["captured"]:
        source = CDP_FILES / item["fileName"]
        if not source.exists():
            continue
        destination = OUTPUT_ASSETS / item["fileName"]
        shutil.copy2(source, destination)
        local = f"assets/{destination.name}"
        register(item["url"], local)
        records.append({**item, "localPath": local, "capture": "browser-cache"})

    network = json.loads(NETWORK_MANIFEST.read_text(encoding="utf-8"))
    for item in network["captured"]:
        if item["url"] in url_map:
            continue
        source = NETWORK_FILES / item["fileName"]
        if not source.exists():
            continue
        destination = OUTPUT_ASSETS / item["fileName"]
        shutil.copy2(source, destination)
        local = f"assets/{destination.name}"
        register(item["url"], local)
        records.append({**item, "localPath": local, "capture": "network-response"})

    for page_asset_dir in PAGE_ASSET_DIRS:
        page_assets = json.loads((page_asset_dir / "manifest.json").read_text(encoding="utf-8"))
        for item in page_assets["assets"]:
            url = item["url"]
            if url.startswith("inline-svg:") or url in url_map:
                continue
            source = page_asset_dir / Path(item["path"]).name
            if not source.exists():
                continue
            suffix = source.suffix or mimetypes.guess_extension(item.get("contentType") or "") or ""
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            name = safe_name(url, item.get("name") or f"resource{suffix}")
            if suffix and not name.lower().endswith(suffix.lower()):
                name += suffix
            destination = OUTPUT_ASSETS / f"{digest}-{name}"
            shutil.copy2(source, destination)
            local = f"assets/{destination.name}"
            register(url, local)
            records.append(
                {
                    "url": url,
                    "mimeType": item.get("contentType"),
                    "type": item.get("kind"),
                    "bytes": destination.stat().st_size,
                    "localPath": local,
                    "capture": "page-assets",
                }
            )

    for supplemental_dir, capture_name in (
        (MANUAL_RESOURCE_DIR, "direct-asset-download"),
        (CSS_DEPENDENCY_DIR, "css-dependency"),
    ):
        supplemental = json.loads((supplemental_dir / "manifest.json").read_text(encoding="utf-8"))
        for item in supplemental["assets"]:
            if item["url"] in url_map:
                continue
            source = supplemental_dir / item["fileName"]
            destination = OUTPUT_ASSETS / item["fileName"]
            shutil.copy2(source, destination)
            local = f"assets/{destination.name}"
            register(item["url"], local)
            records.append(
                {
                    **item,
                    "bytes": destination.stat().st_size,
                    "localPath": local,
                    "capture": capture_name,
                }
            )

    return url_map, records


def mapped_url(raw_url: str, base_url: str, url_map: dict[str, str], *, from_css: bool = False) -> str:
    value = raw_url.strip()
    if not value or value.startswith(("data:", "blob:", "#", "javascript:", "mailto:", "tel:")):
        return raw_url
    absolute = urljoin(base_url, value)
    local = url_map.get(absolute)
    if not local:
        return raw_url
    return Path(local).name if from_css else local


def rewrite_css(url_map: dict[str, str], records: list[dict[str, object]]) -> None:
    for record in records:
        if record.get("type") not in ("Stylesheet", "stylesheet"):
            continue
        css_path = ROOT / str(record["localPath"])
        try:
            css = css_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            css = css_path.read_text(encoding="latin-1")
        source_url = str(record["url"])

        def replace_url(match: re.Match[str]) -> str:
            original = match.group(2)
            replacement = mapped_url(original, source_url, url_map, from_css=True)
            return f"url({match.group(1)}{replacement}{match.group(1)})"

        def replace_import(match: re.Match[str]) -> str:
            replacement = mapped_url(match.group(2), source_url, url_map, from_css=True)
            return f"{match.group(1)}{replacement}{match.group(3)}"

        css = CSS_URL_RE.sub(replace_url, css)
        css = CSS_IMPORT_RE.sub(replace_import, css)
        css_path.write_text(css, encoding="utf-8")


def rewrite_html(html: str, url_map: dict[str, str]) -> str:
    def replace_attr(match: re.Match[str]) -> str:
        replacement = mapped_url(match.group("url"), BASE_URL, url_map)
        return f'{match.group("prefix")}{replacement}{match.group("suffix")}'

    def replace_srcset(match: re.Match[str]) -> str:
        candidates: list[str] = []
        for candidate in match.group("value").split(","):
            parts = candidate.strip().split()
            if parts:
                parts[0] = mapped_url(parts[0], BASE_URL, url_map)
            candidates.append(" ".join(parts))
        return f'{match.group("prefix")}{", ".join(candidates)}{match.group("suffix")}'

    html = HTML_ATTR_RE.sub(replace_attr, html)
    html = HTML_SRCSET_RE.sub(replace_srcset, html)

    # Inline CSS can contain background images that are not represented by attributes.
    def replace_inline_css(match: re.Match[str]) -> str:
        quote, value = match.group(1), match.group(2)
        return f"url({quote}{mapped_url(value, BASE_URL, url_map)}{quote})"

    return CSS_URL_RE.sub(replace_inline_css, html)


def apply_local_customizations(html: str) -> str:
    """Reapply approved local presentation changes after rebuilding the capture."""
    html = re.sub(
        r'\s*<div class="brand-web">\s*<img\b[^>]*\balt="brand ets"[^>]*>\s*</div>',
        "",
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'\s*<div class="brand-mobile d-lg-none">\s*<img\b[^>]*\balt="brand ets"[^>]*>\s*</div>',
        "",
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    supporting_copy = (
        "En uygun uçak bileti fiyatlarını karşılaştır; aktarmasız, tek yön veya "
        "gidiş dönüş seçeneklerinden sana uygun olanı seç ve biletini satın al."
    )
    if 'class="homepageHeaderSupport"' not in html:
        html = re.sub(
            r'(<h1 class="homepageHeaderH1 homepageHeaderH1-new">.*?</h1>)',
            rf'\1\n\t<p class="homepageHeaderSupport">{supporting_copy}</p>',
            html,
            count=1,
            flags=re.DOTALL,
        )
    # Cheapest-routes row between the campaign carousel and the mobile app banner.
    if 'class="row cheapestRoutesRow"' not in html:
        component = (COMPONENT_DIR / "cheapest-routes.html").read_text(encoding="utf-8")
        anchor = '<div class="mobileAppLanding">'
        html = html.replace(anchor, f"{component}{anchor}", 1)

    stylesheets = [
        '<link rel="stylesheet" href="header-overrides.css?v=4">',
        '<link rel="stylesheet" href="cheapest-routes.css?v=1">',
    ]
    for stylesheet in stylesheets:
        if stylesheet not in html:
            html = html.replace("</head>", f"    {stylesheet}\n</head>", 1)
    return html


def write_static_aliases(records: list[dict[str, object]]) -> None:
    """Place captured dynamic dependencies at the root-relative URLs used by the site's scripts."""
    by_url = {str(item["url"]): item for item in records}
    for url, alias in STATIC_ALIASES.items():
        item = by_url.get(url)
        if not item:
            continue
        source = ROOT / str(item["localPath"])
        destination = ROOT / alias
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    required = [SOURCE_HTML, CDP_MANIFEST, NETWORK_MANIFEST]
    required.extend(directory / "manifest.json" for directory in PAGE_ASSET_DIRS)
    required.append(MANUAL_RESOURCE_DIR / "manifest.json")
    required.append(CSS_DEPENDENCY_DIR / "manifest.json")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing capture inputs: " + ", ".join(missing))

    url_map, records = copy_captures()
    rewrite_css(url_map, records)
    write_static_aliases(records)

    source = SOURCE_HTML.read_text(encoding="utf-8")
    output = apply_local_customizations(rewrite_html(source, url_map))
    (ROOT / "index.html").write_text(output, encoding="utf-8")

    failures = {
        "browserCache": json.loads(CDP_MANIFEST.read_text(encoding="utf-8"))["failed"],
        "networkResponses": json.loads(NETWORK_MANIFEST.read_text(encoding="utf-8"))["failed"],
        "pageAssets": {
            directory.name: json.loads((directory / "manifest.json").read_text(encoding="utf-8"))["failures"]
            for directory in PAGE_ASSET_DIRS
        },
        "cssDependencies": json.loads((CSS_DEPENDENCY_DIR / "manifest.json").read_text(encoding="utf-8"))["failures"],
    }
    manifest = {
        "source": BASE_URL,
        "resourceCount": len(records),
        "resources": sorted(records, key=lambda item: str(item["url"])),
        "captureFailures": failures,
    }
    (OUTPUT_ASSETS / "asset-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote index.html ({(ROOT / 'index.html').stat().st_size:,} bytes)")
    print(f"Saved {len(records)} resources in {OUTPUT_ASSETS}")


if __name__ == "__main__":
    main()
