import json
import os
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()

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


def _smart_fallback(idea: str, row_count: int):
    """
    Parse the user's prompt to build a usable fallback strategy.
    Not as good as the AI strategy, but MUCH better than empty signals.
    """
    idea_lower = idea.lower()

    # Detect fundraising
    is_fundraising = any(w in idea_lower for w in [
        "investor", "invest", "fundrais", "funding", "raise", "capital", "vc", "angel", "seed", "series"
    ])
    # Detect hiring/job search
    is_hiring = any(w in idea_lower for w in [
        "hire", "hiring", "job", "recruit", "employee", "engineer", "developer", "designer", "work on", "work for"
    ])
    # Detect partnerships
    is_partner = any(w in idea_lower for w in [
        "partner", "partnership", "distribution", "integrate", "integration", "resell", "co-sell", "channel", "agency"
    ])
    # Detect sales
    is_sales = any(w in idea_lower for w in [
        "sell", "sales", "pilot", "client", "customer", "buyer", "deal", "revenue"
    ])

    if is_fundraising:
        return {
            "value_flow": "to_me",
            "implicit_ask": f"Seeking investors for: {idea}",
            "persona": "Investors & VCs",
            "summary_analysis": "",
            "anchor_domain": "Technology / AI",
            "keywords": ["investor", "venture", "capital", "fund", "angel", "partner", "portfolio"],
            "boost_words": ["Partner", "Managing Director", "General Partner", "Principal", "Managing Partner", "VP", "Deal Partner"],
            "company_words": ["Capital", "Ventures", "Partners", "Fund", "Holdings", "Investments", "Angels"],
            "negative_words": ["Intern", "Student", "Freelance", "Assistant"],
            "rubric": "Tier1(9-10): Partners/GPs at known VC firms. Tier2(7-8): Founders of funded startups, angels. Tier3(5-6): Tangentially related. Tier4(0-4): Not investors.",
            "priority_signals": ["partner at", "managing director", "venture capital", "angel investor", "general partner", "fund manager"],
        }
    elif is_hiring:
        return {
            "value_flow": "to_me",
            "implicit_ask": f"Looking to hire: {idea}",
            "persona": "Hiring Managers",
            "summary_analysis": "",
            "anchor_domain": "Technology / AI",
            "keywords": ["engineer", "developer", "manager", "director", "head", "lead", "CTO", "VP", "founder"],
            "boost_words": ["VP", "Director", "Head of", "CTO", "CEO", "Founder", "Lead", "Manager", "Principal"],
            "company_words": [],
            "negative_words": ["Intern", "Student", "Freelance", "Assistant", "Partner at fund", "Investor"],
            "rubric": "Tier1(9-10): Right role at strong company. Tier2(7-8): Related role. Tier3(5-6): Tangential. Tier4(0-4): Irrelevant.",
            "priority_signals": ["engineer", "developer", "machine learning", "AI", "software", "data scientist"],
        }
    elif is_partner:
        return {
            "value_flow": "between",
            "implicit_ask": f"Finding distribution/integration/channel partners for: {idea}",
            "persona": "Partnership & Distribution Leaders",
            "summary_analysis": "",
            "anchor_domain": "Technology / SaaS / GTM",
            "keywords": ["partnerships", "business development", "alliances", "integrations", "agency", "operations", "platform", "ecosystem"],
            "boost_words": ["VP", "Director", "Head of", "CEO", "Founder", "Managing Director", "GM"],
            "company_words": ["agency", "solutions", "consulting", "platform", "services"],
            "negative_words": ["Intern", "Student", "Freelance", "Assistant"],
            "rubric": "Tier1(9-10): Leaders at agencies/BPOs/complementary SaaS with distribution leverage. Tier2(7-8): Leaders at tech companies with integration potential. Tier3(5-6): Relevant but individual contributors or small companies. Tier4(0-4): End-users (clients, not partners) or unrelated industries.",
            "priority_signals": ["partnerships", "business development", "alliances", "agency", "outsourced sales", "integration", "platform"],
        }
    elif is_sales:
        return {
            "value_flow": "from_me",
            "implicit_ask": f"Finding buyers/pilots for: {idea}",
            "persona": "Budget Holders",
            "summary_analysis": "",
            "anchor_domain": "Technology",
            "keywords": ["director", "head", "VP", "manager", "operations", "growth", "revenue"],
            "boost_words": ["VP", "Director", "Head of", "Chief", "SVP"],
            "company_words": [],
            "negative_words": ["Intern", "Student", "Freelance", "Assistant"],
            "rubric": "Tier1(9-10): Budget holders at relevant companies. Tier2(7-8): Related decision makers. Tier3(5-6): Tangential. Tier4(0-4): No authority.",
            "priority_signals": ["head of", "VP", "director", "operations", "growth"],
        }
    else:
        return {
            "value_flow": "between",
            "implicit_ask": idea[:200],
            "persona": idea[:80],
            "summary_analysis": "",
            "anchor_domain": "Technology",
            "keywords": ["director", "manager", "head", "VP", "founder", "lead"],
            "boost_words": ["VP", "Director", "Head of", "Founder", "CTO"],
            "company_words": [],
            "negative_words": ["Intern", "Student"],
            "rubric": "Score based on relevance to the user's goal.",
            "priority_signals": [],
        }


