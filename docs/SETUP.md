# SuperBox Infrastructure Setup Guide

Complete guide for deploying SuperBox AWS infrastructure using either manual AWS Console setup or automated OpenTofu/Terraform.

## Architecture Overview

| Component           | Purpose                     | Details                                   |
| ------------------- | --------------------------- | ----------------------------------------- |
| **S3 Bucket**       | MCP server registry storage | Stores server metadata and package files  |
| **Lambda Function** | MCP executor                | Python 3.11 runtime, executes MCP servers |
| **Function URL**    | Public HTTPS endpoint       | CORS enabled, no authentication           |
| **IAM Role**        | Lambda permissions          | S3 access + CloudWatch logs               |
| **CloudWatch Logs** | Execution logs              | 7-day retention                           |

---

## Method 1: Manual Setup (AWS Console)

### Step 1: Create S3 Bucket

1. Open AWS Console and search **S3**
2. Click **Create bucket**
3. Configure:
   - **Bucket name:** `superbox-registry-prod` (must be globally unique)
   - **Region:** Asia Pacific (Mumbai) `ap-south-1`
   - **Block Public Access:** Keep all 4 checkboxes CHECKED
   - **Versioning:** Disable
   - **Encryption:** SSE-S3 (default)
4. Click **Create bucket**

### Step 2: Create IAM Role

1. Open AWS Console and search **IAM**
2. Click **Roles** → **Create role**
3. Configure:
   - **Trusted entity:** AWS service
   - **Use case:** Lambda
4. Click **Next**
5. Add permissions (search and check both):
   - `AWSLambdaBasicExecutionRole` (CloudWatch logs)
   - `AmazonS3FullAccess` (S3 access)
6. Click **Next**
7. Configure:
   - **Role name:** `superbox-lambda-role`
   - **Description:** Execution role for SuperBox Lambda
8. Click **Create role**

### Step 3: Create Lambda Function

1. Open AWS Console and search **Lambda**
2. Click **Create function**
3. Configure:
   - **Method:** Author from scratch
   - **Function name:** `superbox-executor`
   - **Runtime:** Python 3.11
   - **Architecture:** x86_64
4. Expand **Change default execution role**
   - Select **Use an existing role**
   - Choose `superbox-lambda-role`
5. Click **Create function**

### Step 4: Upload Lambda Code

**Prepare ZIP file locally:**

1. Locate `lambda.py` in project root
2. Right-click → **Send to** → **Compressed (zipped) folder**
3. Rename to `lambda.zip`
4. Ensure `lambda.py` is at root level (not in a folder)

**Upload to Lambda:**

1. In Lambda console, scroll to **Code source** section
2. Click **Upload from** → **.zip file**
3. Click **Upload** → select `lambda.zip` → **Save**
4. Wait for success message
5. Scroll to **Runtime settings** → Click **Edit**
   - **Handler:** Change to `lambda.lambda_handler`
6. Click **Save**

### Step 5: Configure Environment Variables

1. Click **Configuration** tab → **Environment variables**
2. Click **Edit** → **Add environment variable**
3. Add:
   - **Key:** `AWS_REGION` | **Value:** `ap-south-1`
   - **Key:** `S3_BUCKET_NAME` | **Value:** `superbox-registry-prod`
4. Click **Save**

> **Important:** Do NOT create .env file in Lambda. Environment variables are managed through Configuration section.

### Step 6: Configure Timeout and Memory

1. Stay in **Configuration** tab → **General configuration**
2. Click **Edit**
3. Configure:
   - **Timeout:** 0 min 30 sec
   - **Memory:** 256 MB
4. Click **Save**

### Step 7: Add Function URL Invoke Permission

1. Stay in **Configuration** tab → **Permissions**
2. Scroll down to **Resource-based policy statements**
3. Click **Add permissions**
4. Configure:
   - **Function URL:** Select this option
   - **Auth type:** NONE
   - **Statement ID:** `FunctionURLAllowPublicAccess`
   - **Principal:** `*`
   - **Action:** `lambda:InvokeFunctionUrl`
5. Click **Save**

> This permission allows public access to your Function URL

### Step 8: Create Function URL

1. Stay in **Configuration** tab → **Function URL**
2. Click **Create function URL**
3. Configure:
   - **Auth type:** NONE
   - Check **Configure CORS**
   - **Allow origin:** `*`
   - **Allow methods:** Check ALL boxes
   - **Allow headers:** `*`
   - **Max age:** `86400`
4. Click **Save**
5. **Copy the Function URL** (save in notepad)

### Step 9: Test Endpoints

**Browser Testing (GET requests):**

```text
https://your-url.lambda-url.ap-south-1.on.aws/health
https://your-url.lambda-url.ap-south-1.on.aws/list
```

**PowerShell Testing:**

```powershell
# Health check
Invoke-RestMethod -Uri "https://your-url/health" -Method GET

# Search (POST)
Invoke-RestMethod -Uri "https://your-url/search" -Method POST -Body '{"query":"test"}' -ContentType "application/json"
```

