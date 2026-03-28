import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load env
from dotenv import load_dotenv
load_dotenv()

# The provided Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize genai client
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


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
        raise ValueError(f"Gemini API Error: {str(e)}")


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
        raise ValueError(f"Gemini API Error: {str(e)}")

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
        raise ValueError(f"Gemini API Error: {str(e)}")

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
class CompanyVerificationResult(BaseModel):
    is_match: bool = Field(description="True if the actual website content strongly aligns with the user's provided description, False if it is a lie or a complete mismatch.")
    reason: str = Field(description="A short 1-sentence explanation of why it matched or mismatched.")

def verify_company_description(scraped_data: dict, user_description: str) -> dict:
    prompt = (
        f"A user is pretending or claiming that their company does the following:\n"
        f"'{user_description}'\n\n"
        f"We have crawled their actual website. Here is their actual website content:\n"
        f"Headings: {scraped_data.get('headings', [])}\n"
        f"Content: {scraped_data.get('text_payload', '')[:20000]}\n\n"
        "Evaluate if their description is truthful and matches the actual nature of their business. "
        "Return is_match=true if it generally matches, and false if they are lying (e.g., claiming to be a cloud company when they sell cars)."
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CompanyVerificationResult,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"API Error in verify_company_description: {e}")
        raise ValueError(f"Gemini API Error: {str(e)}")
