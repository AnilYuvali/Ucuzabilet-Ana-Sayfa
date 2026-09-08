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
LOCAL_ASSET_DIR = ROOT / "custom-assets"
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

    if LOCAL_ASSET_DIR.exists():
        for source in sorted(LOCAL_ASSET_DIR.iterdir()):
            if not source.is_file():
                continue
            destination = OUTPUT_ASSETS / source.name
            shutil.copy2(source, destination)
            records.append(
                {
                    "url": f"local-asset:{source.name}",
                    "mimeType": mimetypes.guess_type(source.name)[0],
                    "type": "local-asset",
                    "bytes": destination.stat().st_size,
                    "localPath": f"assets/{destination.name}",
                    "capture": "approved-local-asset",
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
    popular_flights_markup = """
<section class="popular-flight-deals" id="popular-flight-deals" aria-labelledby="popular-flight-deals-title">
  <div class="popular-flight-deals__header">
    <div>
      <span class="popular-flight-deals__eyebrow">Uçuş fırsatları</span>
      <h2 id="popular-flight-deals-title">En Ucuz Uçak Bileti Fırsatları</h2>
      <div class="popular-flight-deals__updated" aria-label="Fiyatların güncellenme tarihi ve saati">
        <i class="ubicon-dot-single" aria-hidden="true"></i>
        <span>Fiyatlar <strong data-summary-field="updated">1 Eylül 2026</strong>, <strong data-summary-field="updatedTime">10:23</strong> itibarıyla güncellendi</span>
      </div>
      <p>En çok aranan rotaları tek bakışta karşılaştır, seyahatine uygun fırsatı kolayca yakala.</p>
    </div>
  </div>

  <div class="popular-flight-deals__carousel" data-flight-carousel>
  <div class="popular-flight-deals__grid" data-flight-carousel-track tabindex="0" role="region" aria-label="Popüler uçuş fırsatları, yatay kaydırılabilir liste">
    <article class="popular-flight-card" data-deal-index="0">
      <a href="#searchForm" aria-label="İstanbul Antalya uçak bileti fırsatını incele">
        <div class="popular-flight-card__media">
          <img src="assets/popular-flight-antalya.png" width="560" height="315" loading="lazy" alt="Antalya kıyıları ve Akdeniz manzarası">
          <span class="popular-flight-card__badge" data-field="airline">SunExpress</span>
        </div>
        <div class="popular-flight-card__body">
          <div class="popular-flight-card__route">
            <span><strong data-field="originCode">IST</strong><small data-field="origin">İstanbul</small></span>
            <img src="assets/b0c4d3ab23b9-plane-departure.svg" width="22" height="22" alt="">
            <span><strong data-field="destinationCode">AYT</strong><small data-field="destination">Antalya</small></span>
          </div>
          <div class="popular-flight-card__date"><span class="popular-flight-card__date-icon" aria-hidden="true"><img src="assets/422772a5e45a-calendar.svg" width="10" height="11" alt=""></span><span><small>Uçuş tarihi</small><strong data-field="flightDate">9 Eylül 2026, Çarşamba</strong></span></div>
          <h3 data-field="title">En Ucuz İstanbul – Antalya Uçak Bileti</h3>
          <ul class="popular-flight-card__details" aria-label="Uçuş detayları">
            <li><i class="fa fa-clock-o" aria-hidden="true"></i><span><small>Uçuş süresi</small><strong data-field="duration">1 sa 10 dk</strong></span></li>
            <li><i class="fa fa-random" aria-hidden="true"></i><span><small>Aktarma</small><strong data-field="stops">Direkt</strong></span></li>
            <li><i class="fa fa-briefcase" aria-hidden="true"></i><span><small>Sınıf</small><strong data-field="cabin">Ekonomi</strong></span></li>
          </ul>
          <div class="popular-flight-card__footer">
            <span class="popular-flight-card__price"><strong data-field="price">1.179 TL</strong><small>’den başlayan</small></span>
            <span class="popular-flight-card__cta">Bileti incele <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="16" height="17" alt=""></span>
          </div>
        </div>
      </a>
    </article>

    <article class="popular-flight-card" data-deal-index="1">
      <a href="#searchForm" aria-label="İstanbul İzmir uçak bileti fırsatını incele">
        <div class="popular-flight-card__media">
          <img src="assets/popular-flight-izmir.png" width="560" height="315" loading="lazy" alt="İzmir Saat Kulesi ve Kordon manzarası">
          <span class="popular-flight-card__badge" data-field="airline">AJet</span>
        </div>
        <div class="popular-flight-card__body">
          <div class="popular-flight-card__route">
            <span><strong data-field="originCode">IST</strong><small data-field="origin">İstanbul</small></span>
            <img src="assets/b0c4d3ab23b9-plane-departure.svg" width="22" height="22" alt="">
            <span><strong data-field="destinationCode">ADB</strong><small data-field="destination">İzmir</small></span>
          </div>
          <div class="popular-flight-card__date"><span class="popular-flight-card__date-icon" aria-hidden="true"><img src="assets/422772a5e45a-calendar.svg" width="10" height="11" alt=""></span><span><small>Uçuş tarihi</small><strong data-field="flightDate">12 Eylül 2026, Cumartesi</strong></span></div>
          <h3 data-field="title">En Ucuz İstanbul – İzmir Uçak Bileti</h3>
          <ul class="popular-flight-card__details" aria-label="Uçuş detayları">
            <li><i class="fa fa-clock-o" aria-hidden="true"></i><span><small>Uçuş süresi</small><strong data-field="duration">1 sa 05 dk</strong></span></li>
            <li><i class="fa fa-random" aria-hidden="true"></i><span><small>Aktarma</small><strong data-field="stops">Direkt</strong></span></li>
            <li><i class="fa fa-briefcase" aria-hidden="true"></i><span><small>Sınıf</small><strong data-field="cabin">Ekonomi</strong></span></li>
          </ul>
          <div class="popular-flight-card__footer">
            <span class="popular-flight-card__price"><strong data-field="price">1.289 TL</strong><small>’den başlayan</small></span>
            <span class="popular-flight-card__cta">Bileti incele <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="16" height="17" alt=""></span>
          </div>
        </div>
      </a>
    </article>

    <article class="popular-flight-card" data-deal-index="2">
      <a href="#searchForm" aria-label="İstanbul Bodrum uçak bileti fırsatını incele">
        <div class="popular-flight-card__media">
          <img src="assets/popular-flight-bodrum.png" width="560" height="315" loading="lazy" alt="Bodrum koyu, beyaz evler ve kale manzarası">
          <span class="popular-flight-card__badge" data-field="airline">Pegasus</span>
        </div>
        <div class="popular-flight-card__body">
          <div class="popular-flight-card__route">
            <span><strong data-field="originCode">SAW</strong><small data-field="origin">İstanbul</small></span>
            <img src="assets/b0c4d3ab23b9-plane-departure.svg" width="22" height="22" alt="">
            <span><strong data-field="destinationCode">BJV</strong><small data-field="destination">Bodrum</small></span>
          </div>
          <div class="popular-flight-card__date"><span class="popular-flight-card__date-icon" aria-hidden="true"><img src="assets/422772a5e45a-calendar.svg" width="10" height="11" alt=""></span><span><small>Uçuş tarihi</small><strong data-field="flightDate">18 Eylül 2026, Cuma</strong></span></div>
          <h3 data-field="title">En Ucuz İstanbul – Bodrum Uçak Bileti</h3>
          <ul class="popular-flight-card__details" aria-label="Uçuş detayları">
            <li><i class="fa fa-clock-o" aria-hidden="true"></i><span><small>Uçuş süresi</small><strong data-field="duration">1 sa 15 dk</strong></span></li>
            <li><i class="fa fa-random" aria-hidden="true"></i><span><small>Aktarma</small><strong data-field="stops">Direkt</strong></span></li>
            <li><i class="fa fa-briefcase" aria-hidden="true"></i><span><small>Sınıf</small><strong data-field="cabin">Ekonomi</strong></span></li>
          </ul>
          <div class="popular-flight-card__footer">
            <span class="popular-flight-card__price"><strong data-field="price">1.499 TL</strong><small>’den başlayan</small></span>
            <span class="popular-flight-card__cta">Bileti incele <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="16" height="17" alt=""></span>
          </div>
        </div>
      </a>
    </article>

    <article class="popular-flight-card" data-deal-index="3">
      <a href="#searchForm" aria-label="İstanbul Ankara uçak bileti fırsatını incele">
        <div class="popular-flight-card__media">
          <img src="assets/popular-flight-ankara.png" width="560" height="315" loading="lazy" alt="Anıtkabir ve Ankara şehir manzarası">
          <span class="popular-flight-card__badge" data-field="airline">AJet</span>
        </div>
        <div class="popular-flight-card__body">
          <div class="popular-flight-card__route">
            <span><strong data-field="originCode">IST</strong><small data-field="origin">İstanbul</small></span>
            <img src="assets/b0c4d3ab23b9-plane-departure.svg" width="22" height="22" alt="">
            <span><strong data-field="destinationCode">ESB</strong><small data-field="destination">Ankara</small></span>
          </div>
          <div class="popular-flight-card__date"><span class="popular-flight-card__date-icon" aria-hidden="true"><img src="assets/422772a5e45a-calendar.svg" width="10" height="11" alt=""></span><span><small>Uçuş tarihi</small><strong data-field="flightDate">7 Eylül 2026, Pazartesi</strong></span></div>
          <h3 data-field="title">En Ucuz İstanbul – Ankara Uçak Bileti</h3>
          <ul class="popular-flight-card__details" aria-label="Uçuş detayları">
            <li><i class="fa fa-clock-o" aria-hidden="true"></i><span><small>Uçuş süresi</small><strong data-field="duration">1 sa 05 dk</strong></span></li>
            <li><i class="fa fa-random" aria-hidden="true"></i><span><small>Aktarma</small><strong data-field="stops">Direkt</strong></span></li>
            <li><i class="fa fa-briefcase" aria-hidden="true"></i><span><small>Sınıf</small><strong data-field="cabin">Ekonomi</strong></span></li>
          </ul>
          <div class="popular-flight-card__footer">
            <span class="popular-flight-card__price"><strong data-field="price">1.249 TL</strong><small>’den başlayan</small></span>
            <span class="popular-flight-card__cta">Bileti incele <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="16" height="17" alt=""></span>
          </div>
        </div>
      </a>
    </article>

    <article class="popular-flight-card" data-deal-index="4">
      <a href="#searchForm" aria-label="İstanbul Çukurova uçak bileti fırsatını incele">
        <div class="popular-flight-card__media">
          <img src="assets/popular-flight-cukurova.png" width="560" height="315" loading="lazy" alt="Seyhan Nehri, Taşköprü ve Adana şehir manzarası">
          <span class="popular-flight-card__badge" data-field="airline">Türk Hava Yolları</span>
        </div>
        <div class="popular-flight-card__body">
          <div class="popular-flight-card__route">
            <span><strong data-field="originCode">IST</strong><small data-field="origin">İstanbul</small></span>
            <img src="assets/b0c4d3ab23b9-plane-departure.svg" width="22" height="22" alt="">
            <span><strong data-field="destinationCode">COV</strong><small data-field="destination">Çukurova</small></span>
          </div>
          <div class="popular-flight-card__date"><span class="popular-flight-card__date-icon" aria-hidden="true"><img src="assets/422772a5e45a-calendar.svg" width="10" height="11" alt=""></span><span><small>Uçuş tarihi</small><strong data-field="flightDate">21 Eylül 2026, Pazartesi</strong></span></div>
          <h3 data-field="title">En Ucuz İstanbul – Çukurova Uçak Bileti</h3>
          <ul class="popular-flight-card__details" aria-label="Uçuş detayları">
            <li><i class="fa fa-clock-o" aria-hidden="true"></i><span><small>Uçuş süresi</small><strong data-field="duration">1 sa 30 dk</strong></span></li>
            <li><i class="fa fa-random" aria-hidden="true"></i><span><small>Aktarma</small><strong data-field="stops">Direkt</strong></span></li>
            <li><i class="fa fa-briefcase" aria-hidden="true"></i><span><small>Sınıf</small><strong data-field="cabin">Ekonomi</strong></span></li>
          </ul>
          <div class="popular-flight-card__footer">
            <span class="popular-flight-card__price"><strong data-field="price">1.379 TL</strong><small>’den başlayan</small></span>
            <span class="popular-flight-card__cta">Bileti incele <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="16" height="17" alt=""></span>
          </div>
        </div>
      </a>
    </article>
  </div>
  <button class="popular-flight-deals__previous" type="button" data-flight-carousel-previous aria-label="Önceki uçuş fırsatlarını göster">
    <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="14" height="15" alt="">
  </button>
  <button class="popular-flight-deals__next" type="button" data-flight-carousel-next aria-label="Sonraki uçuş fırsatlarını göster">
    <img src="assets/fc14e8a13352-arrow-right-blue.svg" width="14" height="15" alt="">
  </button>
  </div>

  <div class="popular-flight-deals__definition" aria-label="En ucuz uçak bileti fiyat özeti">
    <span class="popular-flight-deals__definition-label">Fiyat özeti</span>
    <p id="popular-flight-definition"><span data-definition-sentence="0">En ucuz uçak bileti fiyatı, seçili tarih ve rotada karşılaştırılan hava yolları arasındaki en düşük başlangıç ücretini ifade eder; 9 Eylül 2026 için İstanbul–Antalya hattında SunExpress ile görülen güncel fırsat 1.179 TL’den başlıyor.</span> <span data-definition-sentence="1">Yoğun ilgi gören İstanbul–İzmir uçuşlarında 1.289 TL’den ve İstanbul–Ankara uçuşlarında 1.249 TL’den başlayan seçenekler, kısa şehir kaçamakları ve iş seyahatleri için öne çıkıyor.</span> <span data-definition-sentence="2">Yaz rotalarında ise İstanbul–Bodrum için 1.499 TL’den, İstanbul–Çukurova için 1.379 TL’den başlayan fiyatları karşılaştırarak toplam beş popüler destinasyon arasından planına en uygun bileti seçebilirsin.</span></p>
  </div>

  <script type="application/json" id="popular-flight-deals-data">{"updated":"1 Eylül 2026","updatedTime":"10:23","searchDate":"9 Eylül 2026","cards":[{"origin":"İstanbul","originCode":"IST","destination":"Antalya","destinationCode":"AYT","airline":"SunExpress","flightDate":"9 Eylül 2026, Çarşamba","duration":"1 sa 10 dk","stops":"Direkt","cabin":"Ekonomi","price":"1.179 TL"},{"origin":"İstanbul","originCode":"IST","destination":"İzmir","destinationCode":"ADB","airline":"AJet","flightDate":"12 Eylül 2026, Cumartesi","duration":"1 sa 05 dk","stops":"Direkt","cabin":"Ekonomi","price":"1.289 TL"},{"origin":"İstanbul","originCode":"SAW","destination":"Bodrum","destinationCode":"BJV","airline":"Pegasus","flightDate":"18 Eylül 2026, Cuma","duration":"1 sa 15 dk","stops":"Direkt","cabin":"Ekonomi","price":"1.499 TL"},{"origin":"İstanbul","originCode":"IST","destination":"Ankara","destinationCode":"ESB","airline":"AJet","flightDate":"7 Eylül 2026, Pazartesi","duration":"1 sa 05 dk","stops":"Direkt","cabin":"Ekonomi","price":"1.249 TL"},{"origin":"İstanbul","originCode":"IST","destination":"Çukurova","destinationCode":"COV","airline":"Türk Hava Yolları","flightDate":"21 Eylül 2026, Pazartesi","duration":"1 sa 30 dk","stops":"Direkt","cabin":"Ekonomi","price":"1.379 TL"}],"popularRoutes":[{"name":"İstanbul–Antalya","price":"1.179 TL"},{"name":"İstanbul–İzmir","price":"1.289 TL"},{"name":"İstanbul–Ankara","price":"1.249 TL"},{"name":"İstanbul–Bodrum","price":"1.499 TL"},{"name":"İstanbul–Çukurova","price":"1.379 TL"}]}</script>
  <script>
    (function () {
      var root = document.getElementById('popular-flight-deals');
      var dataNode = document.getElementById('popular-flight-deals-data');
      if (!root || !dataNode) return;
      var data;
      try { data = JSON.parse(dataNode.textContent); } catch (error) { return; }

      var updated = root.querySelector('[data-summary-field="updated"]');
      if (updated) updated.textContent = data.updated;
      var updatedTime = root.querySelector('[data-summary-field="updatedTime"]');
      if (updatedTime) updatedTime.textContent = data.updatedTime;
      root.querySelectorAll('[data-deal-index]').forEach(function (card, index) {
        var deal = data.cards[index];
        if (!deal) return;
        Object.keys(deal).forEach(function (field) {
          var target = card.querySelector('[data-field="' + field + '"]');
          if (target) target.textContent = deal[field];
        });
        var title = card.querySelector('[data-field="title"]');
        if (title) title.textContent = 'En Ucuz ' + deal.origin + ' – ' + deal.destination + ' Uçak Bileti';
      });

      var routes = data.popularRoutes;
      var sentences = [
        'En ucuz uçak bileti fiyatı, seçili tarih ve rotada karşılaştırılan hava yolları arasındaki en düşük başlangıç ücretini ifade eder; ' + data.searchDate + ' için ' + routes[0].name + ' hattında ' + data.cards[0].airline + ' ile görülen güncel fırsat ' + routes[0].price + '’den başlıyor.',
        'Yoğun ilgi gören ' + routes[1].name + ' uçuşlarında ' + routes[1].price + '’den ve ' + routes[2].name + ' uçuşlarında ' + routes[2].price + '’den başlayan seçenekler, kısa şehir kaçamakları ve iş seyahatleri için öne çıkıyor.',
        'Yaz rotalarında ise ' + routes[3].name + ' için ' + routes[3].price + '’den, ' + routes[4].name + ' için ' + routes[4].price + '’den başlayan fiyatları karşılaştırarak toplam beş popüler destinasyon arasından planına en uygun bileti seçebilirsin.'
      ];
      sentences.forEach(function (sentence, index) {
        var target = root.querySelector('[data-definition-sentence="' + index + '"]');
        if (target) target.textContent = sentence;
      });

      var carousel = root.querySelector('[data-flight-carousel]');
      var track = root.querySelector('[data-flight-carousel-track]');
      var previous = root.querySelector('[data-flight-carousel-previous]');
      var next = root.querySelector('[data-flight-carousel-next]');
      if (carousel && track && previous && next) {
        var updateCarouselState = function () {
          var canScroll = track.scrollWidth > track.clientWidth + 2;
          var isAtStart = track.scrollLeft <= 2;
          var isAtEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
          carousel.classList.toggle('is-scrollable', canScroll);
          carousel.classList.toggle('is-at-start', isAtStart);
          carousel.classList.toggle('is-at-end', isAtEnd);
          previous.hidden = !canScroll || isAtStart;
          next.hidden = !canScroll || isAtEnd;
        };
        previous.addEventListener('click', function () {
          var card = track.querySelector('.popular-flight-card');
          var gap = parseFloat(window.getComputedStyle(track).columnGap) || 0;
          track.scrollBy({ left: -(card ? card.getBoundingClientRect().width + gap : track.clientWidth), behavior: 'smooth' });
        });
        next.addEventListener('click', function () {
          var card = track.querySelector('.popular-flight-card');
          var gap = parseFloat(window.getComputedStyle(track).columnGap) || 0;
          track.scrollBy({ left: card ? card.getBoundingClientRect().width + gap : track.clientWidth, behavior: 'smooth' });
        });
        track.addEventListener('scroll', updateCarouselState, { passive: true });
        window.addEventListener('resize', updateCarouselState);
        updateCarouselState();
      }
    }());
  </script>
</section>
""".strip()
    if 'id="popular-flight-deals"' not in html:
        html = html.replace(
            '<div class="mobileAppLanding">',
            f'{popular_flights_markup}\n<div class="mobileAppLanding">',
            1,
        )

    stylesheet = '<link rel="stylesheet" href="header-overrides.css?v=11">'
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
