from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
import pandas as pd
import asyncio
import os
import datetime
from services import process_csv, generate_strategy, analyze_lead

app = FastAPI(title="PipelineOM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://pipelineom.com", "https://www.pipelineom.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailRequest(BaseModel):
    email: str

@app.post("/subscribe")
async def subscribe(data: EmailRequest):
    email = data.email
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"💰 NEW LEAD: {email} at {timestamp}")
    try:
        file_exists = os.path.isfile("captured_leads.csv")
        with open("captured_leads.csv", "a") as f:
            if not file_exists:
                f.write("timestamp,email\n")
            f.write(f"{timestamp},{email}\n")
    except Exception as e:
        print(f"Error saving to CSV: {e}")
    return {"status": "success"}

@app.post("/analyze")
async def analyze(idea: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        # 1. Process Files
        dfs = []
        for file in files:
            contents = await file.read()
            dfs.append(process_csv(contents))
        
        if not dfs:
            raise HTTPException(status_code=400, detail="No files uploaded")
            
        df = pd.concat(dfs, ignore_index=True)
        
        # Deduplicate
        if 'URL' in df.columns:
            df = df.drop_duplicates(subset=['URL'], keep='first')
        else:
            df = df.drop_duplicates(subset=['First Name', 'Last Name', 'Company'], keep='first')
            
        df = df.fillna("") 

        if df.empty:
            raise HTTPException(status_code=400, detail="Empty CSV")

        # 2. Strategy
        strategy = await generate_strategy(idea)
        keywords = [k.lower() for k in strategy.get("keywords", [])]
        
        # 3. Fast Filter (The "Money" Logic)
        def quick_score(row):
            pos = str(row.get('Position', '')).lower()
            comp = str(row.get('Company', '')).lower()
            text = f"{pos} {comp}"
            
            # Base Keyword Match
            score = sum(1 for w in keywords if w in text)
            
            # 1. VIP Title Boost
            vip_titles = ["partner", "principal", "head", "vp", "chief", "founder", "chairman", "director", "investor"]
            if any(title in pos for title in vip_titles):
                score += 1.5 
            
            # 2. THE "WALL STREET" SIGNAL (Fix for Sequoia Capital)
            # If the company name sounds like an investment firm, boost it heavily.
            money_words = ["capital", "ventures", "fund", "equity", "partners", "investments", "asset", "wealth", "vc", "angel"]
            
            if any(word in comp for word in money_words):
                # If they are a VIP at a "Money Company", massive boost
                if any(title in pos for title in vip_titles):
                    score += 3.0 # Takes priority over almost anything else
                else:
                    score += 1.0

            return score

        df['quick_score'] = df.apply(quick_score, axis=1)
        
        # --- LOGIC CHANGE: 300 IN ---
        # Increased to 300 to ensure we catch everyone
        candidates_to_analyze = df.sort_values(by='quick_score', ascending=False).head(300)
        
        # 4. Deep Analysis (Semaphore to 50 concurrent)
        sem = asyncio.Semaphore(50) 

        async def limited_analyze(row):
            async with sem:
                return await analyze_lead(row, strategy['persona'])

        tasks = [limited_analyze(row) for _, row in candidates_to_analyze.iterrows()]
        enrichments = await asyncio.gather(*tasks)

        # 5. Merge & Sort
        results = []
        for (index, row), enrichment in zip(candidates_to_analyze.iterrows(), enrichments):
            ai_score = enrichment.get('score', 0)
            
            # Strict Filter: Only show 6/10 or higher for final results
            if ai_score >= 6:
                results.append({
                    "name": f"{row.get('First Name', '')} {row.get('Last Name', '')}",
                    "company": row.get('Company', ''),
                    "role": row.get('Position', ''),
                    "score": ai_score,
                    "reasoning": enrichment.get('reasoning', ''),
                })

        final_results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        return {
            "strategy": strategy,
            "data": final_results[:20] 
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)