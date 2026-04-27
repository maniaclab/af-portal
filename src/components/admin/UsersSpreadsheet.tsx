"use client";

import { useState, useEffect, useCallback } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";

interface UserRow {
  unix_name: string;
  name: string;
  email: string;
  join_date: string;
  institution: string;
}

const col = createColumnHelper<UserRow>();

const columns = [
  col.accessor("unix_name", { header: "Username" }),
  col.accessor("name", { header: "Name" }),
  col.accessor("email", { header: "Email" }),
  col.accessor("join_date", { header: "Join date" }),
  col.accessor("institution", {
    header: "Institution",
    cell: ({ row, getValue }) => (
      <EditableCell
        value={getValue()}
        onSave={(val) => saveInstitution(row.original.unix_name, val)}
      />
    ),
  }),
];

function EditableCell({
  value: initial,
  onSave,
}: {
  value: string;
  onSave: (v: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(initial);

  if (!editing) {
    return (
      <span
        style={{ cursor: "pointer" }}
        title="Click to edit"
        onClick={() => setEditing(true)}
      >
        {value || <em className="text-muted">—</em>}
      </span>
    );
  }
  return (
    <input
      autoFocus
      className="form-control form-control-sm"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={() => {
        setEditing(false);
        onSave(value);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          setEditing(false);
          onSave(value);
        } else if (e.key === "Escape") {
          setEditing(false);
          setValue(initial);
        }
      }}
    />
  );
}

function saveInstitution(unix_name: string, institution: string) {
  const form = new FormData();
  form.set("username", unix_name);
  form.set("institution", institution);
  fetch("/admin/update_user_institution", { method: "POST", body: form });
}

export default function UsersSpreadsheet() {
  const [data, setData] = useState<UserRow[]>([]);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  useEffect(() => {
    fetch("/admin/get_user_spreadsheet")
      .then((r) => r.json())
      .then(setData);
  }, []);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div>
      <div className="mb-2 d-flex justify-content-between align-items-center">
        <input
          className="form-control"
          style={{ maxWidth: 300 }}
          placeholder="Search…"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() => {
            const csv = [
              ["Username", "Name", "Email", "Join date", "Institution"],
              ...data.map((u) => [u.unix_name, u.name, u.email, u.join_date, u.institution]),
            ]
              .map((r) => r.map((c) => `"${(c ?? "").replace(/"/g, '""')}"`).join(","))
              .join("\n");
            const a = document.createElement("a");
            a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
            a.download = "users.csv";
            a.click();
          }}
        >
          Export CSV
        </button>
      </div>
      <table className="table table-bordered table-hover table-sm">
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
                  {h.column.getIsSorted() === "asc"
                    ? " ▲"
                    : h.column.getIsSorted() === "desc"
                    ? " ▼"
                    : null}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
