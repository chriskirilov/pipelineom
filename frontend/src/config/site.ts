export const siteConfig = {
  name: "OM",
  description: "Turn your LinkedIn network into revenue.",
  
  hero: {
    headline: "Your network has signal. You just can't see it yet.",
    subtitle: "Upload any CSV with leads (LinkedIn, CRM export, spreadsheet) — we surface the right people for your goal in under a minute.",
  },

  // Set NEXT_PUBLIC_API_URL to http://127.0.0.1:8000 for local backend; omit for production (Railway)
  api: {
    url: process.env.NEXT_PUBLIC_API_URL || "https://pipelineom-production.up.railway.app"
  }
}