### Step 10: View Logs

1. Click **Monitor** tab → **View CloudWatch logs**
2. Click most recent log stream
3. View execution logs and errors

---

## Method 2: Automated (OpenTofu/Terraform)

**Time:** 5-10 minutes | **Difficulty:** Intermediate

### Prerequisites

**Install OpenTofu:**

```powershell
# Windows
winget install OpenTofu.tofu

# macOS
brew install opentofu

# Linux
curl -fsSL https://get.opentofu.org/install-opentofu.sh | bash
```

**Get AWS Credentials:**

1. AWS Console → IAM → Users → Your User → **Security credentials**
2. Click **Create access key** → CLI/SDK
3. Copy **Access Key ID** and **Secret Access Key**

### Step 1: Create Configuration

Create `infra/terraform.tfvars`:

```hcl
aws_access_key = "YOUR_AWS_ACCESS_KEY_ID"
aws_secret_key = "YOUR_AWS_SECRET_ACCESS_KEY"
aws_region     = "ap-south-1"
project_name   = "superbox"
```

> Never commit this file to git (already in .gitignore)

### Step 2: Package Lambda

**Windows:**

```powershell
cd infra
.\scripts\package_lambda.ps1
```

**Linux/macOS:**

```bash
cd infra
chmod +x scripts/package_lambda.sh
./scripts/package_lambda.sh
```

### Step 3: Initialize

```bash
cd infra
tofu init
```

Expected: `Terraform has been successfully initialized!`

### Step 4: Preview Changes

```bash
tofu plan
```

Expected: `Plan: 8 to add, 0 to change, 0 to destroy`

Resources to be created:

- S3 bucket
- IAM role + policies
- Lambda function
- Function URL
- CloudWatch log group

### Step 5: Deploy

```bash
tofu apply
```

Type `yes` when prompted. Wait 1-2 minutes.

Expected output:

```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:
lambda_function_url = "https://abc123xyz.lambda-url.ap-south-1.on.aws/"
s3_bucket_name = "superbox-registry-prod"
lambda_function_name = "superbox-executor"
```

### Step 6: Test

```powershell
# Get Function URL
$url = tofu output -raw lambda_function_url

# Test health
Invoke-RestMethod -Uri "${url}health" -Method GET

# Test list
Invoke-RestMethod -Uri "${url}list" -Method GET
```

---

## API Endpoints

| Path      | Method | Description      | Example Response                                        |
| --------- | ------ | ---------------- | ------------------------------------------------------- |
| `/`       | GET    | Root endpoint    | `{"message": "SuperBox MCP Executor"}`                  |
| `/health` | GET    | Health check     | `{"status": "healthy", "service": "superbox-executor"}` |
| `/list`   | GET    | List all servers | `{"servers": [...]}`                                    |
| `/search` | POST   | Search servers   | `{"results": [...]}`                                    |

**POST Request Body Example:**

```json
{
  "query": "search term"
}
```

---

## Useful Commands (OpenTofu)

```bash
# View all outputs
tofu output

# View specific output
tofu output lambda_function_url

# View current state
tofu show

# Update infrastructure after code changes
tofu plan
tofu apply

# Destroy all resources
tofu destroy
```

---

## Troubleshooting

### Credentials Error

```
Error: error configuring Terraform AWS Provider
```

**Solution:** Check `terraform.tfvars` has correct AWS credentials

### Bucket Already Exists

```
Error: BucketAlreadyExists
```

**Solution:** Change `project_name` in `terraform.tfvars` to make bucket name unique

### Permission Error

```
Error: AccessDenied
```

**Solution:** AWS user needs IAM, S3, Lambda, CloudWatch permissions

### Lambda Execution Errors

**Solution:** Check CloudWatch logs at `/aws/lambda/superbox-executor`

---

## Cost Estimate

| Service         | Monthly Cost                     |
| --------------- | -------------------------------- |
| S3 Storage      | $0.10 - $1.00                    |
| Lambda          | $0.00 - $0.50 (1M requests free) |
| CloudWatch Logs | $0.00 - $0.10 (5GB free)         |
| Data Transfer   | $0.00 - $0.50 (100GB free)       |
| **Total**       | **$0.10 - $2.00**                |

> Most usage stays within AWS Free Tier

---

## Next Steps

**After Deployment:**

- Test all API endpoints
- Upload test MCP server to S3
- Integrate Function URL into CLI
- Set up CloudWatch alerts
- Configure custom domain (optional)

**Production Hardening:**

- Restrict S3 bucket policy
- Replace S3FullAccess with limited policy
- Enable CloudTrail audit logging
- Add API rate limiting
- Implement authentication
- Enable S3 versioning

---

## Support

- **Logs:** CloudWatch at `/aws/lambda/superbox-executor`
- **State:** Stored locally at `infra/terraform.tfstate`
