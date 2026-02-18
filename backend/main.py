from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
import pandas as pd
import asyncio
import os
import datetime
import uuid
import resend
import csv
from io import StringIO
from sqlalchemy import update
from services import process_csv, generate_strategy, analyze_leads_batch, _build_lead_profile
from database import SessionLocal, GlobalLead, SiteEmail

app = FastAPI(title="OM API")
@app.get("/")
async def health_check():
    return {"status": "online", "message": "OM API is awake and ready."}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pipelineom.vercel.app",
        "https://pipelineom.com",
        "https://www.pipelineom.com",
        "https://pulse.pipelineom.com",
        "https://www.pulse.pipelineom.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email Setup
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailRequest(BaseModel):
    email: str

class ReportRequest(BaseModel):
    email: str
    leads: List[dict]
    query: str
    persona: str
    summary_analysis: str = ""
    session_id: str = ""

@app.post("/subscribe")
async def subscribe(data: EmailRequest):
    email = data.email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    print(f"💰 NEW LEAD (subscribe): {email}")
    db = SessionLocal()
    try:
        db.add(SiteEmail(email=email, source="subscribe"))
        db.commit()
    except Exception as e:
        print(f"Subscribe DB Error: {e}")
    finally:
        db.close()
    return {"status": "success"}

