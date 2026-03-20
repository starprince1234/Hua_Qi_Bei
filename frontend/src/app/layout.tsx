import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "油价风险智能预测系统",
  description: "Oil Risk Intelligence Orchestrator - 基于多因子模型的油价风险预测平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
