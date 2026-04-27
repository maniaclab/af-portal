import { requireAdmin } from "@/lib/auth/guards";
import { getUserProfiles } from "@/lib/connect/client";
import Breadcrumb from "@/components/ui/Breadcrumb";
import UsersOverTimeChart from "@/components/admin/UsersOverTimeChart";

export const metadata = { title: "Analysis Facility - Users Over Time" };

export default async function PlotUsersOverTimePage() {
  await requireAdmin();
  const users = await getUserProfiles("root.atlas-af");

  const dateMin = new Date(2021, 6, 1);
  const dateMax = new Date();

  const months: { date: string; count: number }[] = [];
  const cursor = new Date(dateMin);
  while (cursor <= dateMax) {
    const year = cursor.getFullYear();
    const month = cursor.getMonth() + 1;
    const count = users.filter((u) => {
      if (!u.join_date) return false;
      const d = new Date(u.join_date);
      return (
        d.getFullYear() < year ||
        (d.getFullYear() === year && d.getMonth() + 1 <= month)
      );
    }).length;
    months.push({
      date: `${year}-${String(month).padStart(2, "0")}`,
      count,
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  return (
    <section>
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Users", href: "/admin/users" },
            { label: "Plot of users over time" },
          ]}
        />
        <UsersOverTimeChart data={months} />
      </div>
    </section>
  );
}
