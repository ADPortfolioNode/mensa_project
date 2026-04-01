Vercel Deployment — Quick Walkthrough

Overview
- This repository is a monorepo: the production frontend is in `frontend/` (Create React App). The backend (`backend/`) contains a FastAPI app with heavy dependencies and native libs; it is NOT recommended to deploy the backend as Vercel Serverless functions.

What this config does
- `vercel.json` at repo root instructs Vercel to build the `frontend` using `@vercel/static-build` and expects a secret named `backend_url` to be created in Vercel. The frontend reads the API base from `REACT_APP_API_BASE` at runtime.

Quick project setup (Vercel Desktop)
1. Install and login: `vercel` desktop or CLI and connect your Git provider.
2. Import repository and select this repo.
3. In the Import settings:
   - Root Directory: leave blank (root repo)
   - Framework Preset: "Other" or "Create React App" (we use a custom build command below)
   - Build Command: `npm --prefix frontend run build`
   - Output Directory: `frontend/build`
4. Environment variables (Project Settings → Environment Variables):
   - Create a Secret called `backend_url` (value: your backend public URL, e.g. `https://api.example.com`).
   - Set `REACT_APP_API_BASE` to `@backend_url` (this uses the secret at build/runtime).

Notes on the backend
- The `backend/` service depends on large libs (TensorFlow, Chromadb) and expects persistent storage and Chroma. Deploy the backend to a container-friendly host (e.g., Docker-based host, Render, Fly, Railway, or a VM) and set `backend_url` to that service's public URL.

Local testing
- Build locally to verify:
```
npm --prefix frontend ci
npm --prefix frontend run build
npx serve -s frontend/build -l 3000
```
- To run the backend locally use the usual docker/compose flow documented in the repo (recommended) or `uvicorn`/`hypercorn` as in `backend/Dockerfile`.

Troubleshooting
- If the site can't reach the API: verify `REACT_APP_API_BASE` in Vercel Project → Environment Variables.
- For SPA routing issues, add a rewrite in the Vercel dashboard: route all unmatched paths to `/index.html` (usually not necessary with `@vercel/static-build`).

Next steps (optional)
- Add a lightweight `api/` proxy (Vercel Serverless) only if you must transform requests; otherwise use direct backend URL.
- Add a CI/CD Git branch preview configuration in Vercel to deploy PR branches.
