import pandas as pd
from openai import AsyncOpenAI # <--- CHANGED
import json
import io
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Async Client
client = AsyncOpenAI(
    base_url="https://api.gmi-serving.com/v1",
    api_key=os.getenv("GMI_API_KEY"),
)
MODEL_ID = "deepseek-ai/DeepSeek-V3-0324"

def process_csv(file_contents):
    """Parses CSV bytes, automatically finding the header row."""
    try:
        content_str = file_contents.decode('utf-8')
    except UnicodeDecodeError:
        content_str = file_contents.decode('latin-1')
        
    lines = content_str.split('\n')
    header_idx = 0
    for i, line in enumerate(lines[:20]):
        if "First Name" in line and "Company" in line:
            header_idx = i
            break
            
    df = pd.read_csv(io.StringIO(content_str), skiprows=header_idx)
    df.columns = [c.strip() for c in df.columns]
    return df

async def generate_strategy(idea: str): # <--- Added async
    """Step 0: Define who to target."""
    try:
        prompt = f"""
        Business Idea: "{idea}"
        Task: Define TARGET PERSONA and 8 JOB TITLE KEYWORDS to filter a LinkedIn list.
        Return JSON with keys: "persona" (string), "keywords" (list of strings).
        Do not use markdown.
        """
        # <--- Added await
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Strategy Error: {e}")
        return {"persona": "Potential Leads", "keywords": ["Founder", "CEO", "Director", "VP"]}

async def analyze_lead(row, persona): # <--- Added async
    """Step 2: Deep Analysis (Reasoning Only)."""
    try:
        profile = f"{row.get('First Name', '')} {row.get('Last Name', '')}, {row.get('Position', 'Unknown')} at {row.get('Company', 'Unknown')}"
        
        prompt = f"""
        Persona: "{persona}"
        Profile: {profile}
        Task: Score relevance (1-10) and provide strict reasoning why they fit.
        Return JSON keys: "score", "reasoning".
        Do not use markdown.
        """
        
        # <--- Added await
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {"score": 0, "reasoning": "Analysis Failed"}