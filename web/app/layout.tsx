import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// One typeface for the whole console — Inter, tuned for on-screen readability.
const inter = Inter({
  variable: "--font-ui",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "BeatIT — Cardiac Twin",
  description:
    "Auditable cardiac evidence, deterministic physiology, and bounded simulation. Educational and research use only.",
  applicationName: "BeatIT",
  keywords: [
    "BeatIT",
    "cardiac twin",
    "deterministic physiology",
    "bounded simulation",
    "cardiac simulation",
    "provenance",
  ],
};

export const viewport: Viewport = {
  themeColor: "#f5f6f8",
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        {children}
      </body>
    </html>
  );
}
