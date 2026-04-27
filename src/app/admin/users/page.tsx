import { requireAdmin } from "@/lib/auth/guards";
import Breadcrumb from "@/components/ui/Breadcrumb";
import UsersSpreadsheet from "@/components/admin/UsersSpreadsheet";

export const metadata = { title: "Analysis Facility - Users" };

export default async function UsersPage() {
  await requireAdmin();

  return (
    <section id="users">
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Users" },
          ]}
        />
        <p>
          Below is a table of AF users. Click{" "}
          <a
            className="text-decoration-none"
            href="/admin/plot_users_over_time"
            target="_blank"
          >
            here
          </a>{" "}
          to see a graph of user registrations.
        </p>
        <UsersSpreadsheet />
      </div>
    </section>
  );
}