def _extract_json(text: str):
    """Robustly extract JSON from model output, handling markdown fences and extra text."""
    # Remove markdown fences
    text = text.replace("```json", "").replace("```", "").strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find JSON object or array in the text
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    return None


async def generate_strategy(idea: str, row_count: int):
    """Generate scoring strategy with retry and smart fallback."""
    prompt = f"""Goal: "{idea}" | Dataset: {row_count} connections.

You are an executive headhunter. Produce scoring signals for the EXACT type of person needed.

CATEGORY RULES (never mix — understand the EXACT relationship the user wants):
- Job/hire → people with HEADCOUNT at operating companies. VCs score 0.
- Fundraising → people who WRITE CHECKS (VCs/angels). Employees score 0.
- Sales/pilot/client → BUDGET HOLDERS who would BUY and USE the product internally.
- Partner → people who would DISTRIBUTE, RESELL, INTEGRATE, or CO-SELL the product to THEIR customers. Partners are NOT buyers — they are force multipliers. Think: agencies/BPOs (MarketStar, Accenture), complementary SaaS tools (Clay, Apollo, HubSpot), channel resellers, and platform ecosystems.
  * A "Partner" at a VC fund is NOT a business partner — that's their job title.
  * An end-user (VP RevOps who would use the tool themselves) is a CLIENT, not a partner.
- FUNDRAISING ONLY: "Power Signal" = Partner/GP/MD at VC/Fund → auto 9-10.
- PARTNER SEARCH: Prioritize people at COMPANIES that have distribution leverage (agencies, platforms, complementary tools, BPOs with hundreds of end-users). Filter OUT individual end-users and companies in unrelated industries (mining, real estate, beverages, etc.).

Return JSON:
- value_flow: "to_me"|"from_me"|"between"
- implicit_ask: 1 sentence, hyper-specific
- summary_analysis: 1 sentence insight (no "We evaluated N", no restating goal)
- persona: short label
- anchor_domain: short
- keywords: 6-10 for THIS ask
- boost_words: titles for THIS ask
- company_words: company types for THIS ask
- negative_words: always ["Intern","Student","Freelance","Assistant"] + irrelevant roles
- rubric: Tier1(9-10), Tier2(7-8), Tier3(5-6), Tier4(0-4) specific to ask
- priority_signals: 3-8 short phrases for fast filter"""

    # Try up to 2 times
    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            raw = response.choices[0].message.content
            data = _extract_json(raw)
            if data and isinstance(data, dict) and data.get("keywords"):
                data["persona"] = data.get("implicit_ask", idea)[:80]
                print(f"Strategy OK (attempt {attempt+1}): persona={data.get('persona')}, keywords={data.get('keywords')}")
                return data
            else:
                print(f"Strategy attempt {attempt+1}: invalid response, retrying. Raw: {raw[:200]}")
        except Exception as e:
            print(f"Strategy attempt {attempt+1} error: {e}")

    # All attempts failed — use smart fallback
    print(f"Strategy: using smart fallback for '{idea[:50]}'")
    fallback = _smart_fallback(idea, row_count)
    return fallback


