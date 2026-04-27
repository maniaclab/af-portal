import type { UserRole } from "@/types";
import Image from "next/image";

interface NavbarProps {
  isAuthenticated: boolean;
  role?: UserRole;
}

export default function Navbar({ isAuthenticated, role }: NavbarProps) {
  return (
    <header>
      <nav className="navbar navbar-expand-lg bg-light">
        <div className="container-fluid">
          <a className="navbar-brand" href="/">
            <Image
              src="/img/atlas-af-logo.png"
              height={35}
              width={175}
              alt="ATLAS AF"
              style={{ height: 35, width: "auto" }}
            />
          </a>
          <button
            className="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
            aria-controls="navbarNav"
            aria-expanded="false"
            aria-label="Toggle navigation"
          >
            <span className="navbar-toggler-icon"></span>
          </button>
          <div
            className="collapse navbar-collapse justify-content-end"
            id="navbarNav"
          >
            <ul className="navbar-nav">
              {isAuthenticated ? (
                <>
                  {role === "admin" && (
                    <li className="nav-item dropdown">
                      <a
                        className="nav-link dropdown-toggle"
                        href="#"
                        role="button"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                      >
                        Admin
                      </a>
                      <ul className="dropdown-menu dropdown-menu-end">
                        <li>
                          <a className="dropdown-item" href="/admin/users">
                            Users
                          </a>
                        </li>
                        <li>
                          <a
                            className="dropdown-item"
                            href="/admin/groups/root.atlas-af"
                          >
                            Groups
                          </a>
                        </li>
                        <li>
                          <a className="dropdown-item" href="/admin/notebooks">
                            Notebooks
                          </a>
                        </li>
                      </ul>
                    </li>
                  )}
                  <li className="nav-item dropdown">
                    <a
                      className="nav-link dropdown-toggle"
                      href="#"
                      role="button"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                    >
                      Monitoring
                    </a>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li>
                        <a
                          className="dropdown-item"
                          href="/monitoring/notebooks"
                        >
                          Notebooks
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="/monitoring/login_nodes"
                        >
                          Login Nodes
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="/monitoring/htcondor_usage"
                        >
                          HTCondor Usage
                        </a>
                      </li>
                    </ul>
                  </li>
                  <li className="nav-item dropdown">
                    <a
                      className="nav-link dropdown-toggle"
                      href="#"
                      role="button"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                    >
                      Services
                    </a>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li>
                        <a className="dropdown-item" href="/jupyterlab">
                          JupyterLab
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="https://coffea.af.uchicago.edu/"
                          target="_blank"
                          rel="noreferrer"
                        >
                          Coffea Casa
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="https://binderhub.af.uchicago.edu/"
                          target="_blank"
                          rel="noreferrer"
                        >
                          BinderHub(test)
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="https://servicex.af.uchicago.edu"
                          target="_blank"
                          rel="noreferrer"
                        >
                          ServiceX
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="/chat"
                          target="_blank"
                          rel="noreferrer"
                        >
                          Assistant
                        </a>
                      </li>
                    </ul>
                  </li>
                  <li className="nav-item dropdown">
                    <a
                      className="nav-link dropdown-toggle"
                      href="#"
                      role="button"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                    >
                      Documentation
                    </a>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li>
                        <a
                          className="dropdown-item"
                          href="https://usatlas.github.io/af-docs/"
                          target="_blank"
                          rel="noreferrer"
                        >
                          US ATLAS Docs
                        </a>
                      </li>
                      <li>
                        <a className="dropdown-item" href="/aup">
                          Acceptable Use Policy
                        </a>
                      </li>
                      <li>
                        <a className="dropdown-item" href="/hardware">
                          Hardware
                        </a>
                      </li>
                      <li>
                        <a className="dropdown-item" href="/about">
                          About Page
                        </a>
                      </li>
                    </ul>
                  </li>
                  <li className="nav-item dropdown">
                    <a
                      className="nav-link dropdown-toggle"
                      href="#"
                      role="button"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                    >
                      Support
                    </a>
                    <ul className="dropdown-menu dropdown-menu-end">
                      <li>
                        <a
                          className="dropdown-item"
                          href="https://atlas-talk.sdcc.bnl.gov/"
                          target="_blank"
                          rel="noreferrer"
                        >
                          Discourse Forums
                        </a>
                      </li>
                      <li>
                        <a
                          className="dropdown-item"
                          href="mailto:atlas-us-chicago-tier3-admins@cern.ch"
                        >
                          System or Login Problems
                        </a>
                      </li>
                    </ul>
                  </li>
                  <li className="nav-item dropdown">
                    <a
                      className="nav-link dropdown-toggle"
                      href="#"
                      role="button"
                      data-bs-toggle="dropdown"
                      aria-expanded="false"
                    >
                      Account
                    </a>
                    <ul
                      className="dropdown-menu dropdown-menu-end"
                      style={{ minWidth: 100 }}
                    >
                      <li>
                        <a className="dropdown-item" href="/profile">
                          Profile
                        </a>
                      </li>
                      <li>
                        <a className="dropdown-item" href="/auth/logout">
                          Logout
                        </a>
                      </li>
                    </ul>
                  </li>
                </>
              ) : (
                <>
                  <li className="nav-item">
                    <a
                      className="nav-link"
                      href="https://atlas-kibana.mwt2.org:5601/s/analysis-facility/app/dashboards?auth_provider_hint=anonymous1#/view/8bb58440-6145-11ed-afcf-d91dad577662?_g=()&_a=()"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Dashboard
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/about">
                      About
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/auth/login">
                      Login
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/signup">
                      Signup
                    </a>
                  </li>
                </>
              )}
            </ul>
          </div>
        </div>
      </nav>
    </header>
  );
}
