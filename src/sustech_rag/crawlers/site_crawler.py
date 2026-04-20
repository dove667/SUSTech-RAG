from __future__ import annotations

import hashlib
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from sustech_rag.config.models import CrawlConfig
from sustech_rag.pipeline.schemas import RawDocument
from sustech_rag.utils.io import ensure_dir

try:
    from readability import Document
except ImportError:  # pragma: no cover - environment-dependent fallback
    Document = None


class SiteCrawler:
    def __init__(self, config: CrawlConfig, data_dir: Path) -> None:
        self.config = config
        self.pages_dir = ensure_dir(data_dir / "raw" / "pages")
        self.pdfs_dir = ensure_dir(data_dir / "raw" / "pdfs")

    def crawl(self) -> list[RawDocument]:
        seen: set[str] = set()
        queue = deque(self.config.seed_urls)
        docs: list[RawDocument] = []

        headers = {"User-Agent": self.config.user_agent}
        with httpx.Client(timeout=self.config.timeout_seconds, headers=headers, follow_redirects=True) as client:
            while queue and len(docs) < self.config.max_pages:
                url = queue.popleft()
                if url in seen or not self._is_allowed(url):
                    continue
                seen.add(url)

                try:
                    response = client.get(url)
                    response.raise_for_status()
                except Exception:
                    continue

                content_type = response.headers.get("content-type", "").lower()
                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    if self.config.include_pdf_links:
                        docs.append(self._save_binary_doc(url, response.content))
                    continue

                html = response.text
                doc = self._save_html_doc(url, html)
                if doc.text:
                    docs.append(doc)
                for next_url in self._extract_links(url, html):
                    if next_url not in seen:
                        queue.append(next_url)

        return docs

    def _save_binary_doc(self, url: str, content: bytes) -> RawDocument:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        path = self.pdfs_dir / f"{digest}.pdf"
        path.write_bytes(content)
        return RawDocument(
            doc_id=digest,
            url=url,
            title=Path(urlparse(url).path).name or digest,
            content_type="application/pdf",
            text="",
            source_path=str(path),
            metadata={"parser": "pdf_pending"},
        )

    def _save_html_doc(self, url: str, html: str) -> RawDocument:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        path = self.pages_dir / f"{digest}.html"
        path.write_text(html, encoding="utf-8")

        title, text, parser = self._extract_main_content(url, html)
        return RawDocument(
            doc_id=digest,
            url=url,
            title=title.strip(),
            content_type="text/html",
            text=text,
            source_path=str(path),
            metadata={"parser": parser},
        )

    def _extract_main_content(self, url: str, html: str) -> tuple[str, str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fallback_title = soup.title.get_text(strip=True) if soup.title else url

        if Document is not None:
            readable = Document(html)
            title = readable.short_title() or fallback_title
            body_html = readable.summary(html_partial=True)
            body_soup = BeautifulSoup(body_html, "html.parser")
            text = body_soup.get_text("\n", strip=True)
            if text:
                return title, text, "readability"

        main_node = soup.find("main") or soup.find("article") or soup.body or soup
        text = main_node.get_text("\n", strip=True)
        return fallback_title, text, "bs4_fallback"

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            absolute = urljoin(base_url, href)
            if self._is_allowed(absolute):
                links.append(absolute.split("#", maxsplit=1)[0])
        return links

    def _is_allowed(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self.config.allowed_domains)
