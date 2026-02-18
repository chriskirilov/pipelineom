import csv
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


# Canonical column names the rest of the pipeline expects
_CANONICAL = ["First Name", "Last Name", "Company", "Position", "URL", "Email", "Industry", "Location", "Connected On"]

# Variants per canonical (lowercase for case-insensitive match). Order: more specific first.
_COLUMN_VARIANTS = {
    "First Name": ["first name", "firstname", "first_name", "given name", "contact first name", "fname", "first"],
    "Last Name": ["last name", "lastname", "last_name", "family name", "surname", "contact last name", "lname", "last"],
    "Company": ["company", "company name", "companyname", "organization", "org", "account name", "accountname", "employer", "business", "account"],
    "Position": ["position", "job title", "jobtitle", "title", "role", "job role", "job_position", "occupation"],
    "URL": ["url", "linkedin url", "profile url", "website", "linkedin", "profile"],
    "Email": ["email", "email address", "e-mail", "work email"],
    "Industry": ["industry", "sector"],
    "Location": ["location", "city", "region", "country"],
    "Connected On": ["connected on", "connectedon", "date connected", "connection date"],
}

# Header row: must contain at least this many recognizable column names to be treated as header
_HEADER_MIN_MATCHES = 2


def _normalize_header_cell(cell):
    return cell.strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def _header_match_count(line):
    """Count how many cells in the line match our known column variants."""
    try:
        row = next(csv.reader(io.StringIO(line), skipinitialspace=True), [])
    except Exception:
        return 0
    seen = set()
    for cell in row:
        n = cell.strip().lower()
        if not n:
            continue
        n_flat = _normalize_header_cell(cell)
        for canonical, variants in _COLUMN_VARIANTS.items():
            if canonical in seen:
                continue
            for v in variants:
                v_flat = v.replace(" ", "").replace("_", "").replace("-", "")
                if n == v or n_flat == v_flat:
                    seen.add(canonical)
                    break
                if len(v) >= 4 and len(n) >= 3 and (v in n or n in v):
                    seen.add(canonical)
                    break
    return len(seen)


def _build_column_rename(df_columns):
    """Build rename dict: original column -> canonical. Each canonical used at most once.
    
    Uses a two-pass approach: exact matches first (high confidence), then substring
    matches (lower confidence) — so a loose match can't steal a slot from an exact one.
    """
    used = set()
    rename = {}

    # Pass 1: exact matches only (case-insensitive, ignoring separators)
    for col in df_columns:
        raw = col.strip()
        if not raw:
            continue
        n = raw.lower()
        n_flat = _normalize_header_cell(raw)
        for canonical, variants in _COLUMN_VARIANTS.items():
            if canonical in used:
                continue
            for v in variants:
                v_flat = v.replace(" ", "").replace("_", "").replace("-", "")
                if n == v or n_flat == v_flat:
                    rename[col] = canonical
                    used.add(canonical)
                    break

    # Pass 2: substring containment — only for still-unmapped columns & canonicals,
    # and only when both variant and column name have meaningful length
    for col in df_columns:
        if col in rename:
            continue
        raw = col.strip()
        if not raw:
            continue
        n = raw.lower()
        for canonical, variants in _COLUMN_VARIANTS.items():
            if canonical in used:
                continue
            for v in variants:
                if len(v) < 4 or len(n) < 3:
                    continue
                if v in n or n in v:
                    rename[col] = canonical
                    used.add(canonical)
                    break

    return rename


