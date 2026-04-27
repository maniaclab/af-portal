"use client";

import { useState, useEffect, useCallback } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import type { Group, UserProfile } from "@/types";

interface Props {
  group: Group;
}

const memberCol = createColumnHelper<UserProfile>();

function flash(message: string, category: "success" | "warning") {
  const div = document.createElement("div");
  div.className = `alert alert-${category} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
  div.style.zIndex = "9999";
  div.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"/>`;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

function MembersTable({
  groupName,
  type,
  onCountChange,
}: {
  groupName: string;
  type: "members" | "requests" | "potential";
  onCountChange?: (n: number) => void;
}) {
  const [data, setData] = useState<UserProfile[]>([]);
  const [sorting, setSorting] = useState<SortingState>([{ id: "role", desc: true }]);

  const load = useCallback(async () => {
    const url =
      type === "members"
        ? `/admin/get_members/${groupName}`
        : type === "requests"
        ? `/admin/get_member_requests/${groupName}`
        : `/admin/get_potential_members/${groupName}`;
    const r = await fetch(url);
    const j = await r.json();
    const list: UserProfile[] =
      type === "members" ? j.members : type === "requests" ? j.member_requests : j.potential_members;
    setData(list ?? []);
    onCountChange?.(list?.length ?? 0);
  }, [groupName, type, onCountChange]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (action: string, user: string) => {
    const url =
      action === "remove"
        ? `/admin/remove_group_member/${groupName}/${user}`
        : action === "approve"
        ? `/admin/approve_membership_request/${groupName}/${user}`
        : action === "deny"
        ? `/admin/deny_membership_request/${groupName}/${user}`
        : `/admin/add_group_member/${groupName}/${user}`;
    await fetch(url);
    await load();
    flash(
      action === "remove"
        ? `Removed ${user} from ${groupName}`
        : action === "approve"
        ? `Approved ${user} for ${groupName}`
        : action === "deny"
        ? `Denied ${user} from ${groupName}`
        : `Added ${user} to ${groupName}`,
      "success"
    );
  };

  const actionCol =
    type === "members"
      ? memberCol.display({
          id: "action",
          header: "Action",
          cell: ({ row }) => (
            <button
              className="badge bg-danger border-0"
              onClick={() => handleAction("remove", row.original.unix_name)}
            >
              <i className="fa-solid fa-circle-xmark" /> Remove
            </button>
          ),
        })
      : type === "requests"
      ? memberCol.display({
          id: "action",
          header: "Action",
          cell: ({ row }) => (
            <>
              <button
                className="badge bg-success border-0 me-1"
                onClick={() => handleAction("approve", row.original.unix_name)}
              >
                <i className="fa-regular fa-circle-check" /> Approve
              </button>
              <button
                className="badge bg-danger border-0"
                onClick={() => handleAction("deny", row.original.unix_name)}
              >
                <i className="fa-regular fa-circle-xmark" /> Deny
              </button>
            </>
          ),
        })
      : memberCol.display({
          id: "action",
          header: "Action",
          cell: ({ row }) => (
            <button
              className="badge bg-primary border-0"
              onClick={() => handleAction("add", row.original.unix_name)}
            >
              <i className="fa-solid fa-circle-plus" /> Add
            </button>
          ),
        });

  const roleCol = memberCol.accessor("role", {
    header: "Status",
    cell: ({ getValue }) => {
      const v = getValue();
      const cls = v === "admin" ? "text-primary" : v === "active" ? "text-success" : v === "pending" ? "text-warning" : "";
      return <span className={cls}>{v}</span>;
    },
  });

  const columns = [
    memberCol.accessor("unix_name", { header: "Username" }),
    memberCol.accessor("name", { header: "Name" }),
    memberCol.accessor("email", { header: "Email" }),
    memberCol.accessor("phone", { header: "Phone" }),
    memberCol.accessor("institution", { header: "Institution" }),
    roleCol,
    actionCol,
  ];

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <table className="table table-sm table-hover">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((h) => (
              <th
                key={h.id}
                style={{ cursor: h.column.getCanSort() ? "pointer" : undefined }}
                onClick={h.column.getToggleSortingHandler()}
              >
                {flexRender(h.column.columnDef.header, h.getContext())}
                {h.column.getIsSorted() === "asc" ? " ▲" : h.column.getIsSorted() === "desc" ? " ▼" : null}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

interface SubgroupRow {
  name: string;
  email: string;
  phone: string;
  description: string;
}

function SubgroupsTable({ groupName }: { groupName: string }) {
  const [data, setData] = useState<SubgroupRow[]>([]);
  const col = createColumnHelper<SubgroupRow>();

  useEffect(() => {
    fetch(`/admin/get_subgroups/${groupName}`)
      .then((r) => r.json())
      .then((j) => setData(j.subgroups ?? []));
  }, [groupName]);

  const columns = [
    col.accessor("name", {
      header: "Name",
      cell: ({ getValue }) => (
        <a href={`/admin/groups/${getValue()}`} className="text-decoration-none">
          {getValue()}
        </a>
      ),
    }),
    col.accessor("email", { header: "Contact email" }),
    col.accessor("phone", { header: "Phone" }),
    col.accessor("description", { header: "Description" }),
  ];

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <table className="table table-sm table-hover">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((h) => (
              <th key={h.id}>{flexRender(h.column.columnDef.header, h.getContext())}</th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EmailForm({ groupName }: { groupName: string }) {
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const r = await fetch(`/admin/email/${groupName}`, { method: "POST", body: form });
    const j = await r.json();
    setStatus(j.message);
    if (j.success) (e.target as HTMLFormElement).reset();
  };

  return (
    <form onSubmit={handleSubmit}>
      {status && <div className="alert alert-info">{status}</div>}
      <div className="mb-3">
        <h6>Send an email to the {groupName} users</h6>
      </div>
      <div className="form-floating mb-3">
        <input type="text" className="form-control" name="subject" id="subject" placeholder="Subject" required />
        <label htmlFor="subject">Subject</label>
      </div>
      <div className="form-floating mb-3">
        <textarea className="form-control" placeholder="Body" name="body" id="body" style={{ height: 300 }} required />
        <label htmlFor="body">Body</label>
      </div>
      <button type="submit" className="btn btn-primary">Submit</button>
    </form>
  );
}

export default function GroupTabs({ group }: Props) {
  const [requestCount, setRequestCount] = useState(0);

  return (
    <>
      <ul className="nav nav-tabs my-4" role="tablist">
        {[
          { id: "overview", label: "Overview", icon: "fa-cubes" },
          { id: "members", label: "Members", icon: "fa-user-group" },
          { id: "member_requests", label: "Member Requests", icon: "fa-user-group", badge: requestCount },
          { id: "subgroups", label: "Subgroups", icon: "fa-diagram-project" },
          { id: "add_members", label: "Add Members", icon: "fa-user-plus" },
          { id: "email", label: "Email", icon: "fa-envelope" },
        ].map((tab, i) => (
          <li key={tab.id} className="nav-item" role="presentation">
            <button
              className={`nav-link${i === 0 ? " active" : ""}`}
              data-bs-toggle="tab"
              data-bs-target={`#${tab.id}`}
              type="button"
              role="tab"
            >
              <i className={`fa-solid ${tab.icon}`} />&nbsp;{tab.label}
              {tab.badge != null && tab.badge > 0 && (
                <span className="badge rounded-pill bg-warning ms-1">{tab.badge}</span>
              )}
            </button>
          </li>
        ))}
      </ul>

      <div className="tab-content">
        <div className="tab-pane fade show active" id="overview" role="tabpanel">
          <div className="card col-sm-6">
            <div className="card-header">{group.display_name}</div>
            <div className="card-body">
              <ul className="list-unstyled">
                <li><span className="text-muted">Unix name:</span> {group.name}</li>
                <li><span className="text-muted">Description:</span> {group.description}</li>
                <li><span className="text-muted">Purpose:</span> {group.purpose}</li>
                <li>
                  <span className="text-muted">Contact email:</span>{" "}
                  <a className="text-decoration-none" href={`mailto:${group.email}`}>{group.email}</a>
                </li>
                <li><span className="text-muted">Phone number:</span> {group.phone}</li>
                <li><span className="text-muted">Created on:</span> {group.creation_date}</li>
              </ul>
            </div>
            <div className="card-footer bg-transparent border-top-0">
              <a href={`/admin/edit_group/${group.name}`} className="btn btn-sm btn-primary">Edit group</a>
              <a href={`/admin/create_subgroup/${group.name}`} className="btn btn-sm btn-primary ms-2">Create subgroup</a>
              {group.is_removable && (
                <a href={`/admin/remove_group/${group.name}`} className="btn btn-sm btn-danger ms-2">Delete group</a>
              )}
            </div>
          </div>
        </div>

        <div className="tab-pane fade fs-6" id="members" role="tabpanel">
          <MembersTable groupName={group.name} type="members" />
        </div>

        <div className="tab-pane fade fs-6" id="member_requests" role="tabpanel">
          <MembersTable groupName={group.name} type="requests" onCountChange={setRequestCount} />
        </div>

        <div className="tab-pane fade fs-6" id="subgroups" role="tabpanel">
          <SubgroupsTable groupName={group.name} />
        </div>

        <div className="tab-pane fade fs-6" id="add_members" role="tabpanel">
          <MembersTable groupName={group.name} type="potential" />
        </div>

        <div className="tab-pane fade col-lg-8 mx-auto" id="email" role="tabpanel">
          <EmailForm groupName={group.name} />
        </div>
      </div>
    </>
  );
}
