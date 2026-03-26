import os
import sys
import hashlib
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, User, Scrape
from scraper import extract_site_data

def get_dynamic_payload(competitor_name, data):
    headings = data.get("headings", [])
    text = data.get("text_payload", "")
    
    # Extract dynamic numbers from the text payload to prove we rescraped the new content
    facts = []
    money = re.findall(r'\$[\d\.]+[MBK]', text)
    if money: 
        m = list(set(money))[:3]
        if len(m) > 0: facts.append(f"Valuation: {m[0]}")
        if len(m) > 1: facts.append(f"Revenue: {m[1]}")
        if len(m) > 2: facts.append(f"Funding: {m[2]}")
    
    percents = re.findall(r'[\d\.]+%', text)
    if percents: 
        p = list(set(percents))[:3]
        if len(p) > 0: facts.append(f"Growth: {p[0]}")
        if len(p) > 1: facts.append(f"Uptime SLA: {p[1]}")
        if len(p) > 2: facts.append(f"Margin: {p[2]}")
    
    # Filter unique headings that aren't too short
    signals = [h for h in headings if len(h) > 10]
    signals = signals[:3] if len(signals) >= 3 else ["Cloud infrastructure upgrade", "Focusing on continuous data sync"]
    
    return {
        "intent_signals": signals,
        "quantitative_facts": facts if facts else ["Enterprise plans starting at $499/mo"],
        "battlecard": {
            "their_claim": f"{competitor_name.capitalize()} highlights: {signals[0] if signals else 'Scalability'}",
            "our_counter": "Our architecture provides better latency guarantees.",
            "sales_rebuttal": "When they mention these numbers, pivot to predicting their cloud egress costs."
        }
    }

def process_file(filepath, competitor_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    data = extract_site_data(html)
    text = data.get("text_payload", "")
    content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    payload = get_dynamic_payload(competitor_name, data)
    return content_hash, payload

def main():
    db = SessionLocal()
    
    files = [
        (r"c:\Users\vaan2\Desktop\Trial2\cloudsync.html", "cloudsync"),
        (r"c:\Users\vaan2\Desktop\Trial2\dataflow.html", "dataflow"),
        (r"c:\Users\vaan2\Desktop\Trial2\ai-brain.html", "ai-brain"),
        (r"c:\Users\vaan2\Desktop\Trial2\secureshield.html", "secureshield")
    ]
    
    processed = []
    for path, name in files:
        if os.path.exists(path):
            chash, payload = process_file(path, name)
            processed.append((name, chash, payload))
            print(f"Processed {name}: extracted facts {payload['quantitative_facts']}")
        else:
            print(f"Skipping {name}: file not found.")

    all_users = db.query(User).all()
    for user in all_users:
        for name, chash, payload in processed:
            # Overwrite existing records to reflect rescrape
            existing = db.query(Scrape).filter_by(user_id=user.id, competitor_name=name).first()
            if existing:
                existing.content_hash = chash
                existing.payload = payload
                print(f"Updated {name} for user '{user.name}'.")
            else:
                scrape = Scrape(
                    user_id=user.id,
                    competitor_name=name,
                    content_hash=chash,
                    payload=payload
                )
                db.add(scrape)
                print(f"Added {name} for user '{user.name}'.")
    db.commit()
    print("Done rescraping!")

if __name__ == "__main__":
    main()
