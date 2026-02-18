"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Upload, ArrowRight, Lock, Zap, Layers, Unlock, RotateCcw 
} from "lucide-react";
import axios from "axios";
import { siteConfig } from "@/config/site";
import Image from 'next/image';

export default function Home() {
  const [idea, setIdea] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [status, setStatus] = useState<"idle" | "analyzing" | "done">("idle");
  const [results, setResults] = useState<any[]>([]);
  const [strategy, setStrategy] = useState<any>(null);
  const [email, setEmail] = useState("");
  const [sessionId, setSessionId] = useState<string>("");
  const [isUnlocked, setIsUnlocked] = useState(false);
  
  // Loading State
  const [loadingMessage, setLoadingMessage] = useState("Initializing...");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (status === "analyzing") {
      const messages = [
        "Extracting your Current Ask...",
        "Mapping value flow...",
        "Triple-Fit: Resource, Gravity, Why Now...",
        "Building tactical briefings...",
        "Finalizing priority list..."
      ];
      let i = 0;
      setLoadingMessage(messages[0]);
      
      const interval = setInterval(() => {
        i = (i + 1) % messages.length;
        setLoadingMessage(messages[i]);
      }, 1200);

      const progressInterval = setInterval(() => {
        setProgress((old) => (old >= 95 ? 95 : old + 5));
      }, 400);

      return () => {
        clearInterval(interval);
        clearInterval(progressInterval);
      };
    }
  }, [status]);

  const handleAnalyze = async () => {
    if (!files || files.length === 0 || !idea) return;
    
    const formData = new FormData();
    formData.append("idea", idea);
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    try {
      setStatus("analyzing");
      setIsUnlocked(false); 
      
      const response = await axios.post(`${siteConfig.api.url}/analyze`, formData);
      setStrategy(response.data.strategy);
      setResults(response.data.data);
      setSessionId(response.data.session_id || "");
      setProgress(100);
      setTimeout(() => setStatus("done"), 500);
      
    } catch (e) {
      alert("Analysis failed. Ensure backend is running.");
      setStatus("idle");
    }
  };

  const handleUnlock = async () => {
    if (!email.includes("@")) {
      alert("Please enter a valid email address.");
      return;
    }

    try {
      setIsUnlocked(true); 

      await axios.post(`${siteConfig.api.url}/send-report`, {
        email: email,
        leads: results || [],
        query: idea || "Network Analysis",
        persona: strategy?.persona || "Targeted Leads",
        summary_analysis: strategy?.summary_analysis || strategy?.summary || "Analysis complete.",
        session_id: sessionId,
      });
      
    } catch (e) {
      console.error("Email delivery failed", e);
      // Keep it unlocked for UX even if email fails
      setIsUnlocked(true);
    }
  };

  return (
    <main className="min-h-screen bg-white text-stone-900 font-sans selection:bg-stone-200">
      
      {/* Navbar */}
      <nav className="fixed w-full z-50 top-0 border-b border-[#e7e5e4] bg-white/95 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Image
              src="/logo.png"
              alt="PipelineOM Logo"
              width={32}
              height={32}
              className="rounded-md"
            />
            <span className="font-serif text-xl font-semibold tracking-tight text-stone-900">PipelineOM</span>
          </div>
        </div>
      </nav>

      {/* Hero — same product family copy */}
      <section className="pt-32 pb-12 px-6 max-w-3xl mx-auto text-center">
        <h1 className="font-serif text-4xl md:text-5xl font-medium tracking-tight text-stone-900 mb-6 leading-tight">
          {siteConfig.hero?.headline ?? "Your network has signal. You just can't see it yet."}
        </h1>
        <p className="text-lg text-stone-600 max-w-xl mx-auto leading-relaxed">
          {siteConfig.hero?.subtitle ?? "Upload any CSV with leads (LinkedIn, CRM export, spreadsheet) — we surface the right people for your goal in under a minute."}
        </p>
      </section>

      {/* Main Interface — same card borders as homepage */}
      <section className="px-4 pb-20 max-w-4xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl border border-[#e7e5e4] shadow-sm overflow-hidden relative"
        >
          {status === "analyzing" && (
            <div className="absolute inset-0 z-50 bg-[#fafaf9]/95 backdrop-blur-sm flex flex-col items-center justify-center p-8 text-center">
               <div className="w-full max-w-sm space-y-4">
                  <div className="relative w-14 h-14 mx-auto">
                     <div className="absolute inset-0 border-2 border-stone-200 rounded-full"></div>
                     <div className="absolute inset-0 border-2 border-stone-500 rounded-full border-t-transparent animate-spin"></div>
                  </div>
                  <h3 className="font-serif text-xl font-medium text-stone-900">{loadingMessage}</h3>
                  <div className="w-full h-1.5 bg-stone-200 rounded-full overflow-hidden">
                    <motion.div 
                      className="h-full bg-stone-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ ease: "linear" }}
                    />
                  </div>
                  <p className="text-xs text-stone-400">Mapping signal...</p>
               </div>
            </div>
          )}

          {status === "done" ? (
             <div className="p-0">
                {/* Header */}
                <div className="p-6 bg-[#fafaf9] border-b border-[#e7e5e4] flex flex-col md:flex-row md:items-start justify-between gap-6">
                  <div className="space-y-3 max-w-2xl">
                    <div>
                        <div className="text-xs font-medium text-stone-500 uppercase tracking-wider mb-1">
                            What we analyzed
                        </div>
                        <p className="font-serif text-lg text-stone-900 leading-snug">
                            {idea}
                        </p>
                    </div>
                  </div>
                  <button 
                    onClick={() => {
                        setStatus("idle");
                        setFiles(null);
                        setIdea("");
                    }}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-[#e7e5e4] hover:border-stone-400 hover:text-stone-800 text-stone-600 rounded-lg font-medium transition-all text-sm h-fit"
                  >
                    <RotateCcw className="w-4 h-4" /> New Scan
                  </button>
                </div>

                <div className="p-6">
                  <p className="text-base text-stone-600 leading-relaxed mb-6">
                    {strategy?.summary_analysis || strategy?.summary || "Analysis complete. Review the top candidates below."}
                  </p>

                  <div className="flex items-center gap-2 mb-4">
                    <div className={`w-2 h-2 rounded-full ${isUnlocked ? 'bg-stone-600' : 'bg-amber-500 animate-pulse'}`}></div>
                    <p className="text-sm font-medium text-stone-500 uppercase tracking-wide">
                      {isUnlocked ? `Report: ${results.length} candidates` : "Preview (locked)"}
                    </p>
                  </div>

                  {/* Results Table — Pulse-style bar + number, muted palette */}
                  <div className="border border-[#e7e5e4] rounded-lg overflow-hidden">
                    <div className="grid grid-cols-12 bg-[#fafaf9] border-b border-[#e7e5e4] py-3 px-4 text-xs font-medium text-stone-500 uppercase tracking-wide">
                      <div className="col-span-2">Score</div>
                      <div className="col-span-3">Profile</div>
                      <div className="col-span-7">Tactical Briefing</div>
                    </div>

                    {(isUnlocked ? results : results.slice(0, 3)).map((r, i) => (
                      <div key={i} className="grid grid-cols-12 py-4 px-4 border-b border-[#e7e5e4] last:border-b-0 items-center hover:bg-[#fafaf9]/60 transition-colors">
                        <div className="col-span-2 flex items-center gap-3">
                          <div className="flex-1 h-2 bg-stone-200 rounded-full overflow-hidden max-w-[80px]">
                            <div 
                              className="h-full bg-stone-500 rounded-full"
                              style={{ width: `${Math.min(100, (r.score / 10) * 100)}%` }}
                            />
                          </div>
                          <span className="font-serif text-stone-700 font-medium tabular-nums w-8">{r.score}</span>
                        </div>
                        <div className="col-span-3 pr-4">
                          <div className="font-medium text-stone-900 leading-tight mb-0.5">
                            {r.name || 'Unknown'}
                          </div>
                          <div className="text-xs text-stone-600">{r.role || r.Position || r.position || '—'}</div>
                          <div className="text-sm text-stone-400 mt-0.5">{r.company || r.Company || '—'}</div>
                        </div>
                        <div className="col-span-7 pl-2">
                          {r.symmetric_value ? (
                            <p className="text-sm text-stone-700 leading-snug"><span className="font-medium text-stone-600">Why them: </span> {r.symmetric_value}</p>
                          ) : (
                            <p className="text-sm text-stone-500 italic">High authority match based on industry signals.</p>
                          )}
                        </div>
                      </div>
                    ))}

                    {!isUnlocked && results.length > 0 && (
                      <div className="relative bg-[#fafaf9] py-20 text-center border-t border-[#e7e5e4]">
                        <div className="absolute inset-0 bg-white/70 backdrop-blur-[4px] z-10"></div>
                        <div className="relative z-20 max-w-md mx-auto bg-white p-8 rounded-xl border border-[#e7e5e4] shadow-sm">
                          <div className="w-12 h-12 bg-stone-200 text-stone-600 rounded-full flex items-center justify-center mx-auto mb-4">
                              <Lock className="w-5 h-5" />
                          </div>
                          <h4 className="font-serif text-xl font-medium text-stone-900 mb-2">Get full report</h4>
                          <p className="text-stone-500 mb-6 text-sm">We found <strong>{results.length}</strong> high-signal leads. Enter your email to receive the CSV and unlock the list below.</p>
                          <div className="space-y-3">
                              <input 
                                  type="email" 
                                  placeholder="Enter your email" 
                                  className="w-full px-4 py-3 border border-[#e7e5e4] rounded-lg focus:ring-2 focus:ring-stone-400 focus:border-stone-400 outline-none transition-all text-stone-900"
                                  value={email}
                                  onChange={(e) => setEmail(e.target.value)}
                              />
                              <button 
                                  onClick={handleUnlock}
                                  className="w-full bg-stone-800 text-white font-medium py-3 rounded-lg hover:bg-stone-900 transition-all flex items-center justify-center gap-2 group"
                              >
                                  <Unlock className="w-4 h-4" /> Unlock & email report
                              </button>
                          </div>
                          <p className="text-xs text-stone-400 mt-4">Includes CSV export</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Pulse bridge — on-ramp to design partner */}
                  <div className="mt-8 p-5 rounded-lg border border-[#e7e5e4] bg-[#fafaf9]">
                    <p className="text-sm text-stone-600 leading-relaxed">
                      <span className="font-medium text-stone-700">This is one signal source.</span> Pulse connects your CRM, email, and calendar so you see who’s in motion — and when to reach out. <a href="#" className="text-stone-800 underline underline-offset-2 hover:no-underline">Join the design partner waitlist</a>.
                    </p>
                  </div>
                </div>
             </div>
          ) : (
            /* Input View */
            <div className="p-8 md:p-12 space-y-10">
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-stone-500 uppercase tracking-wide">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-stone-300 text-stone-700 text-[10px] font-semibold">1</span>
                  Define your objective
                </label>
                <textarea 
                  className="w-full p-4 rounded-lg border border-[#e7e5e4] bg-[#fafaf9] focus:bg-white focus:ring-2 focus:ring-stone-400 focus:border-stone-400 outline-none transition-all resize-none text-base placeholder:text-stone-400"
                  rows={2}
                  placeholder="e.g. Find investors for a pre-seed round..."
                  value={idea}
                  onChange={(e) => setIdea(e.target.value)}
                />
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-stone-500 uppercase tracking-wide">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-stone-300 text-stone-700 text-[10px] font-semibold">2</span>
                  Upload leads CSV
                </label>
                <div className="relative group">
                  <input 
                    type="file" 
                    accept=".csv"
                    multiple
                    onChange={(e) => setFiles(e.target.files)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                  />
                  <div className="border-2 border-dashed border-[#e7e5e4] rounded-lg p-10 flex flex-col items-center justify-center hover:border-stone-400 hover:bg-[#fafaf9] transition-all bg-[#fafaf9]/50">
                    {files && files.length > 0 ? (
                      <div className="flex flex-col items-center">
                        <Layers className="w-10 h-10 text-stone-600 mb-2" />
                        <p className="font-medium text-stone-900">{files.length} CSV file{files.length !== 1 ? 's' : ''}</p>
                        <p className="text-sm text-stone-500 mt-0.5">Any CSV with leads — LinkedIn, CRM, spreadsheet. Ready to analyze.</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-stone-500 group-hover:text-stone-700 transition-colors">
                        <Upload className="w-10 h-10 mb-2" />
                        <p className="font-medium">Upload any CSV with leads</p>
                        <p className="text-sm mt-0.5">LinkedIn export, CRM list, or spreadsheet — drag & drop here</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <button 
                onClick={handleAnalyze}
                disabled={!files || !idea || status !== "idle"}
                className={`w-full py-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
                  ${!files || !idea 
                    ? 'bg-stone-200 text-stone-400 cursor-not-allowed' 
                    : 'bg-stone-800 hover:bg-stone-900 text-white'
                  }
                `}
              >
                Analyze network <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#e7e5e4] bg-white py-8">
        <div className="max-w-5xl mx-auto px-6 text-center text-sm text-stone-500">
          <p>PipelineOM — built for the autonomous enterprise</p>
        </div>
      </footer>
    </main>
  );
}