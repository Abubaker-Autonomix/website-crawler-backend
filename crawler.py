"""
Crawler strategies. No API keys required - everything runs locally.

- 'beautifulsoup': fast, static HTML only (requests + bs4)
- 'playwright': renders JS-heavy pages with a headless browser
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


@dataclass
class CrawledPage:
    url: str
    html: str
    status_code: int
    links: list[str]


class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self, url: str) -> CrawledPage:
        ...


class BeautifulSoupCrawler(BaseCrawler):
    """Static HTML crawler. Fast, no browser, no JS execution."""

    def fetch(self, url: str) -> CrawledPage:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; WebCrawlerBot/1.0)"})
        soup = BeautifulSoup(resp.text, "html.parser")
        links = self._extract_links(soup, url)
        return CrawledPage(url=url, html=resp.text, status_code=resp.status_code, links=links)

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links = []
        base_domain = urlparse(base_url).netloc
        for a in soup.find_all("a", href=True):
            full_url = urljoin(base_url, a["href"])
            if urlparse(full_url).netloc == base_domain:
                links.append(full_url.split("#")[0])
        return list(set(links))


class PlaywrightCrawler(BaseCrawler):
    """Headless-browser crawler for JS-rendered pages. No API key needed."""

    def fetch(self, url: str) -> CrawledPage:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            resp = page.goto(url, timeout=20000, wait_until="networkidle")
            html = page.content()
            links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            status_code = resp.status if resp else 0
            browser.close()

        base_domain = urlparse(url).netloc
        same_domain_links = [l.split("#")[0] for l in links if urlparse(l).netloc == base_domain]
        return CrawledPage(url=url, html=html, status_code=status_code, links=list(set(same_domain_links)))


def extract_clean_text(html: str) -> str:
    """Strip nav/script/style/footer boilerplate, return readable text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


CRAWLERS: dict[str, BaseCrawler] = {
    "beautifulsoup": BeautifulSoupCrawler(),
    "playwright": PlaywrightCrawler(),
}


def get_crawler(engine: str) -> BaseCrawler:
    if engine not in CRAWLERS:
        raise ValueError(f"Unknown crawler engine '{engine}'. Options: {list(CRAWLERS.keys())}")
    return CRAWLERS[engine]


def crawl_site(start_url: str, engine: str, max_depth: int, max_pages: int):
    """Breadth-first crawl. Yields (url, html, status_code) tuples."""
    crawler = get_crawler(engine)
    visited = set()
    queue = [(start_url, 0)]

    while queue and len(visited) < max_pages:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            page = crawler.fetch(url)
        except Exception as e:
            yield (url, None, None, str(e))
            continue

        yield (url, page.html, page.status_code, None)

        if depth < max_depth:
            for link in page.links:
                if link not in visited:
                    queue.append((link, depth + 1))
