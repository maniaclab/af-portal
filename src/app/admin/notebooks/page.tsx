import { requireAdmin } from "@/lib/auth/guards";
import Breadcrumb from "@/components/ui/Breadcrumb";
import AdminNotebooksPanel from "@/components/admin/AdminNotebooksPanel";

export const metadata = { title: "Analysis Facility - Admin Notebooks" };

export default async function AdminNotebooksPage() {
  await requireAdmin();

  return (
    <section id="notebooks">
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Notebooks" },
          ]}
        />
        <AdminNotebooksPanel />
      </div>
    </section>
  );
}
