# SuperBox Infrastructure Setup Guide

Complete guide for deploying SuperBox AWS infrastructure using either manual AWS Console setup or automated OpenTofu/Terraform.

## Architecture Overview

| Component           | Resource Name                       | Purpose                                   |
| ------------------- | ----------------------------------- | ----------------------------------------- |
| **S3 Bucket**       | `superbox-mcp-registry`             | Stores MCP server metadata as JSON files  |
| **Lambda Function** | `superbox-mcp-executor`             | Runs MCP servers in isolated subprocesses |
| **WebSocket API**   | `superbox-mcp-ws`                   | Persistent connections for MCP protocol   |
| **IAM Role**        | `superbox-lambda-role`              | S3, CloudWatch, and WebSocket permissions |
| **CloudWatch Logs** | `/aws/lambda/superbox-mcp-executor` | Execution logs, 7-day retention           |

---

## Method 1: Manual Setup (AWS Console)

### Step 1: Create S3 Bucket

1. Open AWS Console → search **S3** → **Create bucket**
2. Configure:
   - **Bucket name:** `superbox-mcp-registry` (must be globally unique)
   - **Region:** Asia Pacific (Mumbai) `ap-south-1`
   - **Block Public Access:** keep all 4 checkboxes checked
   - **Encryption:** SSE-S3 (default)
3. Click **Create bucket**

### Step 2: Create IAM Role

1. Open AWS Console → search **IAM** → **Roles** → **Create role**
2. Configure:
   - **Trusted entity:** AWS service → **Lambda**
3. Attach permissions:
   - `AWSLambdaBasicExecutionRole`
   - `AmazonS3FullAccess`
   - `AmazonAPIGatewayInvokeFullAccess`
4. Configure:
   - **Role name:** `superbox-lambda-role`
5. Click **Create role**

### Step 3: Create Lambda Function

1. Open AWS Console → search **Lambda** → **Create function**
2. Configure:
   - **Method:** Author from scratch
   - **Function name:** `superbox-mcp-executor`
   - **Runtime:** Python 3.11
   - **Architecture:** x86_64
3. Expand **Change default execution role** → **Use an existing role** → select `superbox-lambda-role`
4. Click **Create function**

### Step 4: Upload Lambda Code

1. Locate `infra/aws/lambda.py`, zip it as `lambda_payload.zip` (file must be at root of zip)
2. In Lambda console → **Code source** → **Upload from** → **.zip file** → upload `lambda_payload.zip` → **Save**
3. Scroll to **Runtime settings** → **Edit** → set **Handler** to `lambda.lambda_handler` → **Save**

### Step 5: Configure Environment Variables

1. **Configuration** tab → **Environment variables** → **Edit** → **Add environment variable**
2. Add:
   - `AWS_REGION` = `ap-south-1`
   - `S3_BUCKET_NAME` = `superbox-mcp-registry`
3. Click **Save**

> Do **not** create a `.env` file in Lambda. All env vars are managed through the Configuration tab.

### Step 6: Configure Timeout and Memory

1. **Configuration** tab → **General configuration** → **Edit**
2. Set **Timeout** to `1 min 0 sec` and **Memory** to `1024 MB`
3. Click **Save**

### Step 7: Create WebSocket API

1. Open AWS Console → search **API Gateway** → **Create API**
2. Choose **WebSocket API** → **Build**
3. Configure:
   - **API name:** `superbox-mcp-ws`
   - **Route selection expression:** `$request.body.action`
4. Click **Next**

### Step 8: Configure Routes

Add three routes and set their integration to the `superbox-mcp-executor` Lambda for each:

| Route key     | Integration type | Lambda function         |
| ------------- | ---------------- | ----------------------- |
| `$connect`    | Lambda           | `superbox-mcp-executor` |
| `$disconnect` | Lambda           | `superbox-mcp-executor` |
| `$default`    | Lambda           | `superbox-mcp-executor` |

### Step 9: Deploy to Stage

