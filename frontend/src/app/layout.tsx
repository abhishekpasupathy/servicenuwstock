import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "NOW Terminal",
  description: "Free ServiceNow stock decision support terminal",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="min-h-screen bg-[var(--bg-primary)]">
          <Sidebar />
          <main className="ml-[220px] min-h-screen">
            <TopBar />
            <div className="p-4">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
