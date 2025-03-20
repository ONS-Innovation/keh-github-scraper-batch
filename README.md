# GitHub Scraper Batch

A Python script that scrapes GitHub repositories and saves the data to an S3 bucket. This repository utilises the scheduled batch module to deploy the service as a batch job on AWS. 

This project utilises the [GitHub API Package](https://github.com/ONS-Innovation/github-api-package) GraphQL interface to get data from GitHub.

The script is run from the command line using the following command:

### Prerequisites:

- Python 3.10+
- Poetry
- AWS CLI
- Make

### Getting started

Setup:
```bash
make install
```

Export AWS environment variables:
```bash
export AWS_ACCESS_KEY_ID=<KEY>
export AWS_SECRET_ACCESS_KEY=<SECRET>
export AWS_DEFAULT_REGION=<REGION>
export AWS_SECRET_NAME=/<env>/github-tooling-suite/<onsdigital/ons-innovation>
```

Export GitHub environment variables:
```bash
export GITHUB_APP_CLIENT_ID=<CLIENT_ID>
export GITHUB_ORG=<onsdigital/ons-innovation>
```

Export other environment variables:
```bash
export SOURCE_BUCKET=<BUCKET_NAME>
export SOURCE_KEY=<KEY>
export BATCH_SIZE=<BATCH_SIZE>
```

- The source_bucket is the S3 bucket that will store the output of the script.
- The source_key is the key of the file that will store the output of the script.
- The batch_size is the number of repositories that will be scraped in each batch.

Run:
```bash
make run
```

### Linting and formatting

Install dev dependencies:
```bash
make install-dev
```

Run lint command:
```bash
make lint
```

Run ruff check:
```bash
make ruff
```

Run pylint:
```bash
make pylint
```

Run black:
```bash
make black
```

## Setting up Concourse Pipeline

Pipelines for our build and deployment steps are built using Concourse. To setup the pipelines, first head to this Confluence page on steps to add your IP to the allowlist and login to the Concourse server. This assumes that you have access to sdp-pipeline-prod. 

Once you have allowlisted your IP and logged in, we can start setting up the pipeline. Make sure to unset any previous AWS credentials in the current terminal session.

First export relevant environment variables for the ECR repository that we want to push to:
```bash
export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
```

We then want to retrieve our password to login to ECR:
```bash
REGISTRY_PASSWORD=`aws ecr get-login-password` && export REGISTRY_PASSWORD
```
We can then setup our pipeline
```bash
fly -t aws-sdp set-pipeline -p hello-world \
  -c concourse/ci.yml \
  --var image-repo-name=<AWS_ACCOUNT_ID>.dkr.ecr.eu-west-2.amazonaws.com/sdp-dev-github-scraper \
  --var registry-username=AWS \
  --var registry-password=$REGISTRY_PASSWORD \
  —var AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID> \
  —var AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY> \
  -var "aws_region=((aws_region))" \
  -var "aws_account_id=((aws_account_id))" \
  -var "aws_access_key_id=((aws_access_key_id))" \
  -var "aws_secret_access_key=((aws_secret_access_key))" \
  -var "aws_bucket_name=((aws_bucket_name))" \
  -var "domain=((domain))" \
  -var "container_ver=((container_ver))" \
  -var "source_bucket=((source_bucket))" \
```
To unpause the pipeline, you can either manually unpause in the Concourse UI or run the following
```bash
fly -t aws-sdp unpause-pipeline -p hello-world
```

Builds are triggered when commits are pushed into the branch. You can also trigger builds manually through the UI or with the following command:
```bash
fly -t aws-sdp trigger-job -j hello-world/build-and-push
```
