import type { Metadata } from "next";
import { fraunces, workSans, plexMono } from "@/lib/fonts";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sutura — Know where every dalasi goes",
  description:
    "Sutura turns your salary, allowances, and other income into a clear monthly plan: what's allocated, what's spent, and what's saved.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${workSans.variable} ${plexMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
