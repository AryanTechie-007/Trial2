import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_engine import analyze_competitor_content

def main():
    dummy_data = {
        "headings": ["Welcome"],
        "cta_buttons": ["Buy"],
        "text_payload": "Bugatti"
    }
    try:
        analyze_competitor_content(dummy_data, "all")
    except Exception as e:
        pass # It's caught inside

if __name__ == "__main__":
    main()