def _build_lead_profile(row):
    """Extract a clean profile dict from a CSV row."""
    fields = {}
    for key in ["First Name", "Last Name", "Position", "Company", "Industry", "Location"]:
        val = row.get(key, "")
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        val = str(val).strip()
        if val:
            fields[key] = val
    return fields


async def analyze_leads_batch(rows, strategy, user_prompt: str):
    """
    Score a BATCH of leads in a single API call for speed.
    Returns a list of result dicts, one per lead.
    """
    value_flow = strategy.get("value_flow", "between")
    implicit_ask = strategy.get("implicit_ask", user_prompt)
    anchor = strategy.get("anchor_domain", "the specified field")
    rubric = strategy.get("rubric", "")

    # Build numbered lead list
    lead_lines = []
    for i, row in enumerate(rows):
        fields = _build_lead_profile(row)
        name = f"{fields.get('First Name', '')} {fields.get('Last Name', '')}".strip()
        pos = fields.get("Position", "Unknown")
        comp = fields.get("Company", "Unknown")
        extra = ""
        if fields.get("Industry"):
            extra += f" | Industry: {fields['Industry']}"
        lead_lines.append(f"{i+1}. {name}, {pos} at {comp}{extra}")

    leads_block = "\n".join(lead_lines)

    prompt = f"""User's Goal: "{user_prompt}"
Implicit Ask: "{implicit_ask}"
Value Flow: {value_flow} | Anchor Domain: "{anchor}"
Rubric: {rubric}

LEADS TO SCORE:
{leads_block}

SCORING RULES (apply to each lead independently):
1. CATEGORY MATCH — understand the EXACT relationship the user wants:
   - Hiring → people at OPERATING COMPANIES with headcount. VCs/investors = 0-2.
   - Fundraising → investors who WRITE CHECKS. Regular employees = 0-2.
     * Prefer investors with an EXPLICIT thesis (AI, GTM, SaaS, sales automation, infrastructure) over generalist "we invest in tech" — if you can't articulate their specific thesis fit, cap at 7. Do NOT hedge with "potential focus" or "if GTM/AI" — either you know the thesis or you don't.
     * STAGE FIT matters: if the user is raising pre-seed/seed and this investor focuses on growth-stage (Series B+), penalize by -1 to -2 points. A growth-stage investor won't write a seed check no matter how good the thesis fit. Conversely, seed-focused funds that match the thesis = 9-10.
   - Sales/pilot/client → BUDGET HOLDERS who would BUY and USE the product internally.
   - Partner → people who DISTRIBUTE, RESELL, INTEGRATE, or CO-SELL the product to THEIR OWN CUSTOMERS. Partners are force multipliers.
     * 9-10: Agencies/BPOs that run operations for 100s of clients (e.g. MarketStar, Accenture) — rolling out the tool = 100+ customers at once.
     * 9-10: Complementary SaaS tools with shared audience (e.g. Clay, Apollo, lemlist) — integration/co-sell partners.
     * 7-8: Channel resellers, GTM consultants who recommend tools to their clients.
     * 3-4: End-users who would just USE the tool themselves — these are CLIENTS, not partners. Score low for a partner search.
     * 0-2: Companies in unrelated industries (mining, real estate, beverages, hardware manufacturing). No partnership leverage.
   Wrong category = score 0-2, stop.

2. COMPANY VIABILITY — does this company have the right leverage?
   - Hiring: real tech companies, scale-ups, enterprises with headcount. Not VCs or 1-person startups.
   - Fundraising: actual investment firms/funds. Not accelerators.
   - Partner: does this company have DISTRIBUTION LEVERAGE? (many end-users, many clients, platform ecosystem, complementary product). A BPO with 500 SDRs = massive leverage. A 1-person consultancy = low.
   Company doesn't fit = cap at 4.

3. DOMAIN + SENIORITY: In "{anchor}"? Right level?
   Wrong domain = 0-2. Right domain, wrong level = 5-6.

4. FINAL SCORE (0-10, tough grading):
   9-10: Perfect fit — right relationship type + right seniority + strong company with distribution leverage or budget.
   7-8: Strong fit — right type but slightly off on company size or seniority.
   5-6: Decent — right type but small company or tangential role.
   0-4: Wrong relationship type, wrong industry, or no leverage.

5. SYMMETRIC VALUE (2-3 sentences, UNIQUE per lead — this is the most important field):
   Build a SPECIFIC argument. The framing depends on the goal:
   
   --- IF FUNDRAISING (value_flow = "to_me" and goal is raising capital) ---
   VCs do NOT invest to "use your product for their portfolio." They invest because they believe your company can reach $100M+ ARR and return their fund.
   
   CRITICAL: Each lead's briefing MUST open with something UNIQUE TO THAT SPECIFIC FUND OR PERSON. Do NOT repeat the same opening across multiple leads. 
   - Sentence 1: LEAD WITH THE FUND, NOT YOUR PITCH. Open with what makes THIS fund/person specifically relevant — their recent deals, their stated thesis, their fund size/stage, their geographic focus, or their personal background. Every lead MUST have a different opening sentence.
   - Sentence 2: Connect the user's company to THAT specific thesis. Why is this a fund-returning bet FOR THEM? (market size, category creation, timing)
   - Sentence 3 (optional): Why this PERSON specifically — seniority, geographic/cultural bridge, specific domain expertise.
   
   If you don't know enough about the fund to write something specific, say so briefly — do NOT fabricate deal history or thesis details. Never use hedging language like "potential focus" or "if they invest in GTM."
   
   GOOD: "Accel's $650M early-stage fund has a mandate for sales automation — Ben's bets on Deel and Pocus show a sharp eye for GTM innovation. Cursor's AI-native outbound could mirror how Pocus redefined revenue intelligence, positioning it as a category-defining infrastructure play."
   GOOD: "Eleven Ventures dominates CEE early-stage and frequently co-invests with US funds. Getting Valeri's conviction early gives you momentum to close a US lead — and his network across the Bulgarian engineering talent pool adds strategic value beyond capital."
   BAD: "Cursor for GTM is positioning as the next foundational layer of AI-native go-to-market infrastructure..." (Do NOT use this as an opening line — it's your pitch, not their thesis. Lead with THEM, not you.)
   BAD: "Dimiter could deploy Cursor across his portfolio to improve portfolio companies' outbound." (B2B sales logic, not venture logic.)
   
   --- IF CLIENT / SALES / PILOT (value_flow = "from_me") ---
   Sentence 1 — COMPANY SITUATION: What does their company do, what market force is pressuring them?
   Sentence 2 — THE BRIDGE: How does the user's offering address that? Concrete outcome (e.g. "cut SDR costs 40%", "launch outbound in 2 weeks without new hires").
   Sentence 3 — WHY THIS PERSON: Role, budget, pain point ownership.
   
   --- IF PARTNER (distribution / integration) ---
   Explain DISTRIBUTION math: "integrating into MarketStar's SDR operations = 500+ end-users from one deal." Reference company BY NAME. No filler (alignment, synergy, explore).

Return a JSON array. Each element: {{"id": <number>, "score": <float>, "symmetric_value": "<string>", "reasoning": "<max 15 words>"}}
Return ONLY the JSON array."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        raw = response.choices[0].message.content
        parsed = _extract_json(raw)

        # Handle dict wrapper
        if isinstance(parsed, dict):
            for key in ["results", "leads", "data", "scores"]:
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        results = parsed if isinstance(parsed, list) else []

        for r in results:
            r["score"] = float(r.get("score", 0))

        scored = [r for r in results if r["score"] >= 6.0]
        print(f"Batch: {len(rows)} leads → {len(scored)} scored 6+")
        return results
    except Exception as e:
        print(f"Batch analysis error: {e}")
        import traceback
        traceback.print_exc()
        return [{"id": i+1, "score": 0, "reasoning": "Analysis failed", "symmetric_value": ""} for i in range(len(rows))]
