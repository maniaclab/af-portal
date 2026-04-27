"use client";
import { useActionState } from "react";
import { createProfileAction } from "./actions";
import SshKeyInstructions from "@/components/profile/SshKeyInstructions";

export default function CreateProfilePage() {
  const [error, formAction, isPending] = useActionState(createProfileAction, null);

  return (
    <section>
      <div className="container">
        {error && (
          <div className="alert alert-warning alert-dismissible">
            {error}
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="alert"
            />
          </div>
        )}
        <div className="row">
          <div className="col-lg-6">
            <form action={formAction}>
              <div className="mb-2">
                <label className="form-label">
                  Name <span className="asterisk">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  name="name"
                  maxLength={256}
                  required
                />
              </div>
              <div className="mb-2">
                <label className="form-label">
                  Unix name <span className="asterisk">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  name="unix_name"
                  id="unix_name"
                  maxLength={256}
                  required
                  pattern="[a-zA-Z0-9._\-]+"
                  title="Only letters, numbers, underscores, dots and dashes"
                />
              </div>
              <div className="mb-2">
                <label className="form-label">
                  Institution <span className="asterisk">*</span> (Your home
                  institution rather than CERN, unless CERN is your institution)
                </label>
                <input
                  type="text"
                  className="form-control"
                  name="institution"
                  maxLength={256}
                  required
                />
              </div>
              <div className="mb-2">
                <label className="form-label">
                  Email <span className="asterisk">*</span> (please use
                  institutional email)
                </label>
                <input
                  type="email"
                  className="form-control"
                  name="email"
                  maxLength={256}
                  required
                />
              </div>
              <div className="mb-2">
                <label className="form-label">
                  Phone <span className="asterisk">*</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  name="phone"
                  maxLength={256}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="form-label">SSH public key</label>
                <textarea
                  className="form-control"
                  name="public_key"
                  rows={5}
                  maxLength={65536}
                />
              </div>
              <div className="mb-2">
                <button
                  className="btn btn-sm btn-primary"
                  type="submit"
                  disabled={isPending}
                >
                  {isPending ? "Creating…" : "Create profile"}
                </button>
              </div>
            </form>
          </div>
          <div className="col-lg-1"></div>
          <div className="col-lg-5">
            <SshKeyInstructions />
          </div>
        </div>
      </div>
    </section>
  );
}
