# gitops_page — Architecture & Codebase Guide

## What this project does

**gitops_page** is a small web application that shows today's date and any notable events (holidays, observances) for that day. It is deployed fully automatically to AWS every time code is pushed to the `main` branch.

The project is also a GitOps learning exercise: all infrastructure is defined as code with OpenTofu (the open-source Terraform fork), and GitHub Actions drives every deployment — no manual AWS console work after the initial bootstrap.

---

## Repository layout

```
gitops_page/
├── bootstrap/          # One-time setup: creates the S3 bucket that stores OpenTofu state
├── infra/              # Main infrastructure: all AWS resources the app needs
├── frontend/           # Static web page (HTML + JS)
├── lambda/             # Python backend (AWS Lambda function + tests)
└── .github/workflows/
    └── deploy.yml      # CI/CD pipeline
```

---

## How a request flows at runtime

```
User's browser
    │
    ▼
CloudFront (CDN, HTTPS)
    │  serves static files
    ▼
S3 bucket  (index.html + app.js + config.js)
    │
    │  app.js calls the API URL injected at deploy time
    ▼
API Gateway HTTP API  (GET /today)
    │
    ▼
Lambda function  (Python)
    │  looks up today's date and returns matching events
    ▼
JSON response  →  browser renders date + event list
```

---

## Component deep-dive

### frontend/

Two files, no build step.

**`index.html`** — The page shell. Contains inline CSS for a centred card layout. Loads `config.js` (injected at deploy time) then `app.js`.

**`app.js`** — Reads `window.API_URL` (set by `config.js`), fetches `GET /today`, and renders the date and event list into the DOM. Falls back to `/today` if `window.API_URL` is not set (useful for local development).

**`config.js`** — Not in the repo. Generated during deployment:
```js
window.API_URL='https://<api-id>.execute-api.eu-north-1.amazonaws.com/today';
```
It is listed in `.gitignore` because the URL is only known after the infrastructure is deployed.

---

### lambda/

**`handler.py`** — The Lambda function. Contains a hard-coded `EVENTS` dictionary keyed by `MM-DD` (e.g. `"12-24": ["Christmas Eve"]`). On each invocation it:
1. Gets today's UTC date via `datetime.datetime.now(datetime.timezone.utc).date()`
2. Looks up `MM-DD` in the dictionary
3. Returns a JSON response with `date` (ISO-8601) and `events` (list of strings)

The response includes `Access-Control-Allow-Origin: *` so the browser can call it from the CloudFront domain.

**`test_handler.py`** — pytest unit tests. Tests cover: specific known dates return the right events, an ordinary date returns an empty list, the handler response shape, and the CORS header. Uses `unittest.mock.patch` to freeze the date.

**`requirements-dev.txt`** — Contains only `pytest==8.3.5`. The handler itself has no third-party dependencies (only stdlib).

---

### bootstrap/

A separate, standalone OpenTofu root module. Run **once by hand** (with developer AWS credentials) before anything else.

**What it creates:**
- An S3 bucket named `gitops-page-tfstate-<random-8-hex-chars>` to store the main infra's OpenTofu state file
- Versioning enabled on that bucket (so state history is preserved and accidental deletes are recoverable)
- AES-256 server-side encryption on the bucket
- Public access fully blocked

**Why it is separate:** OpenTofu state must exist somewhere before it can store state. The bootstrap bucket cannot manage itself, so it is applied locally once and its state lives in the `bootstrap/terraform.tfstate` file (which is gitignored — keep it safe).

After running bootstrap, copy the output bucket name into `infra/providers.tf`:
```hcl
backend "s3" {
  bucket = "gitops-page-tfstate-<your-suffix>"
  ...
}
```

---

### infra/

The main OpenTofu module. Contains all AWS resources that make the app work. Applied automatically by GitHub Actions on every push to `main`.

#### providers.tf — Backend & provider config

```hcl
terraform {
  required_version = ">= 1.8.0"
  backend "s3" {
    bucket = "gitops-page-tfstate-a1618081"   # created by bootstrap
    key    = "terraform.tfstate"
    region = "eu-north-1"
  }
}
provider "aws" { region = var.aws_region }
```

State is stored remotely in S3 so GitHub Actions and local runs share the same state. There is no DynamoDB locking table — concurrent applies could theoretically corrupt state, though this is low risk for a single-developer project.

#### variables.tf

| Variable | Default | Purpose |
|---|---|---|
| `aws_region` | `eu-north-1` | AWS region for all resources |
| `github_repo` | *(required)* | `org/repo` used in the OIDC trust policy |

`github_repo` is set automatically in CI via `TF_VAR_github_repo: ${{ github.repository }}`.

#### main.tf — AWS resources

**`random_id.suffix`** — Generates a random 4-byte (8 hex char) suffix. Used to make the S3 bucket name globally unique. The suffix is stable for the lifetime of the state file.

**S3 (`aws_s3_bucket.frontend`)** — Stores the static frontend files. Named `gitops-page-<suffix>`. All public access is blocked; the bucket is only accessible via CloudFront using Origin Access Control.

**CloudFront OAC + distribution** — Serves the frontend over HTTPS with a CloudFront domain. Uses `PriceClass_100` (US/Europe/Asia edge locations). Cache TTL is 60 seconds default, 5 minutes max. All HTTP traffic is redirected to HTTPS. The S3 bucket policy allows only CloudFront (via OAC) to call `s3:GetObject`.

**Lambda (`aws_lambda_function.info`)** — Python 3.12 runtime. The zip is built from `lambda/handler.py` using the `archive` provider's `archive_file` data source. The source hash ensures Lambda is redeployed whenever the handler code changes.

