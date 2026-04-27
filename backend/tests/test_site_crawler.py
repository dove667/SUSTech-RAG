from pathlib import Path

import sustech_rag.crawlers.site_crawler as site_crawler_module
from sustech_rag.config.models import CrawlConfig
from sustech_rag.crawlers.site_crawler import SiteCrawler


def make_crawler(tmp_path: Path) -> SiteCrawler:
    config = CrawlConfig(
        user_agent="test-agent",
        seed_urls=["https://www.sustech.edu.cn/"],
        allowed_domains=["sustech.edu.cn"],
        max_pages=10,
        timeout_seconds=5,
        # 测试中显式打开，避免依赖默认配置。
        include_pdf_links=True,
    )
    return SiteCrawler(config, tmp_path)


def test_extract_main_content_uses_readability_when_available(tmp_path: Path, monkeypatch) -> None:
    crawler = make_crawler(tmp_path)

    class FakeDocument:
        def __init__(self, html: str) -> None:
            self.html = html

        def short_title(self) -> str:
            return "Readable Title"

        def summary(self, html_partial: bool = True) -> str:
            return "<article><p>核心内容</p></article>"

    monkeypatch.setattr(site_crawler_module, "Document", FakeDocument)
    title, text, parser = crawler._extract_main_content(
        "https://www.sustech.edu.cn/example",
        "<html><head><title>Fallback</title></head><body><main>Ignored</main></body></html>",
    )

    assert title == "Readable Title"
    assert text == "核心内容"
    assert parser == "readability_lxml"


def test_extract_main_content_falls_back_when_readability_raises(
    tmp_path: Path, monkeypatch
) -> None:
    crawler = make_crawler(tmp_path)

    class BrokenDocument:
        def __init__(self, html: str) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(site_crawler_module, "Document", BrokenDocument)
    title, text, parser = crawler._extract_main_content(
        "https://www.sustech.edu.cn/example",
        """
        <html>
          <head><title>Fallback Title</title></head>
          <body>
            <nav>Menu</nav>
            <main><h1>通知</h1><p>正文内容</p></main>
            <footer>Footer</footer>
          </body>
        </html>
        """,
    )

    assert title == "Fallback Title"
    assert text == "通知\n正文内容"
    assert parser == "bs4_main"


def test_extract_links_normalizes_and_filters_urls(tmp_path: Path) -> None:
    crawler = make_crawler(tmp_path)
    links = crawler._extract_links(
        "https://www.sustech.edu.cn/news/",
        """
        <html><body>
          <a href="/dept/info/?utm_source=wechat&id=1#section">Dept</a>
          <a href="https://lib.sustech.edu.cn/kgsj_77_622/list.htm?source=home">Library</a>
          <a href="mailto:test@sustech.edu.cn">Mail</a>
          <a href="/image/logo.png">Image</a>
          <a href="/dept/info?id=1">Dup</a>
        </body></html>
        """,
    )

    assert links == [
        "https://www.sustech.edu.cn/dept/info?id=1",
        "https://lib.sustech.edu.cn/kgsj_77_622/list.htm",
    ]
