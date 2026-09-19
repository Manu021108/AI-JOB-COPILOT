import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "AI Job Copilot", description: "Your AI-powered job application workspace." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
