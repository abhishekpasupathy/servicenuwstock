import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { LiveTickerBar } from "@/components/layout/LiveTickerBar";
import { TopBar } from "@/components/layout/TopBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "DadStock Bloomberg Terminal",
  description: "Institutional-style market analytics terminal",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="min-h-screen bg-[var(--bg-primary)]">
          <Sidebar />
          <main className="min-h-screen md:ml-[232px]">
            <LiveTickerBar />
            <TopBar />
            <div className="p-2 md:p-3">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
