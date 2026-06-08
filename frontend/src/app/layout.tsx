import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/use-auth";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "FinSight — Smart Audit & Financial Reporting for CA Firms",
  description:
    "Connect to Tally Prime, run 200+ audit rules, map to MCA Schedule III, and generate CA-ready Excel/PDF reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-gray-950 text-gray-100`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
