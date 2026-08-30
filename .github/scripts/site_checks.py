#!/usr/bin/env python3
"""Static content and asset checks for catakan.net."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = SCRIPT_DIR / "site-config.json"
PUBLIC_SOURCE_PATHS = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "script.js",
    ROOT / "ataturk/index.html",
    ROOT / "ataturk/ataturk.css",
    ROOT / "ataturk/ataturk.js",
)
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
RESOURCE_EXTENSIONS = {
    ".css", ".gif", ".ico", ".jpeg", ".jpg", ".js", ".pdf", ".png",
    ".svg", ".webp", ".woff", ".woff2",
}
IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf"}


class SiteHTMLParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.ids: list[str] = []
        self.classes: collections.Counter[str] = collections.Counter()
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.future_node_in_research = False
        self.hash_links: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        self.elements.append((tag, attrs))

        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)

        classes = attrs.get("class", "").split()
        self.classes.update(classes)
        if "future-node" in classes:
            self.future_node_in_research = any(
                ancestor_tag == "section" and ancestor_attrs.get("id") == "research"
                for ancestor_tag, ancestor_attrs in self.stack
            )

        href = attrs.get("href", "")
        if href.startswith("#") and len(href) > 1:
            self.hash_links.append(href[1:])

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_html(path: Path) -> SiteHTMLParser:
    parser = SiteHTMLParser(path)
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def report(title: str, errors: list[str], warnings: list[str], facts: list[str]) -> int:
    print(title)
    for fact in facts:
        print(f"PASS  {fact}")
    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"FAIL  {error}", file=sys.stderr)
    if errors:
        print(f"FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"PASSED with {len(warnings)} warning(s)")
    return 0


def check_content(config: dict) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    main_path = ROOT / "index.html"
    ataturk_path = ROOT / "ataturk/index.html"
    main = parse_html(main_path)
    ataturk = parse_html(ataturk_path)
    invariant = config["content_invariants"]

    for parser in (main, ataturk):
        duplicates = sorted(name for name, count in collections.Counter(parser.ids).items() if count > 1)
        if duplicates:
            errors.append(f"{relative(parser.source)} has duplicate IDs: {', '.join(duplicates)}")
        missing_hashes = sorted(set(parser.hash_links) - set(parser.ids))
        if missing_hashes:
            errors.append(f"{relative(parser.source)} has fragment links without targets: {', '.join(missing_hashes)}")

    expected_sections = {
        main_path: {"top", "manifesto", "research", "certifications", "inside-wire", "signals"},
        ataturk_path: {"ataturk-top", "cumhuriyet", "arsiv", "kapanis"},
    }
    for path, required_ids in expected_sections.items():
        parser = main if path == main_path else ataturk
        missing = sorted(required_ids - set(parser.ids))
        if missing:
            errors.append(f"{relative(path)} is missing required section IDs: {', '.join(missing)}")

    cert_count = main.classes["certification-card"]
    expected_certs = invariant["certification_count"]
    if cert_count != expected_certs:
        errors.append(f"expected {expected_certs} certification cards, found {cert_count}")
    else:
        facts.append(f"all {expected_certs} certification cards are present")

    if main.classes["future-node"] != 1:
        errors.append(f"expected one dormant blog future-node, found {main.classes['future-node']}")
    elif not main.future_node_in_research:
        errors.append("the blog future-node is no longer inside the research section")
    else:
        facts.append("the dormant blog node remains inside the research section")

    if any((ROOT / candidate).exists() for candidate in ("blog", "blog.html", "blog/index.html")):
        errors.append("a deployable blog path exists even though the blog must remain dormant")

    main_text = main_path.read_text(encoding="utf-8")
    if 'class="ataturk-corner-link" href="/ataturk/"' not in main_text:
        errors.append("the main-page Atatürk Köşesi destination is missing or has changed")
    if "ataturk-signature" not in main_text or "Atatürk" not in main_text or "Köşesi" not in main_text:
        errors.append("the main-page Atatürk Köşesi label/signature structure is incomplete")

    public_text = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_SOURCE_PATHS)
    folded_public_text = public_text.casefold()
    for forbidden in invariant["forbidden_public_text"]:
        if forbidden.casefold() in folded_public_text:
            errors.append(f"forbidden public text is present: {forbidden}")

    if "193∞" not in ataturk_path.read_text(encoding="utf-8"):
        errors.append("Atatürk Köşesi no longer contains the required 193∞ notation")

    archive_count = ataturk.classes["archive-card"]
    expected_archive = invariant["archive_image_count"]
    if archive_count != expected_archive:
        errors.append(f"expected {expected_archive} archive cards, found {archive_count}")
    else:
        facts.append(f"all {expected_archive} Atatürk archive cards are present")

    ataturk_js = (ROOT / "ataturk/ataturk.js").read_text(encoding="utf-8")
    flag_entries = re.findall(r"\{\s*name:\s*[^,]+,\s*years:\s*[^,]+,\s*image:\s*[\"'][^\"']+[\"']\s*\}", ataturk_js)
    expected_flags = invariant["historical_flag_count"]
    if len(flag_entries) != expected_flags:
        errors.append(f"expected {expected_flags} historical flag entries, found {len(flag_entries)}")
    else:
        facts.append(f"all {expected_flags} historical flag entries are present")

    analytics = config["analytics"]
    for path in (main_path, ataturk_path):
        source = path.read_text(encoding="utf-8")
        script_count = source.count(analytics["script_url"])
        token_count = source.count(analytics["token"])
        if script_count != 1 or token_count != 1:
            errors.append(
                f"{relative(path)} must contain exactly one analytics script and token "
                f"(found script={script_count}, token={token_count})"
            )
    if not any("analytics" in error for error in errors):
        facts.append("both HTML entry points contain exactly one analytics beacon")

    if "new Date().getFullYear()" not in (ROOT / "script.js").read_text(encoding="utf-8"):
        errors.append("the main-page footer year is no longer generated from JavaScript")

    if "mailto:" in main_text.casefold():
        errors.append("the main page exposes a contact link; contact belongs only in security.txt")

    security_path = ROOT / ".well-known/security.txt"
    security_text = security_path.read_text(encoding="utf-8") if security_path.exists() else ""
    required_security_lines = {
        "Contact: mailto:catakan@catakan.net",
        "Preferred-Languages: en, tr",
        "Canonical: https://catakan.net/.well-known/security.txt",
    }
    missing_security = sorted(line for line in required_security_lines if line not in security_text)
    if missing_security:
        errors.append(f"security.txt is missing: {', '.join(missing_security)}")

    expires_match = re.search(r"^Expires:\s*(\S+)\s*$", security_text, re.MULTILINE)
    if not expires_match:
        errors.append("security.txt has no Expires field")
    else:
        try:
            expires = dt.datetime.fromisoformat(expires_match.group(1).replace("Z", "+00:00"))
            now = dt.datetime.now(dt.timezone.utc)
            remaining = expires - now
            if remaining <= dt.timedelta(days=30):
                errors.append(f"security.txt expires too soon ({remaining.days} days remaining)")
            elif remaining > dt.timedelta(days=366):
                errors.append("security.txt expiry exceeds the RFC 9116 one-year maximum")
            else:
                facts.append(f"security.txt expiry is current ({remaining.days} days remaining)")
        except ValueError:
            errors.append(f"security.txt has an invalid Expires timestamp: {expires_match.group(1)}")

    if not errors:
        facts.insert(0, "required IDs, fragment targets, and unique IDs are intact")
    return report("CONTENT INVARIANTS", errors, warnings, facts)


def is_external(value: str) -> bool:
    return urlsplit(value).scheme in {"http", "https"} or value.startswith("//")


def resolve_local(source: Path, value: str) -> Path | None:
    clean = unquote(urlsplit(value).path)
    if not clean or clean in {"/", "."}:
        return None
    candidate = ROOT / clean.lstrip("/") if clean.startswith("/") else source.parent / clean
    try:
        return candidate.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return Path("../OUTSIDE_REPOSITORY")


def check_assets(config: dict) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    references: set[Path] = set()
    analytics_url = config["analytics"]["script_url"]
    html_paths = (ROOT / "index.html", ROOT / "ataturk/index.html")

    def add_reference(source: Path, value: str) -> None:
        if not value or value.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
            return
        if is_external(value):
            return
        suffix = Path(urlsplit(value).path).suffix.lower()
        if suffix not in RESOURCE_EXTENSIONS:
            return
        resolved = resolve_local(source, value)
        if resolved is None:
            return
        if str(resolved).startswith("../"):
            errors.append(f"{relative(source)} references a path outside the repository: {value}")
            return
        references.add(resolved)
        absolute = ROOT / resolved
        if not absolute.is_file():
            errors.append(f"{relative(source)} references missing asset: {value}")

    for path in html_paths:
        parser = parse_html(path)
        for tag, attrs in parser.elements:
            for attribute in ("src", "data-src", "poster"):
                value = attrs.get(attribute, "")
                if is_external(value) and not (tag == "script" and value == analytics_url):
                    errors.append(f"{relative(path)} has unapproved external runtime asset: {value}")
                add_reference(path, value)

            href = attrs.get("href", "")
            rel_tokens = set(attrs.get("rel", "").split())
            is_runtime_link = tag == "link" and bool(rel_tokens & {"stylesheet", "preload", "icon", "manifest"})
            if is_runtime_link and is_external(href):
                errors.append(f"{relative(path)} has unapproved external runtime link: {href}")
            if tag == "link" or Path(urlsplit(href).path).suffix.lower() in RESOURCE_EXTENSIONS:
                add_reference(path, href)

    css_url_pattern = re.compile(r"url\(\s*([\"']?)(.*?)\1\s*\)", re.IGNORECASE)
    for path in (ROOT / "styles.css", ROOT / "ataturk/ataturk.css"):
        source = path.read_text(encoding="utf-8")
        for _, value in css_url_pattern.findall(source):
            if value.startswith(("data:", "#")):
                continue
            if is_external(value):
                errors.append(f"{relative(path)} has an external CSS asset: {value}")
            add_reference(path, value)

    js_asset_pattern = re.compile(r"[\"']([^\"']+\.(?:gif|jpe?g|png|svg|webp|pdf))[\"']", re.IGNORECASE)
    for path in (ROOT / "script.js", ROOT / "ataturk/ataturk.js"):
        source = path.read_text(encoding="utf-8")
        for value in js_asset_pattern.findall(source):
            if "/" in value:
                add_reference(path, value)

    ataturk_js = (ROOT / "ataturk/ataturk.js").read_text(encoding="utf-8")
    history_names = re.findall(r"image:\s*[\"']([^\"']+)[\"']", ataturk_js)
    for name in history_names:
        path = Path("assets/flags/turkic-history") / name
        references.add(path)
        if not (ROOT / path).is_file():
            errors.append(f"historical flag entry references missing asset: {path.as_posix()}")

    asset_files: set[Path] = set()
    for asset_root in config["asset_roots"]:
        root = ROOT / asset_root
        if not root.is_dir():
            errors.append(f"configured asset root does not exist: {asset_root}")
            continue
        asset_files.update(path.relative_to(ROOT) for path in root.rglob("*") if path.is_file())

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_SOURCE_PATHS)
    orphans = sorted(
        path for path in asset_files
        if path not in references and path.name not in combined_source
    )
    if orphans:
        warnings.append("unreferenced assets: " + ", ".join(path.as_posix() for path in orphans))

    image_limit = config["large_image_warning_bytes"]
    document_limit = config["large_document_warning_bytes"]
    for path in sorted(asset_files):
        size = (ROOT / path).stat().st_size
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS and size > image_limit:
            warnings.append(f"large image {path.as_posix()} ({size / 1024:.0f} KiB)")
        elif suffix in DOCUMENT_EXTENSIONS and size > document_limit:
            warnings.append(f"large document {path.as_posix()} ({size / 1024 / 1024:.1f} MiB)")

    facts.append(f"validated {len(references)} local references across HTML, CSS, and JavaScript")
    facts.append(f"inventoried {len(asset_files)} files under configured asset roots")
    if not orphans:
        facts.append("no orphaned assets found")
    if not any("external" in error for error in errors):
        facts.append("no unapproved external runtime assets found")
    return report("ASSET INVENTORY", errors, warnings, facts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("content", "assets"))
    args = parser.parse_args()
    config = load_config()
    return check_content(config) if args.command == "content" else check_assets(config)


if __name__ == "__main__":
    raise SystemExit(main())
