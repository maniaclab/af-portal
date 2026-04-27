import { requireLogin } from "@/lib/auth/guards";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata = { title: "Analysis Facility - My Groups" };

export default async function UserGroupsPage() {
  await requireLogin();
  return (
    <section>
      <div className="container">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Profile", href: "/profile" },
            { label: "My Groups" },
          ]}
        />
        <h5>My Groups</h5>
        <table
          id="groups-table"
          className="table table-striped nowrap"
          style={{ width: "100%" }}
        >
          <thead>
            <tr>
              <th>Group name</th>
              <th>Unix name</th>
              <th>Member status</th>
              <th>Description</th>
            </tr>
          </thead>
        </table>
      </div>
      <script
        dangerouslySetInnerHTML={{
          __html: `
            $(document).ready(function() {
              $.ajax({
                url: '/profile/get_user_groups',
                success: function(data) {
                  var rows = data.groups.map(function(g) {
                    var roleClass = g.role === 'admin' ? 'text-primary' : g.role === 'active' ? 'text-success' : g.role === 'pending' ? 'text-warning' : 'text-secondary';
                    return [g.name, g.name, '<span class="' + roleClass + '">' + g.role + '</span>', g.description || ''];
                  });
                  var table = $('#groups-table').DataTable({
                    data: rows,
                    columns: [{title:'Group name'},{title:'Unix name'},{title:'Member status'},{title:'Description'}],
                    pageLength: 25,
                    lengthMenu: [25,50,100],
                    order: [[1,'asc']],
                    columnDefs: [{targets: 2, orderable: false}]
                  });
                }
              });
            });
          `,
        }}
      />
      <link
        rel="stylesheet"
        href="https://cdn.datatables.net/2.1.8/css/dataTables.dataTables.min.css"
      />
      <script
        src="https://cdn.datatables.net/2.1.8/js/dataTables.min.js"
        defer
      />
    </section>
  );
}
