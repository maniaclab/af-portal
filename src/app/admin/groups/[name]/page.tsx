import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/auth/guards";
import { getGroupInfo } from "@/lib/connect/client";
import Breadcrumb from "@/components/ui/Breadcrumb";
import GroupTabs from "@/components/admin/GroupTabs";

export const metadata = { title: "Analysis Facility - Groups" };

export default async function GroupPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  await requireAdmin();
  const group = await getGroupInfo(name);
  if (!group) notFound();

  return (
    <section id="groups">
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Groups", href: "/admin/groups/root.atlas-af" },
            { label: group.name },
          ]}
        />
        <GroupTabs group={group} />
      </div>
    </section>
  );
}
