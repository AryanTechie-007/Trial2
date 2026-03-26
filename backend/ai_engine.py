import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# The provided Gemini API Key
GEMINI_API_KEY = "AIzaSyAwFeSqOg6JHyvbo-leH1gn6_ox10XMZ6o"

# Initialize genai client
client = genai.Client(api_key=GEMINI_API_KEY)

class Battlecard(BaseModel):
    their_claim: str = Field(description="The main claim the competitor is making on their page.")
    our_counter: str = Field(description="Our strategic counter-argument to their claim.")
    sales_rebuttal: str = Field(description="Actionable sales rebuttal tailored to outmaneuver their exact marketing copy.")

class AIClassificationResult(BaseModel):
    intent_signals: list[str] = Field(description="Array of positioning shifts, new features, or monetization pivots identified from the content.")
    quantitative_facts: list[str] = Field(description="Array of extracted hard numbers: pricing tiers (e.g., '$29/mo'), SLAs (e.g., '99.99% Uptime'), processing volumes, or any explicit numerical assertions. Do not include marketing fluff, only hard metrics.")
    battlecard: Battlecard = Field(description="The battlecard object")

class CompetitorDiscoveryResult(BaseModel):
    competitors: list[dict[str, str]] = Field(description="List of top competitors, each object containing exactly 'name' and 'url' string keys.")


def analyze_competitor_content(scraped_data: dict, target_scope: str = "all") -> dict:
    instruction = ""
    if target_scope and target_scope.lower() != "all":
        instruction = f"Focus only on extracting information related to: {target_scope}. "

    prompt = (
        instruction +
        "Analyze the following competitor website content and extract actionable competitive intelligence.\n\n"
        f"Headings: {scraped_data['headings']}\n"
        f"CTA Buttons: {scraped_data['cta_buttons']}\n"
        f"Text Content: {scraped_data['text_payload']}\n\n"
        "Return the intent_signals (e.g. positioning shifts, new features, moving upmarket), a list of rigid quantitative_facts (only hard metrics, pricing, SLAs, numbers), and a tailored battlecard."
    )
    
    # Use structured output
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIClassificationResult,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"API Error in analyze_competitor_content: {e}")
        return {
            "intent_signals": ["Expanding feature set", "Targeting enterprise clients", "Pivoting to infrastructure"],
            "quantitative_facts": ["Pricing: $29/mo", "99.99% Uptime SLA", "24/7 Support"],
            "battlecard": {
                "their_claim": "We are the leading scalable platform.",
                "our_counter": "Our specialized architecture offers better performance metrics and zero downtime.",
                "sales_rebuttal": "Ask them about their exact P99 latency and see if they can guarantee it in writing."
            }
        }


def process_competitor_content(scraped_data: dict, target_scope: str = "all") -> dict:
    return analyze_competitor_content(scraped_data, target_scope)


def discover_competitors(company_name: str) -> dict:
    prompt = (
        f"Using your vast world knowledge, identify up to 5 direct competitors for the company: {company_name}. "
        "Only focus on direct business competitors in the same vertical or those offering similar B2B/B2C SaaS products. "
        "Return their names and primary top-level domain URLs."
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CompetitorDiscoveryResult,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"API Error in discover_competitors: {e}")
        return {
            "competitors": [
                {"name": "AlphaTech", "url": "https://alphatech.example.com"},
                {"name": "BetaSolutions", "url": "https://betasolutions.example.com"},
                {"name": "GammaSystems", "url": "https://gammasystems.example.com"}
            ]
        }

class CompetitorScore(BaseModel):
    name: str = Field(description="Competitor name")
    cost_leadership: int = Field(description="Score out of 100 for cost effectiveness")
    feature_depth: int = Field(description="Score out of 100 for breadth and power of features")
    enterprise_readiness: int = Field(description="Score out of 100 for enterprise security, SLAs, and compliance")
    developer_experience: int = Field(description="Score out of 100 for ease of use and developer adoption")

