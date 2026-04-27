# AF Portal

The AF Portal is a web application for the ATLAS Analysis Facility. It provides user and group management, JupyterLab notebook deployment on Kubernetes, resource monitoring (GPU availability, HTCondor jobs, login nodes), and an admin dashboard with user analytics.

## Architecture

The application is built with **Next.js 15** using the App Router. Pages are React Server Components. API endpoints are Next.js Route Handlers under `src/app/**/route.ts`. Business logic lives in `src/lib/`.

```text
src/
├── app/          # Pages and API route handlers (App Router)
├── components/   # React components
├── lib/          # Business logic: auth, connect API, kubernetes, email
└── types/        # Shared TypeScript interfaces
```

## Technology

**Client-side:** React 19, Bootstrap 5, Font Awesome, Recharts, TanStack React Table.

**Server-side:** Next.js 15 (Node.js runtime), TypeScript 5, `@kubernetes/client-node` for Kubernetes management, `iron-session` for encrypted cookie sessions, `jose` for JWT decoding, `p-queue` for email queuing via Mailgun.

## Authentication

Users authenticate via **Globus** (institutional SSO). The OAuth flow is handled in `src/lib/auth/globus.ts`. Sessions are stored in encrypted HTTP-only cookies managed by `iron-session`. Authorization guards in `src/lib/auth/guards.ts` enforce login, member, and admin roles.

## Setup

Copy `.env.local.example` to `.env.local` and fill in the required values:

| Variable | Description |
| --- | --- |
| `GLOBUS_CLIENT_ID` | Globus OAuth application ID |
| `GLOBUS_CLIENT_SECRET` | Globus OAuth secret |
| `GLOBUS_REDIRECT_URI` | OAuth callback URL |
| `SESSION_SECRET` | Random string (32+ chars) for session encryption |
| `CONNECT_API_TOKEN` | CI-Connect API token |
| `CONNECT_API_ENDPOINT` | CI-Connect base URL |
| `MAILGUN_API_TOKEN` | Mailgun API token |
| `NAMESPACE` | Kubernetes namespace for notebooks (e.g. `af-jupyter`) |
| `DOMAIN_NAME` | Base domain (e.g. `af.uchicago.edu`) |
| `KUBECONFIG` | Path to kubeconfig file (leave blank for in-cluster auth) |

Install dependencies:

```bash
npm install
```

## Running locally

```bash
npm run dev
```

Then open <http://localhost:3000>.

Other useful commands:

```bash
npm run build       # production build
npm run start       # run production build
npm run type-check  # TypeScript type checking
npm run lint        # ESLint
```

## Deployment

The application is packaged as a Docker image using the `Dockerfile` (3-stage build: deps → builder → runner, Node 22 Alpine, port 3000).

CI/CD runs on pushes to `main` via `.github/workflows/main.yaml`: builds and pushes the image to `hub.opensciencegrid.org/maniaclab/af-portal`, then triggers a GitOps deployment via repository dispatch to `maniaclab/flux_apps`.
