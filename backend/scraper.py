import hashlib
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def scrape_competitor_site(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Navigate to the URL and wait for the network to be idle
            page.goto(url, wait_until="networkidle", timeout=30000)
            html_content = page.content()
        except Exception as e:
            browser.close()
            raise Exception(f"Failed to load URL {url}: {str(e)}")
        
        browser.close()

        # Clean the DOM
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove unwanted tags
        for tag in soup(["nav", "footer", "script", "style", "noscript", "iframe", "header"]):
            tag.decompose()
        
        # Extract headings
        headings = [h.get_text(strip=True) for h in soup.find_all(re.compile('^h[1-6]$'))]
        headings = [h for h in headings if h]
        
        # Extract CTA buttons (common selectors)
        cta_buttons = []
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            if len(text) > 0 and len(text) < 30: # reasonable length for a button
                cta_buttons.append(text)
        
        for button in soup.find_all("button"):
            text = button.get_text(strip=True)
            if len(text) > 0 and len(text) < 30:
                cta_buttons.append(text)
                
        # Pure text payload
        text_payload = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text_payload = re.sub(r'\s+', ' ', text_payload)
        
        # Generate hash of content
        content_hash = hashlib.sha256(text_payload.encode('utf-8')).hexdigest()
        
        return {
            "headings": list(set(headings)), # dedup
            "cta_buttons": list(set(cta_buttons)),
            "text_payload": text_payload[:15000], # Trucate text payload to keep LLM context reasonable
            "content_hash": content_hash
        }
