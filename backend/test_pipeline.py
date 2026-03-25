import asyncio
import json
import logging
import sys
from database import SessionLocal, Scrape
from scraper import scrape_competitor_site
from ai_engine import analyze_competitor_content

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def test():
    url = "https://example.com"
    name = "Example"
    
    logging.info(f"Targeting: {url}")
    try:
        scraped = await scrape_competitor_site(url)
    except Exception as e:
        logging.error(f"Playwright scrape failed: {e}")
        return
        
    logging.info(f"Scraped {len(scraped['headings'])} headings and {len(scraped['cta_buttons'])} CTAs")
    logging.info("Sending to Gemini for analysis...")
    
    try:
        ai_res = analyze_competitor_content(scraped)
        logging.info("Gemini Analysis Successful:")
        print(json.dumps(ai_res, indent=2))
    except Exception as e:
         logging.error(f"Gemini API failed: {e}")
         return
    
    db = SessionLocal()
    try:
        new_scrape = Scrape(
            competitor_name=name.lower(),
            content_hash=scraped["content_hash"],
            payload=ai_res
        )
        db.add(new_scrape)
        db.commit()
        logging.info("Saved to database.")
    except Exception as e:
        logging.error(f"DB save failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
