import type { Metadata } from "next";
import "./globals.css";
import { LiveRefresh } from "@/components/live-refresh";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Unified SOC Platform",
  description: "Unified Security Operations Center Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-soc-bg text-soc-text font-sans antialiased">
        <LiveRefresh /><AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
