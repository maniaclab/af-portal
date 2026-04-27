"use client";
import { useEffect, useState, useCallback } from "react";
import type { Notebook } from "@/types";

export default function NotebooksTable() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/jupyterlab/get_notebooks");
      const data = await res.json();
      setNotebooks(data.notebooks ?? []);
      const anyNotReady = (data.notebooks ?? []).some(
        (n: Notebook) => n.status !== "Ready"
      );
      if (anyNotReady) {
        setTimeout(load, 10000);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function removeNotebook(id: string) {
    setNotebooks((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, status: "Removing notebook..." } : n
      )
    );
    await fetch(`/jupyterlab/remove/${id}`);
    setTimeout(load, 2000);
  }

  if (loading) {
    return <div className="text-muted">Loading notebooks…</div>;
  }

  return (
    <div className="fs14">
      <table className="table">
        <thead className="text-muted">
          <tr>
            <th>Notebook</th>
            <th>Status</th>
            <th>Creation date</th>
            <th>Expiration date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {notebooks.length === 0 && (
            <tr>
              <td colSpan={5} className="text-center text-muted">
                No notebooks running
              </td>
            </tr>
          )}
          {notebooks.map((n) => (
            <tr key={n.id}>
              <td>
                {n.status === "Ready" && n.url ? (
                  <a
                    href={n.url}
                    className="text-decoration-none"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {n.id}
                  </a>
                ) : (
                  n.id
                )}
              </td>
              <td>
                {n.status === "Removing notebook..." ? (
                  n.status
                ) : (
                  <>
                    <a
                      className="text-decoration-none"
                      data-bs-toggle="collapse"
                      role="button"
                      href={`#${n.id}_status`}
                    >
                      {n.status}
                    </a>
                    <ul
                      className="collapse list-unstyled mb-0"
                      id={`${n.id}_status`}
                    >
                      {n.conditions.map((c, i) => {
                        if (c.type === "PodScheduled" && c.status === "True")
                          return <li key={i}>Pod scheduled.</li>;
                        if (c.type === "PodScheduled" && c.status === "False")
                          return <li key={i}>Scheduling pod...</li>;
                        if (c.type === "Initialized" && c.status === "True")
                          return <li key={i}>Pod initialized.</li>;
                        if (c.type === "Ready" && c.status === "True")
                          return <li key={i}>Pod ready.</li>;
                        if (c.type === "ContainersReady" && c.status === "True")
                          return <li key={i}>Container ready.</li>;
                        return null;
                      })}
                      {n.status === "Starting notebook..." && (
                        <li>Starting Jupyter notebook...</li>
                      )}
                      {n.status === "Ready" && (
                        <li>Jupyter notebook started.</li>
                      )}
                    </ul>
                  </>
                )}
              </td>
              <td>{new Date(n.creation_date).toLocaleString()}</td>
              <td>{new Date(n.expiration_date).toLocaleString()}</td>
              <td>
                {n.status !== "Removing notebook..." ? (
                  <button
                    className="btn btn-link p-0"
                    onClick={() => removeNotebook(n.id)}
                    title="Remove notebook"
                  >
                    <i className="fa-regular fa-trash-can"></i>
                  </button>
                ) : (
                  <i className="fa-regular fa-trash-can text-muted"></i>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
