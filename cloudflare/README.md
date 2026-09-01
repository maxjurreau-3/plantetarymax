# Cloudflare deployment (Worker + Pages)

This folder contains the Worker Durable Object broker implementation and GitHub Actions to deploy both the Worker and the frontend (Max-View) to Cloudflare Pages.

Required GitHub repository secrets:
- CF_API_TOKEN           - Cloudflare API token with permissions to publish Workers and Pages
- CF_ACCOUNT_ID          - Cloudflare account id
- CF_PAGES_PROJECT_NAME  - Pages project name (for the Pages deploy action)
- VITE_API_BASE          - URL of the deployed Worker (set for Pages build)
- EVENTS_PUBLISH_TOKEN   - publish token for authenticated publishers

Files added
- wrangler.toml           - Worker config and Durable Object binding
- src/index.ts            - Worker + BrokerDO (SSE, per-channel DO, publish forwarding, snapshot)
- .github/workflows/deploy-worker.yml - publishes Worker on push
- .github/workflows/deploy-pages.yml  - builds & deploys Max-View to Pages

Manual deploy (local)
1. Install Wrangler:
   npm install -g wrangler
   wrangler login

2. Provision Worker secrets:
   wrangler secret put EVENTS_PUBLISH_TOKEN

3. Publish Worker:
   wrangler publish --env production

Notes & recommendations
- Durable Object per channel is used (idFromName(channel)). This keeps subscribers for a channel in one DO instance.
- SSE is implemented using ReadableStream in the DO. Keep an eye on connection counts and memory usage.
- The publish endpoint requires EVENTS_PUBLISH_TOKEN. Rotate and store the token securely.
- For snapshots we use DO.storage (per-channel). For cross-channel data, use Workers KV.
- Ensure VITE_API_BASE in Pages build points to the deployed Worker URL so the frontend connects correctly.
