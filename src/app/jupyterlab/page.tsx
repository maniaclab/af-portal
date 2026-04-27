import { requireMember } from "@/lib/auth/guards";
import Breadcrumb from "@/components/ui/Breadcrumb";
import JupyterLabTable from "@/components/jupyterlab/NotebooksTable";

export const metadata = { title: "Analysis Facility - JupyterLab" };

export default async function JupyterLabPage() {
  await requireMember();
  return (
    <section id="jupyterlab">
      <div className="container">
        <Breadcrumb
          items={[{ label: "Home", href: "/" }, { label: "JupyterLab" }]}
        />
        <a
          href="/jupyterlab/configure"
          className="btn btn-sm btn-primary mb-4"
        >
          Configure notebook
        </a>
        <JupyterLabTable />
      </div>
    </section>
  );
}
