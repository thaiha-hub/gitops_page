# GitOps Status Page

A small course project that deploys a static frontend and a Python Lambda API to AWS using OpenTofu and GitHub Actions.

The page shows today's date and a small list of matching events. The frontend is hosted in S3 behind CloudFront. The `/today` API is served by Lambda through API Gateway. GitHub Actions runs tests and deploys changes from `main`.

## Project Structure

- `frontend/` contains the static HTML, CSS, and JavaScript.
- `lambda/` contains the Python Lambda handler and unit tests.
- `bootstrap/` creates the S3 bucket used for OpenTofu remote state.
- `infra/` creates the application infrastructure and the GitHub Actions OIDC role.
- `.github/workflows/deploy.yml` tests and deploys the project.

## Prerequisites

- AWS account and AWS CLI credentials configured locally.
- OpenTofu `>= 1.8.0`.
- Python 3.12 or newer for local tests.
- A GitHub repository for this project.

## 1. Run Tests Locally

```bash
python3 -m pip install -r lambda/requirements-dev.txt
python3 -m pytest lambda
```

## 2. Create The OpenTofu State Bucket

Run the bootstrap OpenTofu once from your local machine:

```bash
tofu -chdir=bootstrap init
tofu -chdir=bootstrap apply
tofu -chdir=bootstrap output opentofu_state_bucket
```

Copy the output bucket name into `infra/providers.tf`, replacing:

```hcl
bucket = "gitops-page-tfstate-REPLACE_ME"
```

## 3. Deploy Infrastructure Once Locally

The first infrastructure deployment must be run locally because it creates the GitHub Actions role that GitHub will use later.

Replace `OWNER/REPO` with your GitHub repository, for example `thaiha/gitops_page`:

```bash
tofu -chdir=infra init
tofu -chdir=infra apply -var="github_repo=OWNER/REPO"
tofu -chdir=infra output github_actions_role_arn
```

## 4. Add GitHub Secret

In GitHub, open:

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

Create this secret:

```text
AWS_ROLE_ARN=<value from tofu output github_actions_role_arn>
```

## 5. Deploy With GitOps

Commit and push to `main`. GitHub Actions will:

1. Run the Lambda unit tests.
2. Apply OpenTofu from `infra/`.
3. Generate `frontend/config.js` with the API Gateway URL.
4. Upload the frontend to S3.
5. Invalidate the CloudFront cache.

After the workflow finishes, check the `CLOUDFRONT_URL` value in the workflow summary or run:

```bash
tofu -chdir=infra output cloudfront_url
```

## Useful Commands

```bash
tofu -chdir=infra fmt
tofu -chdir=infra validate
tofu -chdir=infra output
python3 -m pytest lambda
```
