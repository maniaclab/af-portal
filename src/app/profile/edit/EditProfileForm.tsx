"use client";
import { useActionState } from "react";
import { editProfileAction } from "./actions";
import type { UserProfile } from "@/types";
import SshKeyInstructions from "@/components/profile/SshKeyInstructions";

export default function EditProfileForm({ profile }: { profile: UserProfile }) {
  const [error, formAction, isPending] = useActionState(editProfileAction, null);

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
                  defaultValue={profile.name}
                  maxLength={256}
                  required
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
                  defaultValue={profile.institution}
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
                  defaultValue={profile.email}
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
                  defaultValue={profile.phone}
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
                  defaultValue={profile.public_key}
                />
              </div>
              <div className="form-check mb-2">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="totpsecret"
                  name="totpsecret"
                />
                <label className="form-check-label" htmlFor="totpsecret">
                  Set up Multi-Factor Authentication
                </label>
                <small className="form-text text-muted d-block">
                  {profile.totp_secret
                    ? "This will delete your current MFA secret and generate a new one"
                    : "Enabling MFA will add an additional layer of security for SSH connections"}
                </small>
              </div>
              <div className="mb-2">
                <button
                  className="btn btn-sm btn-primary me-2"
                  type="submit"
                  disabled={isPending}
                >
                  {isPending ? "Updating…" : "Update profile"}
                </button>
                <a href="/profile" className="btn btn-sm btn-danger">
                  Cancel
                </a>
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
