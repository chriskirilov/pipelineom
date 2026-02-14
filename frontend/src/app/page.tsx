"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Upload, ArrowRight, Lock, Zap, Layers, Unlock, RotateCcw 
} from "lucide-react";
import axios from "axios";
import { siteConfig } from "@/config/site";

export default function Home() {
  const [idea, setIdea] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [status, setStatus] = useState<"idle" | "analyzing" | "done">("idle");
  const [results, setResults] = useState<any[]>([]);
  const [strategy, setStrategy] = useState<any>(null);
  const [email, setEmail] = useState("");
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

      // ENSURE ALL FIELDS ARE PRESENT
      await axios.post(`${siteConfig.api.url}/send-report`, {
        email: email,
        leads: results || [],
        query: idea || "Network Analysis",
        persona: strategy?.persona || "Targeted Leads",
        summary_analysis: strategy?.summary_analysis || strategy?.summary || "Analysis complete." 
      });
      
    } catch (e) {
      console.error("Email delivery failed", e);
      // Keep it unlocked for UX even if email fails
      setIsUnlocked(true);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-100">
      
      {/* Navbar */}
      <nav className="fixed w-full z-50 top-0 border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="font-bold text-xl tracking-tight flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">OM</div>
            {siteConfig.name}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-12 px-6 max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-sm font-medium mb-6">
          <Zap className="w-3 h-3 fill-current" /> AI-Powered Network Audit
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-slate-900 mb-6 leading-tight">
          {siteConfig.hero.title} <br className="hidden md:block" />
          Your{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
            {siteConfig.hero.highlight}
          </span>
        </h1>
        
        <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
          {siteConfig.hero.subtitle}
        </p>
      </section>

      {/* Main Interface */}
      <section className="px-4 pb-20 max-w-4xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden relative"
        >
          {status === "analyzing" && (
            <div className="absolute inset-0 z-50 bg-white/95 backdrop-blur-sm flex flex-col items-center justify-center p-8 text-center">
               <div className="w-full max-w-sm space-y-4">
                  <div className="relative w-16 h-16 mx-auto">
                     <div className="absolute inset-0 border-4 border-indigo-100 rounded-full"></div>
                     <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">{loadingMessage}</h3>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div 
                      className="h-full bg-indigo-600 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ ease: "linear" }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 font-mono">Value-optimization engine...</p>
               </div>
            </div>
          )}

          {status === "done" ? (
             <div className="p-0">
                {/* Header with Dynamic Query & Persona */}
                <div className="p-6 bg-slate-50 border-b border-slate-100 flex flex-col md:flex-row md:items-start justify-between gap-6">
                  <div className="space-y-3 max-w-2xl">
                    <div>
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                            <Zap className="w-3 h-3 text-indigo-500" /> What we analyzed
                        </div>
                        <p className="text-lg font-medium text-slate-900 leading-snug">
                            {idea}
                        </p>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => setStatus("idle")}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 text-slate-600 rounded-lg font-medium transition-all shadow-sm hover:shadow-md active:scale-95 text-sm h-fit"
                  >
                    <RotateCcw className="w-4 h-4" /> New Scan
                  </button>
                </div>

                <div className="p-6">
                  <p className="text-base text-slate-600 leading-relaxed mb-6">
                    {strategy?.summary_analysis}
                  </p>

                  <div className="flex items-center gap-2 mb-4">
                    <div className={`w-2 h-2 rounded-full ${isUnlocked ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`}></div>
                    <p className="text-sm font-bold text-slate-500 uppercase tracking-tight">
                      {isUnlocked ? `Final Report: ${results.length} Candidates` : "Priority Preview (Locked)"}
                    </p>
                  </div>

                  {/* Results Table — Tactical Briefing */}
                  <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="grid grid-cols-12 bg-slate-50 border-b border-slate-200 py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-widest">
                      <div className="col-span-1">Utility</div>
                      <div className="col-span-3">Profile</div>
                      <div className="col-span-8">Tactical Briefing</div>
                    </div>

                    {(isUnlocked ? results : results.slice(0, 3)).map((r, i) => (
                      <div key={i} className="grid grid-cols-12 py-5 px-4 border-b border-slate-100 items-start hover:bg-slate-50/80 transition-colors animate-in fade-in slide-in-from-bottom-2 duration-500">
                        <div className="col-span-1">
                          <span className={`inline-flex items-center justify-center w-10 h-8 rounded-lg font-bold text-sm shadow-sm
                            ${r.score >= 9.0 ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 
                              r.score >= 7.5 ? 'bg-blue-100 text-blue-800 border border-blue-200' : 
                              r.score >= 5.0 ? 'bg-amber-100 text-amber-800 border border-amber-200' : 
                              'bg-slate-100 text-slate-500'}
                          `}>
                            {r.score}
                          </span>
                        </div>
                        <div className="col-span-3 pr-4">
                          <div className="font-bold text-slate-900 leading-tight mb-0.5">{r.name}</div>
                          <div className="text-xs text-slate-700 font-semibold">{r.role}</div>
                          <div className="text-sm text-slate-400 mt-1">{r.company}</div>
                        </div>
                        <div className="col-span-8">
                          {r.symmetric_value && (
                            <p className="text-base text-slate-700 leading-snug"><span className="font-semibold text-slate-600">Win-win:</span> {r.symmetric_value}</p>
                          )}
                        </div>
                      </div>
                    ))}

                    {!isUnlocked && (
                      <div className="relative bg-slate-50 py-20 text-center border-t border-slate-200">
                        <div className="absolute inset-0 bg-white/70 backdrop-blur-[4px] z-10"></div>
                        <div className="relative z-20 max-w-md mx-auto bg-white p-8 rounded-2xl shadow-2xl border border-slate-200">
                          <div className="w-14 h-14 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 ring-8 ring-indigo-50">
                              <Lock className="w-6 h-6" />
                          </div>
                          <h4 className="text-2xl font-bold text-slate-900 mb-2">Get Full Report</h4>
                          <p className="text-slate-500 mb-8">We found <strong>{results.length}</strong> high-authority leads. We'll email the full CSV analysis and unlock the results below.</p>
                          
                          <div className="space-y-4">
                              <input 
                                  type="email" 
                                  placeholder="Enter your email" 
                                  className="w-full px-5 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all shadow-inner text-lg"
                                  value={email}
                                  onChange={(e) => setEmail(e.target.value)}
                              />
                              <button 
                                  onClick={handleUnlock}
                                  className="w-full bg-indigo-600 text-white font-bold py-4 rounded-xl hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-xl shadow-indigo-100 group"
                              >
                                  <Unlock className="w-5 h-5 group-hover:rotate-12 transition-transform" /> Unlock & Email Report
                              </button>
                          </div>
                          <p className="text-xs text-slate-400 mt-5 uppercase tracking-widest font-bold">1-Click PDF & CSV Export</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
             </div>
          ) : (
            /* Input View */
            <div className="p-8 md:p-12 space-y-10">
              <div className="space-y-4">
                <label className="flex items-center gap-2 text-sm font-bold text-slate-500 uppercase tracking-widest">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white text-[10px]">1</span>
                  Define your objective
                </label>
                <textarea 
                  className="w-full p-5 rounded-2xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all resize-none text-xl font-medium placeholder:text-slate-300"
                  rows={2}
                  placeholder="e.g. Find clients for for my startup doing X..."
                  value={idea}
                  onChange={(e) => setIdea(e.target.value)}
                />
              </div>

              <div className="space-y-4">
                <label className="flex items-center gap-2 text-sm font-bold text-slate-500 uppercase tracking-widest">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white text-[10px]">2</span>
                  Data Sources
                </label>
                <div className="relative group">
                  <input 
                    type="file" 
                    accept=".csv"
                    multiple
                    onChange={(e) => setFiles(e.target.files)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                  />
                  <div className="border-2 border-dashed border-slate-200 rounded-2xl p-10 flex flex-col items-center justify-center hover:bg-indigo-50/50 transition-all bg-slate-50 group-hover:border-indigo-300">
                    {files && files.length > 0 ? (
                      <div className="flex flex-col items-center animate-in zoom-in">
                        <Layers className="w-12 h-12 text-indigo-600 mb-3" />
                        <p className="text-xl font-bold text-slate-900">{files.length} Connections Files</p>
                        <p className="text-sm text-slate-500 mt-1 font-medium">Ready for deep-scan analysis</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-slate-400 group-hover:text-indigo-500 transition-colors">
                        <Upload className="w-12 h-12 mb-3" />
                        <p className="text-lg font-bold">Upload LinkedIn Connections</p>
                        <p className="text-sm font-medium">Drag & drop your .csv exports here</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <button 
                onClick={handleAnalyze}
                disabled={!files || !idea || status !== "idle"}
                className={`w-full py-5 rounded-2xl font-bold text-xl flex items-center justify-center gap-2 transition-all transform active:scale-[0.98]
                  ${!files || !idea 
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xl shadow-indigo-100'
                  }
                `}
              >
                Analyze Network <ArrowRight className="w-6 h-6" />
              </button>
            </div>
          )}
        </motion.div>
      </section>
    </main>
  );
}