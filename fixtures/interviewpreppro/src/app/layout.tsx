import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import "./globals.css";
import PerformanceMonitor from "@/components/utils/PerformanceMonitor";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: 'swap',
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: 'swap',
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    template: '',
    default: 'Fleet-Drive - Truck Company Management',
  },
  description: "Streamline your truck fleet operations with comprehensive file management, compliance tracking, and operational tools.",
  keywords: ["fleet management", "truck management", "file management", "compliance", "fleet operations"],
  authors: [{ name: "Fleet-Drive Team" }],
  openGraph: {
    title: 'Fleet-Drive - Truck Company Management',
    description: 'Streamline your truck fleet operations with comprehensive file management',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="prevent-overscroll">
      <body className={`${geistSans.variable} ${geistMono.variable} ${inter.variable} prevent-overscroll hw-accelerated`}>
        <PerformanceMonitor />
        <div className="scrollable-content min-h-screen hw-accelerated">
          {children}
        </div>
      </body>
    </html>
  );
}
