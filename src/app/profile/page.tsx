import { redirect } from "next/navigation";
import { requireLogin } from "@/lib/auth/guards";
import { getConnectUserProfile } from "@/lib/connect/client";
import { generateQRCodeDataURL } from "@/lib/utils/qrcode";
import Breadcrumb from "@/components/ui/Breadcrumb";
import type { UserRole } from "@/types";

export const metadata = { title: "Analysis Facility - Profile" };

function RoleBadge({ role }: { role: UserRole }) {
  const cls =
    role === "admin"
      ? "text-primary"
      : role === "active"
        ? "text-success"
        : role === "pending"
          ? "text-warning"
          : "text-secondary";
  return <span className={cls}>{role}</span>;
}

export default async function ProfilePage() {
  const session = await requireLogin();
  if (!session.unix_name) redirect("/profile/create");

  const profile = await getConnectUserProfile(session.unix_name);
  if (!profile) redirect("/profile/create");

  let qrCodeDataUrl: string | null = null;
  if (profile.totp_secret) {
    const authenticatorString =
      `otpauth://totp/${profile.unix_name}?secret=${profile.totp_secret}&issuer=CI Connect`;
    try {
      qrCodeDataUrl = await generateQRCodeDataURL(authenticatorString);
    } catch {
      // non-critical
    }
  }

  const atlasGroups = profile.group_memberships.filter(
    (g) => g.name === "root.atlas-af" || g.name.startsWith("root.atlas-af.")
  );

  return (
    <section>
      <div className="container">
        <Breadcrumb
          items={[{ label: "Home", href: "/" }, { label: "Profile" }]}
        />
        <div className="row">
          <div className="col-sm-6">
            <div className="card h-100">
              <div className="card-header">
                <b>User information</b>
                <i className="fa-solid fa-user-pen float-end"></i>
              </div>
              <div className="card-body">
                <ul className="list-unstyled">
                  <li>
                    <span className="text-muted">Username:</span>{" "}
                    {profile.unix_name}
                  </li>
                  <li>
                    <span className="text-muted">Globus ID:</span>{" "}
                    {session.globus_id}
                  </li>
                  <li>
                    <span className="text-muted">Name:</span> {profile.name}
                  </li>
                  <li>
                    <span className="text-muted">Email:</span> {profile.email}
                  </li>
                  <li>
                    <span className="text-muted">Phone:</span> {profile.phone}
                  </li>
                  <li>
                    <span className="text-muted">Institution:</span>{" "}
                    {profile.institution}
                  </li>
                  <li>
                    <span className="text-muted">Joined:</span>{" "}
                    {profile.join_date}
                  </li>
                </ul>
              </div>
              <div className="card-footer bg-transparent border-top-0">
                <a
                  href="/profile/edit"
                  className="btn btn-sm btn-primary"
                >
                  Edit profile
                </a>
              </div>
            </div>
          </div>

          <div className="col-sm-6">
            <div className="card h-100">
              <div className="card-header">
                <b>Group memberships</b>
                <i className="fa-solid fa-users float-end"></i>
              </div>
              <div className="card-body">
                {profile.role === "pending" || profile.role === "nonmember" ? (
                  <p className="card-text">
                    Membership status: <RoleBadge role={profile.role} />
                  </p>
                ) : (
                  <table className="table table-sm table-borderless">
                    <thead className="text-muted">
                      <tr>
                        <td>Group name</td>
                        <td>Membership status</td>
                      </tr>
                    </thead>
                    <tbody>
                      {atlasGroups.map((g) => (
                        <tr key={g.name}>
                          <td>{g.name}</td>
                          <td>
                            <RoleBadge role={g.state} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="card-footer bg-transparent border-top-0">
                {profile.role === "nonmember" ? (
                  <a
                    href={`/profile/request_membership/${profile.unix_name}`}
                    className="btn btn-sm btn-primary"
                  >
                    Request membership
                  </a>
                ) : (
                  <a href="/profile/groups" className="btn btn-sm btn-primary">
                    My groups
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>

        {profile.totp_secret && qrCodeDataUrl && (
          <div className="col-lg-12 mx-auto mt-3">
            <div className="row">
              <div className="col-sm-12 col-md-6">
                <div className="card h-100">
                  <div className="card-header">
                    <b>Multi-Factor Authentication</b>
                    <i className="fas fa-user-secret float-end"></i>
                  </div>
                  <div className="card-body" style={{ fontSize: 14 }}>
                    <ol>
                      <li>
                        Download the Google Authenticator application:
                        <ul>
                          <li>
                            <a href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2">
                              Android
                            </a>
                          </li>
                          <li>
                            <a href="https://apps.apple.com/us/app/google-authenticator/id388497605">
                              iOS
                            </a>
                          </li>
                        </ul>
                      </li>
                      <li>
                        You will need to scan the QR code. If it is your first
                        time using the authenticator app, the app will ask for
                        camera access to scan the code. Otherwise, touch the
                        &quot;+&quot; icon in the lower righthand corner and
                        then touch &quot;Scan a QR Code&quot;
                      </li>
                      <li>
                        Use your phone camera to scan the following QR code:{" "}
                        <a href="#" id="showQRCode">
                          Click here
                        </a>
                      </li>
                      <div id="qrCodeContainer" style={{ display: "none" }}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={qrCodeDataUrl} alt="QR Code" />
                      </div>
                      <li>
                        Once scanned, the app will store a cryptographic secret
                        and begin generating six-digit security tokens every 30
                        seconds.
                      </li>
                      <li>
                        When using secure shell to log in to the access point,
                        you will be prompted for the current security token:
                      </li>
                      <div>
                        <kbd>
                          Verification code:{" "}
                          <i>enter your current six-digit token</i>
                        </kbd>
                      </div>
                    </ol>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      <script
        dangerouslySetInnerHTML={{
          __html: `
            document.getElementById('showQRCode')?.addEventListener('click', function(e) {
              e.preventDefault();
              document.getElementById('showQRCode').style.display = 'none';
              document.getElementById('qrCodeContainer').style.display = 'inline-block';
            });
          `,
        }}
      />
    </section>
  );
}