def process_csv(file_contents):
    """Parse CSV with flexible header detection and column mapping for LinkedIn, Salesforce, HubSpot, Sheets."""
    if not file_contents or len(file_contents) == 0:
        raise ValueError("File is empty")
    try:
        content_str = file_contents.decode('utf-8')
    except UnicodeDecodeError:
        content_str = file_contents.decode('latin-1')
    content_str = content_str.lstrip("\ufeff").strip()
    if not content_str:
        raise ValueError("File has no content")

    lines = content_str.split('\n')

    # Find the header: scan first 25 lines, pick the one with the MOST matches
    # (LinkedIn exports often have 3+ noise rows before the real header)
    best_header_idx = 0
    best_header_score = 0
    for i, line in enumerate(lines[:25]):
        score = _header_match_count(line)
        if score > best_header_score:
            best_header_score = score
            best_header_idx = i
    header_idx = best_header_idx
    print(f"[csv] header detection: line {header_idx} won with {best_header_score} column matches")

    # Try each delimiter; keep the one that gives the most recognized columns
    best_df = None
    best_sep = ","
    best_rename = {}

    for try_sep in [",", "\t", ";", "|"]:
        try:
            trial = pd.read_csv(io.StringIO(content_str), skiprows=header_idx, sep=try_sep)
            if trial.empty:
                continue
            trial.columns = [str(c).strip().strip('"').strip("'") for c in trial.columns]
            trial_rename = _build_column_rename(trial.columns)
            if len(trial_rename) > len(best_rename):
                best_df = trial
                best_sep = try_sep
                best_rename = trial_rename
            if len(trial_rename) >= 3:
                break
        except Exception:
            continue

    if best_df is None or best_df.empty:
        raise ValueError("CSV has no data rows")

    df = best_df
    rename = best_rename
    print(f"[csv] delimiter: {repr(best_sep)}, skipped {header_idx} noise rows")
    print(f"[csv] original columns ({len(df.columns)}): {list(df.columns)}")
    print(f"[csv] rename map: {rename}")
    df.rename(columns=rename, inplace=True)
    print(f"[csv] mapped columns: {list(df.columns)}")

    # Fallback: Full Name / Name -> First Name + Last Name
    name_col = None
    want = {"full name", "name", "contact name", "fullname", "display name"}
    for col in df.columns:
        if str(col).strip().lower() in want:
            name_col = col
            break
    if name_col is not None:
        try:
            need_first = "First Name" not in df.columns or df["First Name"].fillna("").astype(str).str.strip().eq("").all()
            need_last = "Last Name" not in df.columns or df["Last Name"].fillna("").astype(str).str.strip().eq("").all()
            if need_first or need_last:
                parts = df[name_col].fillna("").astype(str).str.strip().str.split(n=1, expand=True)
                if parts.shape[1] >= 1:
                    if "First Name" not in df.columns:
                        df["First Name"] = parts[0]
                    elif need_first:
                        df["First Name"] = parts[0]
                if parts.shape[1] >= 2:
                    if "Last Name" not in df.columns:
                        df["Last Name"] = parts[1]
                    elif need_last:
                        df["Last Name"] = parts[1]
        except Exception:
            pass  # keep existing or empty columns

    # Ensure canonical columns exist so downstream never KeyErrors
    for col in _CANONICAL:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")
    # Diagnostic: show actual data in key columns for first 2 rows
    key_cols = ["First Name", "Last Name", "Company", "Position", "URL"]
    for idx, row in df.head(2).iterrows():
        sample = {c: str(row.get(c, ""))[:40] for c in key_cols if row.get(c, "")}
        non_canonical = {str(c)[:25]: str(v)[:30] for c, v in row.items() if c not in _CANONICAL and str(v).strip()}
        print(f"[csv] row {idx}: canonical={sample}, other={non_canonical}")
    print(f"[csv] final: {len(df)} rows, {len(df.columns)} columns")
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
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Bracket-matching: find the first [ or { and its balanced closing partner.
    # This avoids the greedy-regex bug where stray brackets in prose break parsing.
    for open_ch, close_ch in [("[", "]"), ("{", "}")]:
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


async def generate_strategy(idea: str, row_count: int):
    """Generate scoring strategy with retry and smart fallback."""
    prompt = f"""User Goal: "{idea}"

Task: Create a Scoring Rubric.

CRITICAL INSTRUCTION:
1. Provide BROADER keywords (e.g., 'Investor' instead of 'SaaS Seed Investor') to ensure we don't miss targets in the first pass.
2. If the user mentions 'Investors', you MUST include: 'Partner', 'VC', 'Capital', 'Ventures', 'Angel' in keywords.
3. Your summary_analysis must be a string.

Dataset: {row_count} connections.

CATEGORY RULES (never mix — understand the EXACT relationship the user wants):
- Job/hire → people with HEADCOUNT at operating companies. VCs score 0.
- Fundraising → people who WRITE CHECKS (VCs/angels). Employees score 0.
- Sales/pilot/client → BUDGET HOLDERS who would BUY and USE the product internally.
- Partner → people who would DISTRIBUTE, RESELL, INTEGRATE, or CO-SELL the product to THEIR customers. Partners are NOT buyers — they are force multipliers. Think: agencies/BPOs (MarketStar, Accenture), complementary SaaS tools (Clay, Apollo, HubSpot), channel resellers, and platform ecosystems.
  * A "Partner" at a VC fund is NOT a business partner — that's their job title.
  * An end-user (VP RevOps who would use the tool themselves) is a CLIENT, not a partner.
- FUNDRAISING ONLY: "Power Signal" = Partner/GP/MD at VC/Fund → auto 9-10.
- PARTNER SEARCH: Prioritize people at COMPANIES that have distribution leverage (agencies, platforms, complementary tools, BPOs with hundreds of end-users). Filter OUT individual end-users and companies in unrelated industries (mining, real estate, beverages, etc.).

Return a SINGLE JSON object (all values must be strings or arrays of strings — NO nested objects):
- value_flow: "to_me"|"from_me"|"between"
- implicit_ask: 1 sentence, hyper-specific (string)
- summary_analysis: 1 sentence insight, no "We evaluated N", no restating goal (string)
- persona: 2-4 word label (string)
- anchor_domain: short (string)
- keywords: 6-10 for THIS ask (array of strings)
- boost_words: titles for THIS ask (array of strings)
- company_words: company types for THIS ask (array of strings)
- negative_words: always ["Intern","Student","Freelance","Assistant"] + irrelevant roles (array of strings)
- rubric: "Tier1(9-10): ..., Tier2(7-8): ..., Tier3(5-6): ..., Tier4(0-4): ..." as ONE flat string
- priority_signals: 3-8 short phrases for fast filter (array of strings)"""

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
                if not data.get("persona"):
                    data["persona"] = data.get("implicit_ask", idea)[:80]
                # Coerce fields the frontend renders directly — model sometimes returns dicts
                for str_field in ("rubric", "summary_analysis", "implicit_ask", "persona"):
                    val = data.get(str_field)
                    if isinstance(val, dict):
                        data[str_field] = " | ".join(f"{k}: {v}" for k, v in val.items())
                    elif val is not None and not isinstance(val, str):
                        data[str_field] = str(val)
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
    """Extract a clean profile dict from a CSV row.
    
    Tries canonical columns first, then scans all columns by header name
    so data still flows even when column mapping missed something.
    """
    fields = {}
    for key in ["First Name", "Last Name", "Position", "Company", "Industry", "Location"]:
        val = row.get(key, "")
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        val = str(val).strip()
        if val:
            fields[key] = val

    # If key fields are still empty, scan all columns by header keyword
    _FALLBACK = {
        "First Name": ["first name", "firstname", "first_name", "fname"],
        "Last Name": ["last name", "lastname", "last_name", "lname", "surname"],
        "Company": ["company", "organization", "employer", "account", "business"],
        "Position": ["position", "title", "role", "job title", "occupation"],
    }
    for canonical, hints in _FALLBACK.items():
        if fields.get(canonical):
            continue
        for col_name in row.index:
            if col_name in _CANONICAL:
                continue
            col_lower = str(col_name).strip().lower()
            if any(h in col_lower for h in hints):
                val = row.get(col_name, "")
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    continue
                val = str(val).strip()
                if val:
                    fields[canonical] = val
                    break

    # Full name fallback: if we still have no name, look for a "name" column
    if not fields.get("First Name") and not fields.get("Last Name"):
        for col_name in row.index:
            col_lower = str(col_name).strip().lower()
            if col_lower in ("name", "full name", "fullname", "contact name", "display name"):
                val = str(row.get(col_name, "")).strip()
                if val:
                    parts = val.split(None, 1)
                    fields["First Name"] = parts[0]
                    if len(parts) > 1:
                        fields["Last Name"] = parts[1]
                    break

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
   
   If you don't know enough about the fund to write something specific, say so briefly — do NOT fabricate deal history or thesis details. Never use hedging language like "potential focus" or "if they invest in X."
   
   GOOD: "[Fund name]'s early-stage fund focuses on [specific thesis]. [Person]'s track record with [known deal] signals conviction in this category. The user's product maps directly to that thesis as a [market size / category creation argument]."
   BAD: "[User's product] is the next foundational layer of..." (Do NOT use this as an opening line — it's your pitch, not their thesis. Lead with THEM, not you.)
   BAD: "[Person] could deploy this across their portfolio to help portfolio companies." (B2B sales logic, not venture logic.)
   
   --- IF CLIENT / SALES / PILOT (value_flow = "from_me") ---
   Sentence 1 — COMPANY SITUATION: What does their company do, what market force is pressuring them?
   Sentence 2 — THE BRIDGE: How does the user's offering address that? Concrete outcome (e.g. "cut costs 40%", "launch in 2 weeks without new hires").
   Sentence 3 — WHY THIS PERSON: Role, budget, pain point ownership.
   
   --- IF PARTNER (distribution / integration) ---
   Explain DISTRIBUTION math: "integrating into [Company]'s operations = N end-users from one deal." Reference company BY NAME. No filler (alignment, synergy, explore).

Return a JSON array. Each element: {{"id": <number>, "score": <float>, "symmetric_value": "<string>", "reasoning": "<max 15 words>"}}
Return ONLY the JSON array."""

    try:
        response = await client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
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
            try:
                r["score"] = float(r.get("score", 0))
            except (ValueError, TypeError):
                r["score"] = 0.0

        scored = [r for r in results if r["score"] >= 6.0]
        print(f"Batch: {len(rows)} leads → {len(results)} parsed, {len(scored)} scored 6+")
        return results
    except Exception as e:
        print(f"Batch analysis error: {e}")
        import traceback
        traceback.print_exc()
        return [{"id": i+1, "score": 0, "reasoning": "Analysis failed", "symmetric_value": ""} for i in range(len(rows))]
