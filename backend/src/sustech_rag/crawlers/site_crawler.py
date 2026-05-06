from __future__ import annotations

import hashlib
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from readability import Document

from sustech_rag.config.models import CrawlConfig
from sustech_rag.pipeline.schemas import RawDocument
from sustech_rag.utils.io import ensure_dir

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"spm", "from", "source", "_t", "_refluxos"}
SKIPPED_SCHEMES = ("mailto:", "javascript:", "tel:")
SKIPPED_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".zip",
    ".rar",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
)


class SiteCrawler:
    def __init__(self, config: CrawlConfig, data_dir: Path) -> None:
        """
        初始化站点抓取器，准备抓取配置与本地保存目录。
        输入参数：config 为抓取配置；data_dir 为数据根目录。
        输出参数：None。
        """
        self.config = config
        self.pages_dir = ensure_dir(data_dir / "raw" / "pages")
        # PDF 目录仍然保留，便于后续单独开启和验证 PDF 抓取流程。
        self.pdfs_dir = ensure_dir(data_dir / "raw" / "pdfs")

    def crawl(self) -> list[RawDocument]:
        """
        按种子链接执行广度优先抓取，并返回已保存的原始文档列表。
        输入参数：无。
        输出参数：list[RawDocument]，抓取并解析后的原始文档列表。
        """
        seen: set[str] = set()
        queue = deque(self._normalize_url(url) for url in self.config.seed_urls)
        docs: list[RawDocument] = []

        headers = {"User-Agent": self.config.user_agent}
        with httpx.Client(
            timeout=self.config.timeout_seconds,
            headers=headers,
            follow_redirects=True,
        ) as client:
            while queue and len(docs) < self.config.max_pages:
                url = queue.popleft()
                if url in seen or not self._is_allowed(url):
                    continue
                seen.add(url)

                try:
                    response = client.get(url)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    print(
                        f"[sustech-rag] HTTP {exc.response.status_code} for {url}, skipping.",
                        flush=True,
                    )
                    continue
                except httpx.RequestError as exc:
                    print(
                        f"[sustech-rag] request failed for {url}: {exc}, skipping.",
                        flush=True,
                    )
                    continue

                final_url = self._normalize_url(str(response.url))
                seen.add(final_url)

                content_type = response.headers.get("content-type", "").lower()
                if "pdf" in content_type or final_url.lower().endswith(".pdf"):
                    if self.config.include_pdf_links:
                        docs.append(self._save_binary_doc(final_url, response.content))
                    continue

                html = response.text
                doc = self._save_html_doc(final_url, html)
                if doc.text:
                    docs.append(doc)
                for next_url in self._extract_links(final_url, html):
                    if next_url not in seen:
                        queue.append(next_url)

        return docs

    def _save_binary_doc(self, url: str, content: bytes) -> RawDocument:
        """
        将二进制内容保存到本地，并构造对应的原始文档对象。
        输入参数：url 为资源地址；content 为二进制内容。
        输出参数：RawDocument，二进制文档记录。
        """
        # 当前默认配置不会走到这里；PDF 保存逻辑保留为后续可选开发项。
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
        """
        将 HTML 页面保存到本地，并提取正文构造原始文档对象。
        输入参数：url 为页面地址；html 为页面源码。
        输出参数：RawDocument，HTML 文档记录。
        """
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
        """
        从 HTML 中提取标题、正文与解析器标记。
        输入参数：url 为页面地址；html 为页面源码。
        输出参数：tuple[str, str, str]，分别为标题、正文文本和解析器名称。
        """
        soup = BeautifulSoup(html, "html.parser")
        fallback_title = soup.title.get_text(strip=True) if soup.title else url

        try:
            readable = Document(html)
            title = readable.short_title() or fallback_title
            body_html = readable.summary(html_partial=True)
            body_soup = BeautifulSoup(body_html, "html.parser")
            text = body_soup.get_text("\n", strip=True)
            if text:
                return title, text, "readability_lxml"
        except Exception:
            print(
                f"[sustech-rag] readability-lxml failed for {url}, falling back to bs4",
                flush=True,
            )

        main_node = self._select_fallback_main_node(soup)
        text = main_node.get_text("\n", strip=True)
        return fallback_title, text, "bs4_main"

    def _extract_links(self, base_url: str, html: str) -> list[str]:
        """
        从页面源码中解析并过滤可继续抓取的链接。
        输入参数：base_url 为当前页面地址；html 为页面源码。
        输出参数：list[str]，去重后的可抓取链接列表。
        """
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith(SKIPPED_SCHEMES):
                continue
            absolute = self._normalize_url(urljoin(base_url, href))
            if absolute.lower().endswith(SKIPPED_SUFFIXES):
                continue
            if self._is_allowed(absolute):
                links.append(absolute.split("#", maxsplit=1)[0])
        return list(dict.fromkeys(links))

    def _is_allowed(self, url: str) -> bool:
        """
        判断目标链接是否属于允许抓取的域名范围。
        输入参数：url 为待检查的链接。
        输出参数：bool，允许抓取返回 True，否则返回 False。
        """
        host = urlparse(url).netloc.lower()
        return any(
            host == domain or host.endswith(f".{domain}")
            for domain in self.config.allowed_domains
        )

    def _normalize_url(self, url: str) -> str:
        """
        规范化 URL，统一协议、主机、路径与查询参数格式。
        输入参数：url 为待规范化的链接。
        输出参数：str，规范化后的 URL。
        """
        parsed = urlparse(url.strip())
        scheme = (parsed.scheme or "https").lower()
        host = parsed.netloc.lower()
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")

        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in TRACKING_QUERY_KEYS and not key.startswith(TRACKING_QUERY_PREFIXES)
        ]
        query = urlencode(filtered_query, doseq=True)
        return urlunparse((scheme, host, path, "", query, ""))

    def _select_fallback_main_node(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        在无法使用主解析器时，选择用于正文抽取的回退节点。
        输入参数：soup 为页面解析后的 BeautifulSoup 对象。
        输出参数：BeautifulSoup，优先返回 main/article/body，否则返回清洗后的根节点。
        """
        pruned = BeautifulSoup(str(soup), "html.parser")
        for node in pruned.select(
            "script, style, noscript, header, footer, nav, aside, form, iframe, svg"
        ):
            node.decompose()
        main = pruned.find("main") or pruned.find("article") or pruned.body
        if main is None:
            print(
                "[sustech-rag] no valid main content node found (no main/article/body), "
                "returning empty pruned document.",
                flush=True,
            )
            return pruned
        return main
