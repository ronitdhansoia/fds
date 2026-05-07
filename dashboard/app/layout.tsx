import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://migrantmoney.vercel.app"),
  title: {
    default: "MigrantMoney: the hidden tax on global remittances",
    template: "%s · MigrantMoney",
  },
  description:
    "A True Cost Index for cross-border remittances and a corridor-level " +
    "estimate of the savings from stablecoin rails. Built on the World Bank " +
    "Remittance Prices Worldwide panel.",
  openGraph: {
    title: "MigrantMoney: the hidden tax on global remittances",
    description:
      "Migrants pay tens of billions a year in fees to move their own " +
      "money. We measure how much, where, and what stablecoins would save.",
    type: "website",
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "MigrantMoney",
    description:
      "A True Cost Index for cross-border remittances. " +
      "World Bank RPW panel × KNOMAD bilateral volumes × stablecoin counterfactual.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="bg-bg text-text antialiased min-h-screen">
        {}
        <div className="grain pointer-events-none fixed inset-0 z-[1]" aria-hidden />
        <div className="relative z-[2]">{children}</div>
      </body>
    </html>
  );
}
