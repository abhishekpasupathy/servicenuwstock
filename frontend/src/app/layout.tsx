import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DadStock",
  description: "A personal stock dashboard for simple market tracking.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
