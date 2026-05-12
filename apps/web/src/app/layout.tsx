import type { Metadata } from "next";
import { Inter_Tight, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
  weight: ["200", "300", "400", "500", "600"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["300", "400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "dqt: The data quality tool that tells you what and why",
  description:
    "Statistical drift detection, column-level lineage, and causal discovery for dbt, warehouses, and data lakes. Python library, CLI, and Web app. All MIT licensed.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "dqt: The data quality tool that tells you what and why",
    description:
      "Statistical drift detection, column-level lineage, and causal discovery for dbt, warehouses, and data lakes. Python library, CLI, and Web app. All MIT licensed.",
    url: "https://dqt.dev",
    siteName: "dqt",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "dqt: The data quality tool that tells you what and why",
    description:
      "Statistical drift detection, column-level lineage, and causal discovery. Python library, CLI, and Web app. All MIT licensed.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body
        className={`${interTight.variable} ${jetbrainsMono.variable} font-sans`}
      >
        {children}
      </body>
    </html>
  );
}
