import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: 'PipelineOM | Cursor for GTM',
  description: 'The AI-native workspace to build, test, and deploy go-to-market campaigns at the speed of thought.',
  openGraph: {
    title: 'PipelineOM | Cursor for GTM',
    description: 'Score your network and uncover high-value targets instantly with our AI routing engine.',
    url: 'https://pipelineom.com',
    siteName: 'PipelineOM',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'PipelineOM | Cursor for GTM',
    description: 'The AI-native workspace to build, test, and deploy go-to-market campaigns at the speed of thought.',
  }
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        style={{ zoom: 0.82 }}
      >
        {children}
      </body>
    </html>
  );
}
