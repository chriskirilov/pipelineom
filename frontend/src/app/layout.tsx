import type { Metadata } from "next";
import { EB_Garamond, DM_Sans } from "next/font/google";
import "./globals.css";

const ebGaramond = EB_Garamond({
  variable: "--font-heading",
  subsets: ["latin"],
});

const dmSans = DM_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: 'OM | Cursor for GTM',
  description: 'The AI-native workspace to build, test, and deploy go-to-market campaigns at the speed of thought.',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/icon.png', type: 'image/png', sizes: '32x32' },
    ],
    apple: '/icon.png',
  },
  openGraph: {
    title: 'OM | Cursor for GTM',
    description: 'Score your network and uncover high-value targets instantly with our AI routing engine.',
    url: 'https://pipelineom.com',
    siteName: 'OM',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'OM | Cursor for GTM',
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
        className={`${ebGaramond.variable} ${dmSans.variable} font-sans antialiased`}
        style={{ zoom: 0.82 }}
      >
        {children}
      </body>
    </html>
  );
}
