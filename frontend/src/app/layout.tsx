import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "StockSoup",
  description: "Value Investing + Technical Trading Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100">
        <Providers>
          <Nav />
          <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
