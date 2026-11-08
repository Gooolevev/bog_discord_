import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard-shell";
import { getSession } from "@/lib/auth";
export const metadata: Metadata = {
  title: "Панель управления",
  robots: { index: false, follow: false },
};
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  return <DashboardShell name={session?.user.name}>{children}</DashboardShell>;
}
