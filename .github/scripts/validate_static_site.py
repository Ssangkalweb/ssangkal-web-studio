#!/usr/bin/env python3
"""Validate the repository's static website without external dependencies."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_URL = "https://ssangkalweb.github.io/ssangkal-web-studio/"
CONTACT_EMAIL = "vmvm87452154@gmail.com"
EXAMPLE_EMAIL = "hello@ssangkal-studio.example"

REQUIRED_FILES = (
    "index.html",
    "style.css",
    "script.js",
    "README.md",
    "AGENTS.md",
    "favicon.svg",
    "sitemap.xml",
    "404.html",
)
TEXT_FILES = REQUIRED_FILES
SECRET_MARKERS = ("OPENAI_API_KEY", "github_pat_", "ghp_")

BIDI_CONTROL_NAMES = {
    "\u061c": "ARABIC LETTER MARK",
    "\u200e": "LEFT-TO-RIGHT MARK",
    "\u200f": "RIGHT-TO-LEFT MARK",
    "\u202a": "LEFT-TO-RIGHT EMBEDDING",
    "\u202b": "RIGHT-TO-LEFT EMBEDDING",
    "\u202c": "POP DIRECTIONAL FORMATTING",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2067": "RIGHT-TO-LEFT ISOLATE",
    "\u2068": "FIRST STRONG ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
}
ZERO_WIDTH_NAMES = {
    "\u200b": "ZERO WIDTH SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\u2060": "WORD JOINER",
}


class ValidationError(Exception):
    """Raised when one or more validation checks fail."""


class SiteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_langs: list[str] = []
        self.title_count = 0
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()

        if tag == "html":
            self.html_langs.append(values.get("lang", ""))
        elif tag == "title":
            self.title_count += 1
        elif tag == "meta":
            self.meta.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "script":
            self.scripts.append(values)
        elif tag == "a":
            self.anchors.append(values)

        for attribute in ("href", "src"):
            if attribute in values:
                self.references.append((attribute, values[attribute]))


def fail(message: str) -> None:
    raise ValidationError(message)


def pass_message(message: str) -> None:
    print(f"[PASS] {message}")


def read_utf8_files() -> dict[str, str]:
    contents: dict[str, str] = {}
    for relative_path in TEXT_FILES:
        path = ROOT / relative_path
        try:
            contents[relative_path] = path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as error:
            fail(f"{relative_path} 파일을 UTF-8 strict 모드로 읽을 수 없습니다: {error}")
        except OSError as error:
            fail(f"{relative_path} 파일을 읽을 수 없습니다: {error}")
    return contents


def check_hidden_characters(contents: dict[str, str]) -> None:
    forbidden = BIDI_CONTROL_NAMES | ZERO_WIDTH_NAMES
    for relative_path, text in contents.items():
        for position, character in enumerate(text):
            if character in forbidden:
                line = text.count("\n", 0, position) + 1
                fail(
                    f"{relative_path}:{line}에 불필요한 숨은 문자 "
                    f"{forbidden[character]}(U+{ord(character):04X})가 있습니다."
                )
            if character == "\ufeff" and position != 0:
                line = text.count("\n", 0, position) + 1
                fail(f"{relative_path}:{line}의 파일 중간에 BOM(U+FEFF)이 있습니다.")


def matching_meta(
    parser: SiteHTMLParser, attribute: str, expected: str
) -> list[dict[str, str]]:
    return [item for item in parser.meta if item.get(attribute, "").lower() == expected]


def matching_links(parser: SiteHTMLParser, relation: str) -> list[dict[str, str]]:
    return [
        item
        for item in parser.links
        if relation in item.get("rel", "").lower().split()
    ]


def require_count(items: list[object], expected: int, label: str) -> None:
    if len(items) != expected:
        fail(f"index.html의 {label} 항목은 정확히 {expected}개여야 하지만 {len(items)}개입니다.")


def normalized_local_path(reference: str) -> str | None:
    value = reference.strip()
    lowered = value.lower()
    excluded_prefixes = ("http://", "https://", "mailto:", "tel:", "#", "data:")
    if not value or lowered.startswith(excluded_prefixes):
        return None

    parsed = urlsplit(value)
    path = unquote(parsed.path).replace("\\", "/")
    site_prefix = "/ssangkal-web-studio/"
    if path.startswith(site_prefix):
        path = path[len(site_prefix) :]
    return path


def check_local_references(parser: SiteHTMLParser) -> None:
    missing: list[str] = []
    invalid: list[str] = []

    for attribute, reference in parser.references:
        local_path = normalized_local_path(reference)
        if local_path is None:
            continue
        if not local_path:
            invalid.append(f'{attribute}="{reference}"')
            continue

        candidate = (ROOT / local_path).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            invalid.append(f'{attribute}="{reference}"')
            continue
        if not candidate.is_file():
            missing.append(f'{attribute}="{reference}" → {local_path}')

    if invalid:
        fail("저장소 밖을 가리키거나 경로가 비어 있는 로컬 참조가 있습니다: " + ", ".join(invalid))
    if missing:
        fail("존재하지 않는 로컬 파일 참조가 있습니다: " + ", ".join(missing))


def check_secret_markers(contents: dict[str, str]) -> None:
    findings: list[str] = []
    for relative_path, text in contents.items():
        for marker in SECRET_MARKERS:
            if marker.lower() in text.lower():
                findings.append(f"{relative_path}: {marker}")
    if findings:
        fail("공개 파일에서 비밀키 표식을 발견했습니다: " + ", ".join(findings))


def check_index(index_text: str) -> SiteHTMLParser:
    parser = SiteHTMLParser()
    parser.feed(index_text)
    parser.close()

    if parser.html_langs != ["ko"]:
        fail(f'index.html의 html lang은 정확히 "ko"여야 합니다: {parser.html_langs}')
    if parser.title_count != 1:
        fail(f"index.html의 title은 정확히 1개여야 하지만 {parser.title_count}개입니다.")

    require_count(matching_meta(parser, "name", "description"), 1, "meta description")
    canonical = matching_links(parser, "canonical")
    require_count(canonical, 1, "canonical")
    if canonical[0].get("href") != PUBLIC_URL:
        fail(f"index.html의 canonical URL이 공개 홈페이지 주소와 다릅니다: {canonical[0].get('href', '')}")
    if not matching_meta(parser, "name", "robots"):
        fail("index.html에 robots 메타데이터가 없습니다.")

    require_count(matching_meta(parser, "property", "og:title"), 1, "og:title")
    require_count(matching_meta(parser, "property", "og:description"), 1, "og:description")
    og_url = matching_meta(parser, "property", "og:url")
    require_count(og_url, 1, "og:url")
    if og_url[0].get("content") != PUBLIC_URL:
        fail(f"index.html의 og:url이 공개 홈페이지 주소와 다릅니다: {og_url[0].get('content', '')}")
    if not matching_meta(parser, "name", "twitter:card"):
        fail("index.html에 twitter:card 메타데이터가 없습니다.")

    favicon_links = [
        item for item in matching_links(parser, "icon")
        if normalized_local_path(item.get("href", "")) == "favicon.svg"
    ]
    if not favicon_links:
        fail("index.html에 favicon.svg 연결이 없습니다.")
    stylesheet_links = [
        item for item in matching_links(parser, "stylesheet")
        if normalized_local_path(item.get("href", "")) == "style.css"
    ]
    if not stylesheet_links:
        fail("index.html에 style.css 연결이 없습니다.")
    script_links = [
        item for item in parser.scripts
        if normalized_local_path(item.get("src", "")) == "script.js"
    ]
    if not script_links:
        fail("index.html에 script.js 연결이 없습니다.")

    pass_message("HTML 메타데이터 확인")
    return parser


def check_email(index_text: str) -> None:
    if CONTACT_EMAIL not in index_text:
        fail(f"index.html에 실제 문의 이메일 {CONTACT_EMAIL}이 없습니다.")
    if f"mailto:{CONTACT_EMAIL}" not in index_text:
        fail(f"index.html에 mailto:{CONTACT_EMAIL} 링크가 없습니다.")
    if EXAMPLE_EMAIL in index_text:
        fail(f"index.html에 예시 이메일 {EXAMPLE_EMAIL}이 남아 있습니다.")
    pass_message("실제 문의 이메일 확인")


def check_svg(svg_text: str) -> None:
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as error:
        fail(f"favicon.svg XML 문법 오류: {error}")
    if root.tag.rsplit("}", 1)[-1] != "svg":
        fail(f"favicon.svg의 루트 요소가 svg가 아닙니다: {root.tag}")
    pass_message("SVG XML 확인")


def check_sitemap(sitemap_text: str) -> None:
    try:
        root = ET.fromstring(sitemap_text)
    except ET.ParseError as error:
        fail(f"sitemap.xml XML 문법 오류: {error}")

    locations = [
        (element.text or "").strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "loc"
    ]
    if locations.count(PUBLIC_URL) != 1:
        fail(
            "sitemap.xml에 공개 홈페이지 주소가 정확히 한 번 있어야 합니다: "
            f"현재 {locations.count(PUBLIC_URL)}개"
        )
    if any("#" in location for location in locations):
        fail("sitemap.xml에 해시 주소가 포함되어 있습니다.")
    if any(re.search(r"(?:^|/)404\.html(?:$|[?#])", location) for location in locations):
        fail("sitemap.xml에 404.html 주소가 포함되어 있습니다.")
    pass_message("sitemap.xml 확인")


def check_404(page_text: str) -> None:
    parser = SiteHTMLParser()
    parser.feed(page_text)
    parser.close()
    if not any(anchor.get("href") == PUBLIC_URL for anchor in parser.anchors):
        fail("404.html에 홈페이지 복귀 절대 주소가 없습니다.")
    if EXAMPLE_EMAIL in page_text:
        fail(f"404.html에 예시 이메일 {EXAMPLE_EMAIL}이 남아 있습니다.")
    for marker in SECRET_MARKERS:
        if marker.lower() in page_text.lower():
            fail(f"404.html에 비밀키 표식 {marker}가 있습니다.")
    pass_message("404 페이지 확인")


def main() -> int:
    missing = [relative_path for relative_path in REQUIRED_FILES if not (ROOT / relative_path).is_file()]
    if missing:
        fail("필수 파일이 없습니다: " + ", ".join(missing))
    pass_message("필수 파일 확인")

    contents = read_utf8_files()
    pass_message("UTF-8 확인")

    check_hidden_characters(contents)
    pass_message("숨은 문자 확인")

    if not (ROOT / "script.js").is_file():
        fail("JavaScript 파일 script.js가 없습니다.")
    pass_message("JavaScript 파일 존재")

    parser = check_index(contents["index.html"])
    check_email(contents["index.html"])
    check_secret_markers(contents)
    pass_message("비밀키 표식 확인")

    check_local_references(parser)
    pass_message("로컬 파일 참조 확인")

    check_svg(contents["favicon.svg"])
    check_sitemap(contents["sitemap.xml"])
    check_404(contents["404.html"])

    print("[SUCCESS] 모든 정적 사이트 검사를 통과했습니다.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValidationError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        sys.exit(1)
