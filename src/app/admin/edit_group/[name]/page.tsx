import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/auth/guards";
import { getGroupInfo } from "@/lib/connect/client";
import Breadcrumb from "@/components/ui/Breadcrumb";
import { editGroupAction } from "./actions";

export const metadata = { title: "Analysis Facility - Edit Group" };

export default async function EditGroupPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  await requireAdmin();
  const group = await getGroupInfo(name);
  if (!group) notFound();
  const action = editGroupAction.bind(null, name) as (formData: FormData) => Promise<void>;

  return (
    <section>
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Groups", href: "/admin/groups/root.atlas-af" },
            { label: group.name, href: `/admin/groups/${group.name}` },
            { label: "Edit" },
          ]}
        />
        <div className="row">
          <div className="col-lg-8 mx-auto">
            <h4 className="mt-3">Edit group information</h4>
            <div className="text-success">
              <hr />
            </div>
            <form action={action}>
              <div className="mb-3">
                <label className="form-label">Display name:</label>
                <input
                  type="text"
                  className="form-control"
                  name="display-name"
                  defaultValue={group.display_name}
                  required
                />
              </div>
              <div className="mb-3">
                <label className="form-label">Contact email:</label>
                <input
                  type="text"
                  className="form-control"
                  name="email"
                  defaultValue={group.email}
                  required
                />
              </div>
              <div className="mb-3">
                <label className="form-label">Contact phone number:</label>
                <input
                  type="text"
                  className="form-control"
                  name="phone"
                  defaultValue={group.phone}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="form-label">Description:</label>
                <input
                  type="text"
                  className="form-control"
                  name="description"
                  defaultValue={group.description}
                />
              </div>
              <div className="mb-3">
                <button className="btn btn-primary" type="submit">
                  Submit
                </button>
                <a
                  href={`/admin/groups/${group.name}`}
                  className="btn btn-danger ms-2"
                  role="button"
                >
                  Cancel
                </a>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
