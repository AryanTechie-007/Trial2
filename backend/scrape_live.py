import os
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, User, Scrape
from scraper import scrape_competitor

from ai_engine import process_competitor_content

def get_dynamic_url_payload(competitor_name, data):
    # Pass the actual extracted data to Gemini instead of rule-based hallucinations
    parsed_analysis = process_competitor_content(data, "all")
    return parsed_analysis

def main():
    db = SessionLocal()
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.bugatti.com/"
    name = sys.argv[2] if len(sys.argv) > 2 else "bugatti"
    
    print(f"Scraping {url}...")
    try:
        data = scrape_competitor(url)
    except Exception as e:
        print(f"Failed to scrape: {e}")
        return
        
    payload = get_dynamic_url_payload(name, data)
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
    print("Done rescraping live URL!")

if __name__ == "__main__":
    main()
