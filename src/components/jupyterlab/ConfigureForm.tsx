"use client";
import { useState, useEffect } from "react";
import type { GpuAvailability } from "@/types";

interface ConfigureFormProps {
  notebookName: string;
  maxMem: number;
}

export default function ConfigureForm({
  notebookName,
  maxMem,
}: ConfigureFormProps) {
  const [gpuInstances, setGpuInstances] = useState(0);
  const [gpus, setGpus] = useState<GpuAvailability[] | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetch("/hardware/gpus")
      .then((r) => r.json())
      .then((d) => setGpus(d.gpus ?? []));
  }, []);

  return (
    <>
      <div className="card col-sm-6 mx-auto">
        <div className="card-header">Configure a Jupyter notebook</div>
        <div className="card-body">
          <form
            id="configure"
            action="/jupyterlab/deploy"
            method="POST"
            onSubmit={() => setIsSubmitting(true)}
          >
            <div className="row mb-2">
              <div className="col-sm-4">
                <label className="form-label my-2">
                  Notebook name{" "}
                  <a
                    className="text-decoration-none"
                    data-bs-toggle="modal"
                    href="#i_notebook-name"
                    role="button"
                  >
                    <i className="fas fa-info-circle"></i>
                  </a>
                </label>
              </div>
              <div className="col-sm-8">
                <input
                  type="text"
                  className="form-control"
                  name="notebook-name"
                  defaultValue={notebookName}
                  pattern="[a-zA-Z0-9._\-]+"
                  maxLength={30}
                  required
                />
              </div>
            </div>
            <div className="row mb-2">
              <div className="col-sm-4">
                <label className="form-label my-2">CPU cores</label>
              </div>
              <div className="col-sm-8">
                <input
                  type="number"
                  className="form-control"
                  name="cpu"
                  min={1}
                  max={16}
                  defaultValue={1}
                  required
                />
              </div>
            </div>
            <div className="row mb-2">
              <div className="col-sm-4">
                <label className="form-label my-2">Memory (GB)</label>
              </div>
              <div className="col-sm-8">
                <input
                  type="number"
                  className="form-control"
                  name="memory"
                  min={1}
                  max={maxMem}
                  defaultValue={2}
                  required
                />
              </div>
            </div>
            <div className="row mb-2">
              <div className="col-sm-4">
                <label className="form-label my-2">
                  GPU instances{" "}
                  <a
                    className="text-decoration-none"
                    data-bs-toggle="modal"
                    href="#gpu-instances"
                    role="button"
                  >
                    <i className="fas fa-info-circle"></i>
                  </a>
                </label>
              </div>
              <div className="col-sm-8">
                <input
                  type="number"
                  className="form-control"
                  name="gpu"
                  min={0}
                  max={4}
                  value={gpuInstances}
                  onChange={(e) => setGpuInstances(parseInt(e.target.value, 10) || 0)}
                  required
                />
              </div>
            </div>
            {gpuInstances > 0 && (
              <div className="row mb-2">
                <div className="col-sm-4">
                  <label className="form-label my-2">
                    GPU Model{" "}
                    <a
                      className="text-decoration-none"
                      data-bs-toggle="modal"
                      href="#gpu-product"
                      role="button"
                    >
                      <i className="fas fa-info-circle"></i>
                    </a>
                  </label>
                </div>
                <div className="col-sm-8">
                  <select name="gpu-product" className="form-control">
                    <option value="NVIDIA-A100-SXM4-40GB-MIG-1g.5gb">
                      NVIDIA-A100 (MIG instance)
                    </option>
                    <option value="NVIDIA-A100-SXM4-40GB">
                      NVIDIA A100 (Whole)
                    </option>
                    <option value="NVIDIA-H200-NVL-MIG-1g.16gb">
                      NVIDIA H200 (MIG instance)
                    </option>
                    <option value="NVIDIA-GeForce-RTX-2080-Ti">
                      NVIDIA GeForce RTX 2080 Ti
                    </option>
                    <option value="NVIDIA-GeForce-GTX-1080-Ti">
                      NVIDIA GeForce GTX 1080 Ti
                    </option>
                    <option value="Tesla-V100-PCIE-16GB">
                      NVIDIA Tesla V100
                    </option>
                  </select>
                </div>
              </div>
            )}
            {gpuInstances === 0 && (
              <input type="hidden" name="gpu-product" value="" />
            )}
            <div className="row mb-2">
              <div className="col-sm-4">
                <label className="form-label my-2">Duration (hours)</label>
              </div>
              <div className="col-sm-8">
                <input
                  type="number"
                  name="duration"
                  className="form-control"
                  min={1}
                  max={72}
                  defaultValue={8}
                  required
                />
              </div>
            </div>
            <div className="row mb-4">
              <div className="col-sm-4">
                <label className="form-label my-2">
                  Image{" "}
                  <a
                    className="text-decoration-none"
                    href="https://usatlas.github.io/af-docs/uchicago/jupyter/#docker-images"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <i className="fa fa-external-link"></i>
                  </a>
                </label>
              </div>
              <div className="col-sm-8">
                <select name="image" className="form-control">
                  <option value="hub.opensciencegrid.org/usatlas/ml-platform:latest">
                    ml-platform:latest
                  </option>
                  <option value="hub.opensciencegrid.org/usatlas/ml-platform:2026.3">
                    ml-platform:2026.3
                  </option>
                </select>
              </div>
            </div>
            <button
              className="btn btn-sm btn-primary"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Creating…" : "Create notebook"}
            </button>
          </form>
        </div>
      </div>

      {/* Modals */}
      <div id="i_notebook-name" className="modal fade" role="dialog">
        <div className="modal-dialog" style={{ maxWidth: 600 }}>
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">Rules of notebook naming</h5>
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
              />
            </div>
            <div className="modal-body">
              <ol className="ps-3">
                <li>No whitespaces.</li>
                <li>Only characters from the set [a-zA-Z0-9._-]</li>
                <li>Less than 30 characters.</li>
              </ol>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-primary"
                data-bs-dismiss="modal"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>

      <div id="gpu-product" className="modal fade" role="dialog">
        <div className="modal-dialog" style={{ maxWidth: 600 }}>
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">Selecting GPU memory</h5>
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
              />
            </div>
            <div className="modal-body">
              {gpus ? (
                <>
                  <p>Here is a table of our GPUs and their availability.</p>
                  <table className="table table-hover table-bordered">
                    <thead>
                      <tr>
                        <th>GPU</th>
                        <th>Count</th>
                        <th>Avail.</th>
                        <th>Memory (MB)</th>
                        <th>Max CPU Req</th>
                        <th>Max Mem Req (GB)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gpus.map((g) => (
                        <tr key={g.product}>
                          <td>{g.product}</td>
                          <td>{g.count}</td>
                          <td>{g.available}</td>
                          <td>{g.memory}</td>
                          <td>{g.cpu_request_max}</td>
                          <td>{g.mem_request_max}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ) : (
                <div>
                  Loading…{" "}
                  <span
                    className="spinner-border spinner-border-sm text-dark ms-2"
                    role="status"
                  />
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-primary"
                data-bs-dismiss="modal"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>

      <div id="gpu-instances" className="modal fade" role="dialog">
        <div className="modal-dialog" style={{ maxWidth: 600 }}>
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">Selecting GPU instances</h5>
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
              />
            </div>
            <div className="modal-body">
              <p>
                The AF cluster has a variety of GPUs you can choose from. Each
                GPU can be partitioned into instances. You can have many
                instances running in parallel.
              </p>
              <p>
                Please select the number of GPU instances you would like to
                request. You can select any number from 0 to 4.
              </p>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-primary"
                data-bs-dismiss="modal"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
