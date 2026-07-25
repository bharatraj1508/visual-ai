import type { Metadata } from "next";

import "react-toastify/dist/ReactToastify.css";
import "./globals.css";

import AppProviders from "@/providers";

export const metadata: Metadata = {
  title: "Visual AI — Data Analyst",
  description: "Upload a CSV and explore it with charts and reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
