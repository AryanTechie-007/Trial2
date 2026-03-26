import os
import sys
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, User, Scrape
from scraper import extract_site_data
from ai_engine import process_competitor_content

def process_and_add(filepath, competitor_name, user_id, db):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    data = extract_site_data(html)
    text = data.get("text_payload", "")
    content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    print(f"Processing {competitor_name}...")
    try:
        payload = process_competitor_content(data)
    except Exception as e:
        print(f"AI engine failed ({e}). Using mock payload.")
        payload = {
            "intent_signals": ["Cloud infrastructure upgrade", "Focusing on continuous data sync"],
            "quantitative_facts": ["Enterprise plans starting at $499/mo", "Unlimited data movement"],
            "battlecard": {
                "their_claim": f"{competitor_name.capitalize()} claims to be the most scalable solution.",
                "our_counter": "Our architecture provides better latency guarantees.",
                "sales_rebuttal": "When they mention scalability, pivot to predicting their cloud egress costs."
            }
        }
    
    scrape = Scrape(
        user_id=user_id,
        competitor_name=competitor_name.lower(),
        content_hash=content_hash,
        payload=payload
    )
    db.add(scrape)
    db.commit()
    print(f"Added {competitor_name} successfully for user {user_id}.")

def main():
    db = SessionLocal()
    # Find user Aryan
    user = db.query(User).filter(User.name.ilike('%Aryan%')).first()
    if not user:
        print("User Aryan not found. Creating him...")
        user = User(
            email="aryan@example.com",
            name="Aryan",
            hashed_password="dummy",
            company_name="AryanTechie",
            plan_tier="enterprise"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        print(f"Found user {user.name} with ID {user.id}")
    
    files = [
        (r"c:\Users\vaan2\Desktop\Trial2\cloudsync.html", "cloudsync"),
        (r"c:\Users\vaan2\Desktop\Trial2\dataflow.html", "dataflow")
    ]
    
    for path, name in files:
        if os.path.exists(path):
            process_and_add(path, name, user.id, db)
        else:
            print(f"File not found: {path}")

if __name__ == "__main__":
    main()
