import type { Metadata } from "next";
import localFont from "next/font/local";
import { ThemeProvider } from "@/components/theme-provider";
import { site } from "@/lib/site";
import "./globals.css";
const belepotan = localFont({
  src: "../public/fonts/belepotan-regular.otf",
  weight: "400",
  display: "swap",
  variable: "--font-interface",
});
export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || "http://127.0.0.1:3000"),
  title: {
    default: "Discord Bot — ваш сервер, только ближе",
    template: "%s · Discord Bot",
  },
  description: site.description,
  applicationName: site.name,
  icons: { icon: `${process.env.NEXT_PUBLIC_BASE_PATH || ""}/icon.svg` },
  openGraph: {
    title: "Discord Bot — ваш сервер, только ближе",
    description: site.description,
    locale: "ru_RU",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Discord Bot — ваш сервер, только ближе",
    description: site.description,
  },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={belepotan.variable}>
        <ThemeProvider>
          <a href="#main" className="skip-link">
            К содержимому
          </a>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