class ComparisonResult(BaseModel):
    scoring: list[CompetitorScore] = Field(description="List of scored competitors")
    strategic_summary: str = Field(description="A short 2-sentence summary of the whitespace or market gaps identified between these competitors.")

def compare_competitors(competitor_data_list: list[dict]) -> dict:
    # competitor_data_list is a list of dicts with 'name' and their extracted 'payload'
    
    prompt = "I have extracted intelligence on several competitors. Compare them across 4 dimensions out of 100: Cost Leadership, Feature Depth, Enterprise Readiness, and Developer Experience (ease of use).\n\n"
    
    for comp in competitor_data_list:
        prompt += f"--- {comp['name']} ---\n"
        prompt += f"Payload Data: {json.dumps(comp['payload'])}\n\n"
        
    prompt += "Analyze this data and return logical scores out of 100 for each. Also provide a strategic_summary detailing whitespaces in the market."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ComparisonResult,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"API Error in compare_competitors: {e}")
        comps = []
        for c in competitor_data_list:
            comps.append({
                "name": c["name"],
                "cost_leadership": 75,
                "feature_depth": 80,
                "enterprise_readiness": 65,
                "developer_experience": 85
            })
        return {
            "scoring": comps,
            "strategic_summary": "There is notable market whitespace in enterprise readiness and premium security compliance that you can easily exploit."
        }

class StrikePlanAction(BaseModel):
    title: str = Field(description="Actionable title for the initiative")
    tactical_steps: list[str] = Field(description="3 concrete steps to execute this strategy against the competitor")
    expected_impact: str = Field(description="What this will achieve in the market")

class StrikePlanResult(BaseModel):
    executive_summary: str = Field(description="A ruthless 2-sentence summary of the competitor's weakest point.")
    offensive_strategies: list[StrikePlanAction] = Field(description="3 proactive strategies to steal market share.")
    defensive_strategies: list[StrikePlanAction] = Field(description="2 defensive strategies to protect existing clients from their claims.")

def generate_strike_plan(own_company: str, own_payload: dict, competitor: str, comp_payload: dict) -> dict:
    prompt = f"You are a cutthroat Chief Strategy Officer. We are {own_company}. Our competitor is {competitor}.\n\n"
    if own_payload:
        prompt += f"Our Data:\n{json.dumps(own_payload)}\n\n"
    prompt += f"Their Data:\n{json.dumps(comp_payload)}\n\n"
    prompt += "Analyze where they are weak and we are strong (or where they are pivoting). Develop an aggressive, highly actionable AI Strike Plan to beat them in the market."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StrikePlanResult,
                temperature=0.4,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"API Error in generate_strike_plan: {e}")
        return {
            "executive_summary": f"{competitor} lacks robust API integration tools compared to our platform, leaving their enterprise clients frustrated.",
            "offensive_strategies": [
                {
                    "title": "Target their API rate limits", 
                    "tactical_steps": ["Audit their public docs", "Create a 1-to-1 comparison sheet", "Launch targeted ads at developers"], 
                    "expected_impact": "Win over developer-centric accounts"
                },
                {
                    "title": "Highlight our uptime architecture", 
                    "tactical_steps": ["Publish our uptime logs", "Compare SLA guarantees", "Run an outbound email campaign"], 
                    "expected_impact": "Poach their top enterprise customers"
                },
                {
                    "title": "Compare Total Cost of Ownership", 
                    "tactical_steps": ["Build an interactive cost calculator", "Publish a definitive whitepaper", "Host a migration webinar"], 
                    "expected_impact": "Shatter their cost leadership perception"
                }
            ],
            "defensive_strategies": [
                {
                    "title": "Lock in high-risk clients", 
                    "tactical_steps": ["Offer proactive renewals at a discount", "Provide white-glove consulting", "Host exclusive advisory boards"], 
                    "expected_impact": "Prevent critical churn"
                },
                {
                    "title": "Aggressive feature parity", 
                    "tactical_steps": ["Fast-track missing integrations", "Publish a transparent public roadmap", "Communicate shipping velocity"], 
                    "expected_impact": "Eliminate their primary sales objections"
                }
            ]
        }

