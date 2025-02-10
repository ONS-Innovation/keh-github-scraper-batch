# GitHub Organisation Repository Technology Lambda

The purpose of this lambda function is to acquire technolgies used across different repositories across ONSDigital

## Setup

Set the appropriate environment variables:
```bash
export GITHUB_ORG='<ORG NAME>'
export GITHUB_APP_CLIENT_ID='<CLIENT ID>'
export AWS_SECRET_NAME='<SECRET_NAME>'
export AWS_DEFAULT_REGION='eu-west-2'
export SOURCE_BUCKET='sdp-dev-github-scraper'
```

## Running the script
```bash
poetry run python app.py
```

These instructions assume:

1. You have a repository set up in your AWS account named sdp-dev-github-scraper.
2. You have created an AWS IAM user with permissions to read/write to ECR (e.g AmazonEC2ContainerRegistryFullAccess policy) and that you have created the necessary access keys for this user. The credentials for this user are stored in ~/.aws/credentials and can be used by accessing --profile <aws-credentials-profile>, if these are the only credentials in your file then the profile name is default.

You can find the AWS repo push commands under your repository in ECR by selecting the "View Push Commands" button. This will display a guide to the following (replace <aws-credentials-profile>, <aws-account-id> and <version> accordingly):

Get an authentication token and authenticate your docker client for pushing images to ECR:

```bash
aws ecr --profile <aws-credentials-profile> get-login-password --region eu-west-2 | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com
```

Tag your latest built docker image for ECR (assumes you have run docker build -t sdp-repo-archive . locally first)

```bash
docker tag sdp-dev-github-scraper:latest <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/sdp-dev-github-scraper:<version>
```

Note: To find the <version> to build look at the latest tagged version in ECR and increment appropriately

Push the version up to ECR

```bash
docker push <aws-account-id>.dkr.ecr.eu-west-2.amazonaws.com/sdp-dev-github-scraper:<version>
```

## Updating the running service using Terraform

If the application has been modified then the following can be performed to update the running service:

Build a new version of the container image and upload to ECR as per the instructions earlier in this guide.

Change directory to the dashboard terraform

```bash
cd terraform/lambda
```

In the appropriate environment variable file env/sandbox/sandbox.tfvars, env/dev/dev.tfvars or env/prod/prod.tfvars

Change the container_ver variable to the new version of your container.
Initialise terraform for the appropriate environment config file backend-dev.tfbackend or backend-prod.tfbackend run:

```bash
terraform init -backend-config=env/dev/backend-dev.tfbackend -reconfigure
```

The reconfigure options ensures that the backend state is reconfigured to point to the appropriate S3 bucket.

Please Note: This step requires an AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to be loaded into the environment if not already in place. This can be done using:

```bash
export AWS_ACCESS_KEY_ID="<aws_access_key_id>"
export AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
```

Refresh the local state to ensure it is in sync with the backend

```bash
terraform refresh -var-file=env/dev/dev.tfvars
```

Plan the changes, ensuring you use the correct environment config (depending upon which env you are configuring):

E.g. for the dev environment run

```bash
terraform plan -var-file=env/dev/dev.tfvars
```

Apply the changes, ensuring you use the correct environment config (depending upon which env you are configuring):

E.g. for the dev environment run

```bash
terraform apply -var-file=env/dev/dev.tfvars
```

When the terraform has applied successfully the running task will have been replaced by a task running the container version you specified in the tfvars file


