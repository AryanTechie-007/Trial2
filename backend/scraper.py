import hashlib
import re
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import requests
from bs4 import BeautifulSoup

HIGH_VALUE_PATHS = ["/pricing", "/features", "/docs", "/product", "/about"]


def extract_site_data(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["nav", "footer", "script", "style", "noscript", "iframe", "header"]):
        tag.decompose()

    headings = [h.get_text(strip=True) for h in soup.find_all(re.compile('^h[1-6]$'))]
    headings = [h for h in headings if h]

    cta_buttons = []
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if text and len(text) < 30:
            cta_buttons.append(text)
    for button in soup.find_all("button"):
        text = button.get_text(strip=True)
        if text and len(text) < 30:
            cta_buttons.append(text)

    links = []
    for a in soup.find_all("a", href=True):
        links.append(a['href'])

    text_payload = soup.get_text(separator=" ", strip=True)
    text_payload = re.sub(r'\s+', ' ', text_payload)

    return {
        "headings": headings,
        "cta_buttons": cta_buttons,
        "text_payload": text_payload,
        "links": list(set(links))
    }


def scrape_competitor_site(url: str):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright is not installed in this environment.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            html_content = page.content()
        except Exception as e:
            browser.close()
            raise Exception(f"Failed to load URL {url}: {str(e)}")
        finally:
            browser.close()

    site_data = extract_site_data(html_content)
    return site_data


def scrape_with_requests(url: str, timeout: int = 30):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (compatible; RivalLens/1.0)"})
    resp.raise_for_status()
    return extract_site_data(resp.text)


def scrape_competitor(url: str):
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    collected_headings = []
    collected_cta = []
    collected_text = []
    content_hash_values = []

    def merge_data(data: dict):
        collected_headings.extend(data.get("headings", []))
        collected_cta.extend(data.get("cta_buttons", []))
        collected_text.append(data.get("text_payload", ""))

    # Try Playwright first for JS-heavy websites
    try:
        data = scrape_competitor_site(url)
        merge_data(data)
    except Exception as e:
        # Fallback to requests for simple builds
        print(f"Playwright scrape failed ({e}); falling back to requests.")
        try:
            data = scrape_with_requests(url)
            merge_data(data)
        except Exception as fallback_exc:
            raise Exception(f"Scrape failed for {url}: {fallback_exc}")

    # 2. Extract discovered hrefs from the homepage 
    discovered_links = data.get("links", [])
    valuable_paths = []
    
    # 3. Dynamically filter for structural pages (Pricing, Features, Product)
    for link in discovered_links:
        if re.search(r'(pricing|price|features|product|solution|about)', link, re.IGNORECASE):
            full_url = urljoin(url, link)
            if urlparse(full_url).netloc == parsed.netloc:
                valuable_paths.append(full_url)
    
    # 4. Deduplicate and limit to top 4 deepest structural links to prevent token overloads
    valuable_paths = list(set(valuable_paths))[:4]
    
    # 5. Deep Spidering: Navigate to discovered structural pages
    for spider_url in valuable_paths:
        try:
            # We use requests for speed on structural sub-pages unless it totally fails
            spider_data = scrape_with_requests(spider_url, timeout=15)
            merge_data(spider_data)
        except Exception as e:
            print(f"Spider failed to crawl nested link {spider_url}: {e}")
            continue

    merged_text = "\n".join(collected_text)
    merged_text = re.sub(r'\s+', ' ', merged_text).strip()
    content_hash = hashlib.sha256(merged_text.encode('utf-8')).hexdigest()

    return {
        "headings": list(set(collected_headings)),
        "cta_buttons": list(set(collected_cta)),
        "text_payload": merged_text[:30000],
        "content_hash": content_hash,
    }
