#!/usr/bin/env python3
"""Fetch secondary font and image URLs referenced by captured stylesheets."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MANIFEST = ASSETS / "asset-manifest.json"
OUTPUT = ROOT / ".capture" / "css-dependencies"
CSS_URL_RE = re.compile(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", re.IGNORECASE)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36"


def safe_name(url: str) -> str:
    name = unquote(Path(urlparse(url).path).name) or "resource"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "resource"
    return name[:100]


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    captured_urls = {item["url"] for item in data["resources"]}
    wanted: set[str] = set()

    for item in data["resources"]:
        if item.get("type") not in ("Stylesheet", "stylesheet"):
            continue
        css = (ROOT / item["localPath"]).read_text(encoding="utf-8", errors="ignore")
        for match in CSS_URL_RE.finditer(css):
            raw = match.group(2).strip()
            if not raw or raw.startswith(("data:", "blob:", "#")):
                continue
            if (ASSETS / raw).exists():
                continue
            url = urljoin(item["url"], raw)
            if url.startswith(("http://", "https://")) and url not in captured_urls:
                wanted.add(url)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for url in sorted(wanted):
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        name = safe_name(url)
        target = OUTPUT / f"{digest}-{name}"
        request = Request(url, headers={"User-Agent": USER_AGENT, "Referer": "https://www.ucuzabilet.com/"})
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                content_type = response.headers.get_content_type()
            if not Path(name).suffix:
                suffix = mimetypes.guess_extension(content_type) or ""
                target = target.with_name(target.name + suffix)
            target.write_bytes(body)
            assets.append(
                {
                    "url": url,
                    "fileName": target.name,
                    "mimeType": content_type,
                    "type": "font" if content_type.startswith("font/") or target.suffix in (".woff", ".woff2", ".ttf") else "image",
                    "bytes": len(body),
                }
            )
        except Exception as error:  # noqa: BLE001 - retain every failed URL in the capture report
            failures.append({"url": url, "error": str(error)})

    (OUTPUT / "manifest.json").write_text(
        json.dumps({"assets": assets, "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Fetched {len(assets)} CSS dependencies; {len(failures)} failed")
    for failure in failures:
        print(f"FAILED {failure['url']}: {failure['error']}")


if __name__ == "__main__":
    main()