1. Click **Deploy API**
2. Create a new stage named `production`
3. Click **Deploy**
4. **Copy the WebSocket URL** — it will look like:
   `wss://xxxxxxxxxx.execute-api.ap-south-1.amazonaws.com/production`

### Step 10: Grant Lambda Permission

In the Lambda console → **Configuration** → **Permissions** → **Resource-based policy statements** → **Add permissions**:

- **AWS service:** API Gateway
- **Statement ID:** `AllowWebSocketInvoke`
- **Action:** `lambda:InvokeFunction`
- **Source ARN:** `arn:aws:execute-api:ap-south-1:*:*/production/*/*`

Click **Save**.

### Step 11: View Logs

1. Lambda console → **Monitor** tab → **View CloudWatch logs**
2. Click the most recent log stream to view execution output

---

## Method 2: Automated — OpenTofu/Terraform _(Recommended)_

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

1. AWS Console → IAM → Users → your user → **Security credentials**
2. Click **Create access key** → CLI/SDK
3. Copy the **Access Key ID** and **Secret Access Key**

### Step 1: Create Configuration

```powershell
cd infra
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `infra/terraform.tfvars`:

```hcl
aws_access_key = "YOUR_ACCESS_KEY_ID"
aws_secret_key = "YOUR_SECRET_ACCESS_KEY"
aws_region     = "ap-south-1"
project_name   = "superbox"
```

> Never commit this file — it is already in `.gitignore`.

### Step 2: Package Lambda

```powershell
# Windows (from infra/)
.\scripts\package_lambda.ps1
```

```bash
# Linux/macOS (from infra/)
chmod +x scripts/package_lambda.sh
./scripts/package_lambda.sh
```

This builds `modules/lambda/lambda_payload.zip` from `aws/lambda.py`.

### Step 3: Deploy

```bash
cd infra
tofu init    # download providers
tofu plan    # preview — expect ~12 resources to add
tofu apply   # type "yes", takes 1-2 minutes
```

### Step 4: Save Outputs

After `tofu apply` completes:

```
s3_bucket_name       = "superbox-mcp-registry"
websocket_url        = "wss://xxxxxxxxxx.execute-api.ap-south-1.amazonaws.com/production"
lambda_function_name = "superbox-mcp-executor"
cloudwatch_log_group = "/aws/lambda/superbox-mcp-executor"
```

Copy `s3_bucket_name` and `websocket_url` — you need these in your `.env`.

---

## Useful Commands

```bash
tofu output                        # view all outputs
tofu output -raw websocket_url     # get WebSocket URL
tofu show                          # inspect current state
tofu apply                         # re-apply after code changes
tofu destroy                       # tear down all resources
```

**Update Lambda code after changes:**

```powershell
.\scripts\package_lambda.ps1
tofu apply
```

**View live logs:**

```bash
aws logs tail /aws/lambda/superbox-mcp-executor --follow
```

---

## Troubleshooting

| Error                                      | Solution                                                                |
| ------------------------------------------ | ----------------------------------------------------------------------- |
| `error configuring Terraform AWS Provider` | Check `terraform.tfvars` credentials                                    |
| `BucketAlreadyExists`                      | Change `project_name` — bucket name must be globally unique             |
| `AccessDenied`                             | IAM user needs S3, Lambda, IAM, CloudWatch, and API Gateway permissions |
| Lambda runtime errors                      | Check CloudWatch at `/aws/lambda/superbox-mcp-executor`                 |

---

## Cost Estimate

| Service          | Monthly Cost                |
| ---------------- | --------------------------- |
| S3 Storage       | ₹9 – ₹85 (1M requests free) |
| Lambda           | ₹0 – ₹42 (1M requests free) |
| API Gateway (WS) | ₹0 – ₹85 (1M messages free) |
| CloudWatch Logs  | ₹0 – ₹9 (5 GB free)         |
| **Total**        | **₹9 – ₹210**               |

> Most usage stays within AWS Free Tier.

---

## Support

- **Logs:** CloudWatch at `/aws/lambda/superbox-mcp-executor`
- **State:** Stored locally at `infra/terraform.tfstate`
