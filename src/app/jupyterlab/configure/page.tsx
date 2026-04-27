import { redirect } from "next/navigation";
import { requireMember } from "@/lib/auth/guards";
import {
  generateNotebookName,
  getUserRoles,
} from "@/lib/kubernetes/configure-helpers";
import Breadcrumb from "@/components/ui/Breadcrumb";
import ConfigureForm from "@/components/jupyterlab/ConfigureForm";

export const metadata = { title: "Analysis Facility - Configure Notebook" };

export default async function ConfigurePage() {
  const { session } = await requireMember();
  if (!session.unix_name) redirect("/profile/create");

  const notebookName = await generateNotebookName(session.unix_name);
  const roles = await getUserRoles(session.unix_name);
  const maxMem = roles["root.atlas-af.bigmem"] ? 256 : 32;

  return (
    <section id="jupyterlab-form">
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "JupyterLab", href: "/jupyterlab" },
            { label: "Configure" },
          ]}
        />
        <ConfigureForm notebookName={notebookName ?? ""} maxMem={maxMem} />
      </div>
    </section>
  );
}
