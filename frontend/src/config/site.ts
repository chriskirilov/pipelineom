export const siteConfig = {
  name: "PipelineOM",
  description: "Turn your LinkedIn network into revenue.",
  
  hero: {
    title: "Uncover Hidden Revenue in",
    highlight: "LinkedIn Network",
    subtitle: "Upload your Connections CSV — our AI finds the exact leads you need in seconds.",
  },

  // This allows you to point to localhost now, and your live URL later
  api: {
    url: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
  }
}