**API Gateway (`aws_apigatewayv2_api.info`)** — HTTP API (not REST API — simpler and cheaper). Single route: `GET /today` → Lambda integration. CORS is configured at the API level to allow `GET` from any origin. Auto-deploy is enabled on the `$default` stage, so changes apply immediately.

**GitHub OIDC (`aws_iam_openid_connect_provider.github`)** — Registers GitHub Actions' OIDC issuer (`token.actions.githubusercontent.com`) as a trusted identity provider in the AWS account. This allows GitHub Actions to assume an IAM role without storing any AWS credentials as secrets.

**GitHub Actions IAM role (`aws_iam_role.github_actions`)** — Can only be assumed via OIDC by a GitHub Actions workflow running in the configured repository (`var.github_repo`). The trust policy uses `StringLike` on the `sub` claim so any branch/environment in the repo can assume it.

**GitHub Actions IAM policy (`aws_iam_role_policy.github_actions`)** — Grants the minimum permissions needed for `tofu apply` to succeed. Broken into named statements:

| Sid | What it allows |
|---|---|
| `S3Frontend` | Full CRUD + bucket inspection on `gitops-page-*` (the frontend bucket and the state bucket share this prefix) |
| `OpenTofuState` | Read/write to the state bucket `gitops-page-tfstate-*` |
| `CloudFront` | Create/update the distribution and OAC; invalidate cache |
| `Lambda` | Create/update the function and manage its resource-based policy |
| `APIGateway` | Full API Gateway access (needed because the provider makes many API calls) |
| `IAMPassRole` | Pass the Lambda execution role to Lambda |
| `IAMManage` | Create/update/delete IAM roles and the GitHub OIDC provider |
| `STSState` | `GetCallerIdentity` (used by the AWS provider to resolve account ID) |

#### outputs.tf

After `tofu apply`, these values are printed and used by later workflow steps:

| Output | Used for |
|---|---|
| `cloudfront_url` | Written to the GitHub Actions job summary so you can click straight to the site |
| `api_url` | Injected into `frontend/config.js` at deploy time |
| `s3_bucket_name` | Used by `aws s3 sync` to upload the frontend |
| `cloudfront_distribution_id` | Used by `aws cloudfront create-invalidation` |
| `github_actions_role_arn` | Copy this value into `AWS_ROLE_ARN` in GitHub repository secrets (one-time setup) |

---

### .github/workflows/deploy.yml

Triggers on push to `main` and on `workflow_dispatch` (manual trigger).

**Permissions:** `id-token: write` (required for OIDC) and `contents: read`.

#### Job 1 — `test`

Runs the pytest suite against the Lambda handler on `ubuntu-latest` with Python 3.12. The deploy job will not start if tests fail.

#### Job 2 — `deploy` (needs: test)

Steps in order:

1. **Checkout** — checks out the repo
2. **Configure AWS credentials** — exchanges the GitHub OIDC token for temporary AWS credentials by assuming `AWS_ROLE_ARN` (stored as a repository secret)
3. **Set up OpenTofu** — installs the `tofu` CLI via the official `opentofu/setup-opentofu@v1` action
4. **tofu init** — initialises providers and connects to the S3 backend
5. **tofu apply (IAM policy first)** — applies *only* `aws_iam_role_policy.github_actions` with `-refresh=false`. This is a bootstrap-cycle fix: the live IAM policy may not yet have permissions to read existing resources, so we update it first using the state file rather than refreshing from AWS.
6. **tofu apply** — full apply with refresh. By this point the role has the correct permissions.
7. **Read outputs** — captures `S3_BUCKET`, `API_URL`, `CLOUDFRONT_DISTRIBUTION_ID`, and `CLOUDFRONT_URL` into environment variables and the job summary.
8. **Create frontend config** — writes `frontend/config.js` with the live API URL.
9. **Upload frontend** — syncs `frontend/` to S3 with `--delete` (removes stale files).
10. **Invalidate CloudFront** — purges `/*` so users immediately get the new frontend.

---

## First-time setup (how to go from zero to running)

1. **Bootstrap the state bucket** (run once, locally, with admin AWS credentials):
   ```bash
   cd bootstrap
   tofu init
   tofu apply
   # note the output bucket name
   ```

2. **Paste the bucket name** into `infra/providers.tf` under `backend "s3" { bucket = "..." }`.

3. **Add the GitHub secret** `AWS_ROLE_ARN`:
   - Run `cd infra && tofu output github_actions_role_arn` after the first manual apply, or find it in the AWS console under IAM roles (`gitops-status-page-github-actions`).
   - Add it as a repository secret in GitHub → Settings → Secrets → Actions.

4. **Push to `main`** — the workflow runs, deploys everything, and prints the CloudFront URL in the job summary.

---

## Key design decisions

| Decision | Reason |
|---|---|
| CloudFront in front of S3 | S3 static websites can't serve HTTPS directly; CloudFront provides HTTPS, caching, and restricts direct bucket access |
| OAC instead of OAI | Origin Access Control is the current AWS recommendation; OAI is legacy |
| GitHub OIDC instead of access keys | No long-lived credentials to rotate or leak |
| `random_id` suffix on bucket names | S3 bucket names are globally unique; the suffix avoids collisions without requiring a manual name decision |
| Bootstrap as a separate module | The state bucket cannot manage itself; separating it avoids a chicken-and-egg problem |
| Two-step apply in CI | The IAM policy must be updated before OpenTofu can refresh the resources it governs; applying it first with `-refresh=false` breaks the cycle |
