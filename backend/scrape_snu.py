import os
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, User, Scrape
from scraper import scrape_competitor

def get_snu_payload(competitor_name, data):
    headings = data.get("headings", [])
    text = data.get("text_payload", "")
    
    # Factually extract only what is physically on the page. No hardcoded hypercar or cloud metrics.
    facts = []
    
    years = list(set(re.findall(r'\b(19\d{2}|20\d{2})\b', text)))
    if len(years) > 0: facts.append(f"Year Referenced: {years[0]}")
    
    numbers = list(set(re.findall(r'\b\d{2,4}\b', text)))
    # Exclude years from numbers
    numbers = [n for n in numbers if n not in years]
    if len(numbers) > 0: facts.append(f"Extracted Value: {numbers[0]}")
    if len(numbers) > 1: facts.append(f"Secondary Value: {numbers[1]}")
    
    if not facts:
        facts.append(f"Word Count: {len(text.split())}")
        facts.append(f"Headers Scanned: {len(headings)}")
        
    signals = [h.strip() for h in headings if len(h.strip()) > 10 and len(h.strip()) < 80]
    
    # Fallback to textual sentences if no valid headings
    if not signals:
        sentences = text.split('.')
        signals = [s.strip() for s in sentences if len(s.strip()) > 15][:3]
        
    # Ensure exactly 3 signals safely
    while len(signals) < 3:
        signals.append("Additional content scanning required")
        
    return {
        "intent_signals": signals[:3],
        "quantitative_facts": facts[:4],
        "battlecard": {
            "their_claim": f"Direct header from site: '{signals[0]}'",
            "our_counter": "We provide a specialized alternative infrastructure.",
            "sales_rebuttal": "Emphasize customized metric benchmarks instead of raw page figures."
        }
    }

def main():
    db = SessionLocal()
    url = "https://www.snuchennai.edu.in/faculty/"
    name = "snu-chennai"
    
    print(f"Scraping exact data from {url}...")
    try:
        data = scrape_competitor(url)
    except Exception as e:
        print(f"Failed to scrape: {e}")
        return
        
    payload = get_snu_payload(name, data)
    chash = data.get("content_hash", "testhash")
    
    all_users = db.query(User).all()
    for user in all_users:
        existing = db.query(Scrape).filter_by(user_id=user.id, competitor_name=name.lower()).first()
        if existing:
            existing.payload = payload
            existing.content_hash = chash
            print(f"Updated {name} for user '{user.name}'.")
        else:
            scrape = Scrape(user_id=user.id, competitor_name=name.lower(), content_hash=chash, payload=payload)
            db.add(scrape)
            print(f"Added {name} for user '{user.name}'.")
    
    db.commit()
    print("Done rescraping safely!")

if __name__ == "__main__":
    main()
