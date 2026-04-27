"use client";

import { useState, useCallback } from "react";
import type { Notebook } from "@/types";

function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function AdminNotebooksPanel() {
  const [list, setList] = useState<string[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [loading, setLoading] = useState(false);

  const loadList = useCallback(async () => {
    const r = await fetch("/admin/list_notebooks");
    const j = await r.json();
    setList(j.notebooks ?? []);
  }, []);

  const loadNotebook = useCallback(async (name: string) => {
    setLoading(true);
    const r = await fetch(`/admin/get_notebook/${encodeURIComponent(name)}`);
    const j = await r.json();
    setNotebook(j.notebook ?? null);
    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const r = await fetch("/admin/list_notebooks");
    const j = await r.json();
    const names: string[] = j.notebooks ?? [];
    setList(names);
    if (selected && names.includes(selected)) {
      await loadNotebook(selected);
    }
    setLoading(false);
  }, [selected, loadNotebook]);

  if (!list) {
    return (
      <button className="btn btn-sm btn-outline-primary mt-3" onClick={loadList}>
        Load notebooks
      </button>
    );
  }

  return (
    <>
      <form className="mt-3 mb-4">
        <label htmlFor="select-notebook" className="form-label d-inline-block">
          Choose a notebook:
        </label>
        <select
          id="select-notebook"
          className="form-select d-inline-block ms-3"
          style={{ maxWidth: 250 }}
          value={selected ?? ""}
          onChange={(e) => {
            setSelected(e.target.value);
            if (e.target.value) loadNotebook(e.target.value);
          }}
        >
          <option value="">— select —</option>
          {list.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-link ms-3"
          onClick={refresh}
          disabled={loading}
        >
          <i className="fa-solid fa-arrows-rotate" />
        </button>
      </form>

      {notebook && (
        <div>
          <ul className="nav nav-tabs mb-4" role="tablist">
            {["notebook", "pod", "resources", "events", "log"].map((tab, i) => (
              <li key={tab} className="nav-item" role="presentation">
                <button
                  className={`nav-link${i === 0 ? " active" : ""}`}
                  data-bs-toggle="tab"
                  data-bs-target={`#${tab}-tab-pane`}
                  type="button"
                  role="tab"
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              </li>
            ))}
          </ul>

          <div className="tab-content">
            <div className="tab-pane fade show active" id="notebook-tab-pane" role="tabpanel" tabIndex={0}>
              <div className="card">
                <div className="card-header">Notebook</div>
                <div className="card-body">
                  <ul className="list-unstyled">
                    <li><span className="text-muted">Notebook:</span> {notebook.name}</li>
                    <li><span className="text-muted">Namespace:</span> {notebook.namespace}</li>
                    <li><span className="text-muted">Owner:</span> {notebook.owner}</li>
                    <li><span className="text-muted">Status:</span> {notebook.status}</li>
                    <li><span className="text-muted">Created:</span> {formatDate(notebook.creation_date)}</li>
                    <li><span className="text-muted">Expires:</span> {formatDate(notebook.expiration_date)}</li>
                    <li><span className="text-muted">Image:</span> {notebook.image}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="tab-pane fade" id="pod-tab-pane" role="tabpanel" tabIndex={0}>
              <div className="card">
                <div className="card-header">Pod</div>
                <div className="card-body">
                  <ul className="list-unstyled">
                    <li><span className="text-muted">Pod:</span> {notebook.id}</li>
                    <li><span className="text-muted">Status:</span> {notebook.pod_status}</li>
                    {notebook.node && <li><span className="text-muted">Node:</span> {notebook.node}</li>}
                  </ul>
                  <div className="mb-3">
                    <span className="text-primary">Conditions</span>
                    <table>
                      <tbody>
                        {notebook.conditions.map((c, i) => (
                          <tr key={i}>
                            <td><span className="text-muted">{c.type}:</span> {c.status}</td>
                            <td><span className="text-muted ms-5">{formatDate(c.timestamp)}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {notebook.node_selector && (
                    <div>
                      <span className="text-primary">Node selector</span>
                      <ul className="list-unstyled">
                        {Object.entries(notebook.node_selector).map(([k, v]) => (
                          <li key={k}><span className="text-muted">{k}:</span> {v}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="tab-pane fade" id="resources-tab-pane" role="tabpanel" tabIndex={0}>
              <div className="card">
                <div className="card-header">Resources</div>
                <div className="card-body">
                  <div>
                    <span className="text-primary">Requests</span>
                    <ul className="list-unstyled">
                      <li><span className="text-muted">Memory:</span> {notebook.requests.memory}</li>
                      <li><span className="text-muted">CPU:</span> {notebook.requests.cpu}</li>
                      <li><span className="text-muted">GPU:</span> {notebook.requests["nvidia.com/gpu"] ?? "0"}</li>
                    </ul>
                  </div>
                  <div>
                    <span className="text-primary">Limits</span>
                    <ul className="list-unstyled">
                      <li><span className="text-muted">Memory:</span> {notebook.limits.memory}</li>
                      <li><span className="text-muted">CPU:</span> {notebook.limits.cpu}</li>
                      <li><span className="text-muted">GPU:</span> {notebook.limits["nvidia.com/gpu"] ?? "0"}</li>
                    </ul>
                  </div>
                  {notebook.gpu && (
                    <div>
                      <span className="text-primary">GPU</span>
                      <ul className="list-unstyled">
                        <li><span className="text-muted">Product:</span> {notebook.gpu.product}</li>
                        <li><span className="text-muted">Memory:</span> {notebook.gpu.memory}</li>
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="tab-pane fade" id="events-tab-pane" role="tabpanel" tabIndex={0}>
              <div className="card">
                <div className="card-header">Events</div>
                <div className="card-body">
                  {notebook.events.length > 0 ? (
                    <ul className="list-unstyled">
                      {notebook.events.map((ev, i) => (
                        <li key={i}>
                          {ev.message}
                          <span className="text-muted float-end">{formatDate(ev.timestamp)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>There are no events for this pod.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="tab-pane fade" id="log-tab-pane" role="tabpanel" tabIndex={0}>
              <div className="card">
                <div className="card-header">Log</div>
                <div className="card-body">
                  {notebook.log ? (
                    <div className="form-floating">
                      <textarea className="form-control" rows={16} readOnly defaultValue={notebook.log} style={{ height: "auto" }} />
                    </div>
                  ) : (
                    <p>The pod does not have a log.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
