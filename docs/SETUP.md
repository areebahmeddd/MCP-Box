# SuperBox Infrastructure Setup Guide

Complete guide for deploying SuperBox infrastructure on Cloudflare using Wrangler.

## Architecture Overview

| Component             | Resource Name           | Purpose                                              |
| --------------------- | ----------------------- | ---------------------------------------------------- |
| **Cloudflare Worker** | `superbox-executor`     | Entry point: CORS, routing, session management       |
| **Durable Object**    | `McpSession`            | Per-session MCP execution via TypeScript interpreter |
| **R2 Bucket**         | `superbox-mcp-registry` | Stores MCP server metadata as JSON files             |

## Prerequisites

**Install Wrangler:**

```bash
npm install -g wrangler
```

**Authenticate with Cloudflare:**

```bash
wrangler login
```

**Create an R2 API Token** (for CLI access from the Python backend):

1. Cloudflare Dashboard → **R2** → **Manage R2 API Tokens** → **Create API Token**
2. Set permissions: **Edit** (Object Read & Write)
3. Copy the **Access Key ID** and **Secret Access Key**

## Step 1: Create R2 Bucket

```bash
wrangler r2 bucket create superbox-mcp-registry
```

For a dev/staging bucket:

```bash
wrangler r2 bucket create superbox-mcp-registry-dev
```

## Step 2: Deploy the Worker

```bash
cd cloudflare
npm install
wrangler deploy
```

After deployment, the Worker URL has the form:

```
https://superbox-executor.<your-subdomain>.workers.dev
```

## Step 3: Configure Environment Variables

Create `.env` at the repo root (never commit this file):

```env
# Cloudflare
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=superbox-mcp-registry
CLOUDFLARE_WORKER_URL=https://superbox-executor.<your-subdomain>.workers.dev

# Firebase
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_PROJECT_ID=your_firebase_project_id

# Razorpay
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

Your **Account ID** is visible in the Cloudflare Dashboard URL: `dash.cloudflare.com/<account_id>`.

## Step 4: Verify Deployment

```bash
curl https://superbox-executor.<your-subdomain>.workers.dev/health
```

Expected response:

```json
{ "status": "ok", "worker": "superbox-executor" }
```

## Useful Commands

```bash
wrangler deploy                    # deploy Worker changes
wrangler dev                       # run Worker locally on http://localhost:8787
wrangler tail superbox-executor    # stream live logs
wrangler r2 object list superbox-mcp-registry  # list registry entries
wrangler r2 bucket delete superbox-mcp-registry  # tear down bucket
```

## Troubleshooting

| Error                               | Solution                                                       |
| ----------------------------------- | -------------------------------------------------------------- |
| `authentication error` on R2        | Regenerate R2 API token with Object Read & Write permissions   |
| `No such bucket`                    | Run `wrangler r2 bucket create superbox-mcp-registry`          |
| Pyodide load timeout                | Durable Object cold start can take 3–10 s; retry the request   |
| `Script startup exceeded CPU limit` | Pyodide loads lazily on first tool call, not at Worker startup |

## Cost Estimate

| Service             | Monthly Cost (approx.)     |
| ------------------- | -------------------------- |
| Workers (free tier) | 100k requests/day free     |
| Durable Objects     | 1M requests free / month   |
| R2 Storage          | 10 GB free, ₹1.27/GB after |
| **Total**           | **₹0 for moderate usage**  |

> All usage typically stays within Cloudflare's free tier for development and small production loads.

## Support

- **Live logs:** `wrangler tail superbox-executor --format pretty`
- **Dashboard:** [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → superbox-executor
