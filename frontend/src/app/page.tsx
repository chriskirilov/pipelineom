"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Upload, ArrowRight, Lock, CheckCircle2, Search, Zap, Layers, Unlock } from "lucide-react";
import axios from "axios";
import { siteConfig } from "@/config/site";

export default function Home() {
  const [idea, setIdea] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "analyzing" | "done">("idle");
  const [results, setResults] = useState<any[]>([]);
  const [strategy, setStrategy] = useState<any>(null);
  
  // New State for the Lead Magnet
  const [email, setEmail] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);

  const handleAnalyze = async () => {
    if (!files || files.length === 0 || !idea) return;
    
    const formData = new FormData();
    formData.append("idea", idea);
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    try {
      setStatus("analyzing");
      // Reset unlock state on new search
      setIsUnlocked(false); 
      
      const response = await axios.post(`${siteConfig.api.url}/analyze`, formData);
      setStrategy(response.data.strategy);
      setResults(response.data.data);
      setStatus("done");
    } catch (e) {
      alert("Error: Ensure Backend is running on port 8000");
      setStatus("idle");
    }
  };

  const handleUnlock = async () => {
    if (!email.includes("@")) {
      alert("Please enter a valid email address.");
      return;
    }

    try {
      // 1. Send to Backend
      await axios.post(`${siteConfig.api.url}/subscribe`, { email });
      
      // 2. Unlock the View
      setIsUnlocked(true);
      
    } catch (e) {
      console.error("Subscription error", e);
      // Optional: Unlock anyway even if API fails, to be nice to the user
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
      <section className="pt-32 pb-12 px-6 max-w-4xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-sm font-medium mb-6">
          <Zap className="w-3 h-3 fill-current" /> Free Network Audit
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-slate-900 mb-6">
          {siteConfig.hero.title} <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
            {siteConfig.hero.highlight}
          </span>
        </h1>
      </section>

      {/* Main Interface */}
      <section className="px-4 pb-20 max-w-3xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden"
        >
          {status === "done" ? (
             // Results View
             <div className="p-8">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">Targeting: {strategy?.persona}</h3>
                    <p className="text-sm text-slate-500">
                      {isUnlocked ? `Showing all ${results.length} candidates.` : "Showing Top 3 Preview."}
                    </p>
                  </div>
                  <button onClick={() => setStatus("idle")} className="text-sm font-medium text-indigo-600 hover:underline">New Scan</button>
                </div>

                <div className="border border-slate-100 rounded-xl overflow-hidden">
                  {/* Header */}
                  <div className="grid grid-cols-12 bg-slate-50 border-b border-slate-100 py-3 px-4 text-xs font-bold text-slate-400 uppercase">
                    <div className="col-span-2">Score</div>
                    <div className="col-span-4">Profile</div>
                    <div className="col-span-6">Reasoning</div>
                  </div>

                  {/* THE DISPLAY LOGIC: 
                      If unlocked, show ALL. 
                      If locked, show only first 3.
                  */}
                  {(isUnlocked ? results : results.slice(0, 3)).map((r, i) => (
                    <div key={i} className="grid grid-cols-12 py-4 px-4 border-b border-slate-50 items-start hover:bg-slate-50 transition-colors animate-in fade-in slide-in-from-bottom-2 duration-500">
                      <div className="col-span-2">
                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-700 font-bold text-sm">
                          {r.score}
                        </span>
                      </div>
                      <div className="col-span-4 pr-2">
                        <div className="font-bold text-slate-900">{r.name}</div>
                        <div className="text-xs text-slate-500">{r.role}</div>
                        <div className="text-xs text-slate-400 mt-0.5">{r.company}</div>
                      </div>
                      <div className="col-span-6">
                        <p className="text-sm text-slate-600 leading-snug">{r.reasoning}</p>
                      </div>
                    </div>
                  ))}

                  {/* THE GATE (Only shows if NOT unlocked) */}
                  {!isUnlocked && (
                    <div className="relative bg-slate-50 py-16 text-center border-t border-slate-100">
                      {/* Blur Effect Overlay */}
                      <div className="absolute inset-0 bg-white/60 backdrop-blur-[3px] z-10"></div>
                      
                      {/* The Email Form */}
                      <div className="relative z-20 max-w-sm mx-auto bg-white p-8 rounded-2xl shadow-xl border border-slate-200 ring-1 ring-slate-900/5">
                        <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Lock className="w-6 h-6" />
                        </div>
                        <h4 className="text-xl font-bold text-slate-900 mb-2">Unlock Top 20 Leads</h4>
                        <p className="text-sm text-slate-500 mb-6">Enter your email to reveal the full list of high-value prospects hidden in your network.</p>
                        
                        <div className="space-y-3">
                            <input 
                                type="email" 
                                placeholder="name@company.com" 
                                className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                            <button 
                                onClick={handleUnlock}
                                className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 shadow-lg shadow-indigo-100"
                            >
                                <Unlock className="w-4 h-4" /> Reveal Leads
                            </button>
                        </div>
                        <p className="text-xs text-slate-400 mt-4">We respect your inbox. No spam.</p>
                      </div>
                      
                      {/* Fake rows behind the blur for visual effect */}
                      <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-30 z-0 pointer-events-none">
                          {[1,2,3].map(n => (
                              <div key={n} className="grid grid-cols-12 py-4 px-4 border-b border-slate-200">
                                  <div className="col-span-2"><div className="w-8 h-8 bg-slate-200 rounded-full"></div></div>
                                  <div className="col-span-4 space-y-2"><div className="h-4 bg-slate-200 w-3/4 rounded"></div><div className="h-3 bg-slate-100 w-1/2 rounded"></div></div>
                                  <div className="col-span-6 space-y-2"><div className="h-3 bg-slate-200 w-full rounded"></div><div className="h-3 bg-slate-100 w-5/6 rounded"></div></div>
                              </div>
                          ))}
                      </div>
                    </div>
                  )}

                </div>
             </div>
          ) : (
            // Input View (Unchanged)
            <div className="p-8 md:p-12 space-y-8">
              {/* Step 1 */}
              <div>
                <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs">1</span>
                  What are you looking for?
                </label>
                <textarea 
                  className="w-full p-4 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all resize-none"
                  rows={2}
                  placeholder="e.g. Find me Investors for my AI startup..."
                  value={idea}
                  onChange={(e) => setIdea(e.target.value)}
                />
              </div>

              {/* Step 2 */}
              <div>
                <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs">2</span>
                  Upload CSVs (LinkedIn Exports)
                </label>
                <div className="relative group">
                  <input 
                    type="file" 
                    accept=".csv"
                    multiple
                    onChange={(e) => setFiles(e.target.files)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                  />
                  <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center hover:bg-indigo-50/50 transition-colors">
                    {files && files.length > 0 ? (
                      <div className="flex flex-col items-center">
                        <Layers className="w-10 h-10 text-indigo-600 mb-2" />
                        <p className="font-bold text-slate-900">{files.length} Files Selected</p>
                        <p className="text-xs text-slate-500 mt-1">Ready to merge & scan</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-slate-400 group-hover:text-indigo-500 transition-colors">
                        <Upload className="w-10 h-10 mb-2" />
                        <p className="font-medium">Upload one or multiple CSVs</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <button 
                onClick={handleAnalyze}
                disabled={!files || !idea || status !== "idle"}
                className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all
                  ${!files || !idea 
                    ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-200'
                  }
                `}
              >
                {status === "analyzing" ? "Processing Data..." : "Analyze Network"} <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </motion.div>
      </section>
    </main>
  );
}