import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "宏观周期状态雷达",
  description: "指标数据结构 + 规则系统 + Agent解读的宏观周期理解系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