@app.post("/send-report")
async def send_report(data: ReportRequest):
    email = (data.email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")

    db = SessionLocal()
    try:
        if data.session_id:
            stmt = update(GlobalLead).where(GlobalLead.session_id == data.session_id).values(owner_email=email)
            db.execute(stmt)
        db.add(SiteEmail(email=email, source="report_unlock"))
        db.commit()
    except Exception as e:
        print(f"Send-report DB Error: {e}")
    finally:
        db.close()

    try:
        # 1. Short attachment filename
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        filename = f"OM_Report_{date_str}.csv"

        # 2. Generate CSV in Memory
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Name", "Role", "Company", "Utility Score", "Symmetric Value", "Reasoning"])
        for lead in data.leads:
            writer.writerow([
                lead.get("name", ""),
                lead.get("role", ""),
                lead.get("company", ""),
                lead.get("score", ""),
                lead.get("symmetric_value", ""),
                lead.get("reasoning", "")
            ])
        csv_content = csv_buffer.getvalue()
        
        # 3. Contextual Email Body
        top_lead = data.leads[0]['name'] if data.leads else "high-value matches"
        
        params = {
"from": "OM <no-reply@leads.pipelineom.com>",
            "to": [data.email],
            "subject": "Your OM report",
            "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; color: #1e293b; line-height: 1.6;">
                    <h2 style="color: #4f46e5;">Your Network Analysis is Ready</h2>
                    <p>We analyzed your connections to help with your goal: <strong>"{data.query}"</strong></p>
                    
                    <div style="background: #f8fafc; padding: 20px; border-left: 4px solid #4f46e5; margin: 20px 0;">
                        <p style="margin: 0; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 12px; letter-spacing: 0.05em;">Overview</p>
                        <p style="margin: 5px 0 0 0; color: #334155;">{data.summary_analysis}</p>
                    </div>
                    
                    <h3>Proposed Next Steps:</h3>
                    <ul style="padding-left: 20px;">
                        <li><strong>High Priority:</strong> Reach out to <strong>{top_lead}</strong>. Based on their authority and industry presence, they are a primary decision-maker for your goal.</li>
                        <li><strong>Leverage the List:</strong> The attached CSV contains 20 leads filtered by hiring authority and budget stability.</li>
                        <li><strong>Refine Your Pitch:</strong> Focus on the specific value points mentioned in the "Reasoning" column of the report.</li>
                    </ul>
                    
                    <p style="margin-top: 30px; font-size: 14px; color: #64748b;">
                        The full detailed report is attached to this email. Good luck with your outreach!
                    </p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
                    <p style="font-size: 11px; color: #94a3b8; text-align: center;">Powered by OM — Built for the Autonomous Enterprise</p>
                </div>
            """,
            "attachments": [
                {
                    "filename": filename, 
                    "content": list(csv_content.encode("utf-8"))
                }
            ]
        }
        resend.Emails.send(params)
        return {"status": "success"}
    except Exception as e:
        print(f"Email Error: {e}")
        return {"status": "error", "detail": str(e)}

MAX_TOTAL_UPLOAD_MB = 10  # Total file size limit across all uploaded files

@app.post("/analyze")
async def analyze(idea: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        # 1. Process Files (with size limit)
        dfs = []
        total_bytes = 0
        for file in files:
            contents = await file.read()
            total_bytes += len(contents)
            if total_bytes > MAX_TOTAL_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"Total upload exceeds {MAX_TOTAL_UPLOAD_MB}MB limit.")
            try:
                dfs.append(process_csv(contents))
            except Exception as csv_err:
                raise HTTPException(status_code=400, detail=f"Could not parse CSV '{getattr(file, 'filename', 'file')}': {str(csv_err)}")
        
        if not dfs:
            raise HTTPException(status_code=400, detail="No files uploaded")
            
        df = pd.concat(dfs, ignore_index=True)
        print(f"[analyze] raw rows: {len(df)}, columns: {list(df.columns)}")
        
        # Deduplicate — only on columns that have real data, never on empty values
        df = df.fillna("")
        url_col = df['URL'].astype(str).str.strip() if 'URL' in df.columns else pd.Series(dtype=str)
        has_real_urls = url_col.ne("").any()

        if has_real_urls:
            url_mask = url_col.ne("")
            df_with_url = df[url_mask].drop_duplicates(subset=['URL'], keep='first')
            df_without_url = df[~url_mask]
            # For rows without URL, dedup on name+company if those have data
            name_cols = [c for c in ['First Name', 'Last Name', 'Company'] if c in df_without_url.columns and df_without_url[c].astype(str).str.strip().ne("").any()]
            if name_cols:
                df_without_url = df_without_url.drop_duplicates(subset=name_cols, keep='first')
            df = pd.concat([df_with_url, df_without_url], ignore_index=True)
        else:
            dedup_cols = [c for c in ['First Name', 'Last Name', 'Company'] if c in df.columns and df[c].astype(str).str.strip().ne("").any()]
            if dedup_cols:
                df = df.drop_duplicates(subset=dedup_cols, keep='first')

        print(f"[analyze] after dedup: {len(df)} rows")

        if df.empty:
            raise HTTPException(status_code=400, detail="Empty CSV")

        # --- DB: Save all rows to GlobalLead ---
        session_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            records = []
            for _, row in df.iterrows():
                records.append(GlobalLead(
                    session_id=session_id,
                    first_name=str(row.get("First Name", "")),
                    last_name=str(row.get("Last Name", "")),
                    url=str(row.get("URL", "")),
                    company=str(row.get("Company", "")),
                    position=str(row.get("Position", "")),
                    connected_on=str(row.get("Connected On", "")),
                ))
            db.add_all(records)
            db.commit()
        except Exception as e:
            print(f"DB Insert Error: {e}")
        finally:
            db.close()

        # 2. Get Dynamic Strategy from Architect
        row_count = len(df)
        strategy = await generate_strategy(idea, row_count)
        
        keywords = [k.lower() for k in strategy.get("keywords", []) if isinstance(k, str)]
        boost_words = [b.lower() for b in strategy.get("boost_words", []) if isinstance(b, str)]
        company_words = [c.lower() for c in strategy.get("company_words", []) if isinstance(c, str)]
        negative_words = [n.lower() for n in strategy.get("negative_words", ["intern", "student"]) if isinstance(n, str)]
        priority_signals = [s.lower() for s in strategy.get("priority_signals", []) if isinstance(s, str)]
        
        # 3. Fast Filter — score everyone, take top 100. This is just prioritization, NOT elimination.
        # The AI batch scorer does the real filtering.
        def quick_score(row):
            pos = str(row.get('Position', '')).lower()
            comp = str(row.get('Company', '')).lower()
            text = f"{pos} {comp}"
            score = 0
            score += sum(1 for w in keywords if w in text)
            score += sum(2 for w in boost_words if w in pos)
            score += sum(2 for w in company_words if w in comp)
            score += sum(1 for w in priority_signals if w in text)
            for w in negative_words:
                if w in pos:
                    score -= 5
            return score

        df['quick_score'] = df.apply(quick_score, axis=1)
        
        # Take top 100 — if few have positive scores, still take 100 to give the AI enough to work with.
        candidates_df = df.sort_values(by='quick_score', ascending=False).head(100)
        print(f"[analyze] candidates: {len(candidates_df)}, top quick_scores: {candidates_df['quick_score'].head(5).tolist()}")
        
        # 4. Batch Analysis — 10 batches of 10, all in parallel (~3-4s)
        candidate_rows = [row for _, row in candidates_df.iterrows()]
        batch_size = 10
        batches = [candidate_rows[i:i+batch_size] for i in range(0, len(candidate_rows), batch_size)]
        
        batch_tasks = [analyze_leads_batch(batch, strategy, idea) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # 5. Flatten and match results back to candidates
        results = []
        for batch_idx, batch_enrichments in enumerate(batch_results):
            batch = batches[batch_idx]
            enrichment_map = {}
            for i, r in enumerate(batch_enrichments):
                try:
                    rid = int(r.get("id", i + 1))
                except (ValueError, TypeError):
                    rid = i + 1
                enrichment_map[rid] = r

            for i, row in enumerate(batch):
                enrichment = enrichment_map.get(i + 1, None)
                if enrichment is None and i < len(batch_enrichments):
                    enrichment = batch_enrichments[i]
                if enrichment is None:
                    enrichment = {"score": 0, "reasoning": "", "symmetric_value": ""}
                try:
                    ai_score = float(enrichment.get("score", 0))
                except (ValueError, TypeError):
                    ai_score = 0.0
                profile = _build_lead_profile(row)
                results.append({
                    "name": f"{profile.get('First Name', '')} {profile.get('Last Name', '')}".strip(),
                    "company": profile.get('Company', ''),
                    "role": profile.get('Position', ''),
                    "score": ai_score,
                    "reasoning": enrichment.get('reasoning', ''),
                    "symmetric_value": enrichment.get('symmetric_value', ''),
                })

        final_results = sorted(results, key=lambda x: x['score'], reverse=True)[:20]
        meaningful_count = sum(1 for r in final_results if r['score'] > 0)
        print(f"[analyze] total scored: {len(results)}, meaningful (>0): {meaningful_count}, returning: {len(final_results)}, top scores: {[r['score'] for r in final_results[:5]]}")
        
        return {
            "session_id": session_id,
            "strategy": strategy,
            "data": final_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)