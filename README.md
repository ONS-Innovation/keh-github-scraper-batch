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
export ENVIRONMENT=<development/production>
```

- The source_bucket is the S3 bucket that will store the output of the script.
- The source_key is the key of the file that will store the output of the script.
- The batch_size is the number of repositories that will be scraped in each batch.
- The environment determines where to save the results. Development: locally, Production: to S3

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

### Deployments with Concourse

#### Allowlisting your IP
To setup the deployment pipeline with concourse, you must first allowlist your IP address on the Concourse
server. IP addresses are flushed everyday at 00:00 so this must be done at the beginning of every working day
whenever the deployment pipeline needs to be used. Follow the instructions on the Confluence page (SDP Homepage > SDP Concourse > Concourse Login) to
login. All our pipelines run on sdp-pipeline-prod, whereas sdp-pipeline-dev is the account used for
changes to Concourse instance itself. Make sure to export all necessary environment variables from sdp-pipeline-prod (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN).

#### Setting up a pipeline
When setting up our pipelines, we use ecs-infra-user on sdp-dev to be able to interact with our infrastructure on AWS. The credentials for this are stored on
AWS Secrets Manager so you do not need to set up anything yourself.

To set the pipeline, run the following script:
```bash
chmod u+x ./concourse/scripts/set_pipeline.sh
./concourse/scripts/set_pipeline.sh github-scraper
```
Note that you only have to run chmod the first time running the script in order to give permissions.
This script will set the branch and pipeline name to whatever branch you are currently on. It will also set the image tag on ECR to the current commit hash at the time of setting the pipeline.

The pipeline name itself will usually follow a pattern as follows: `<repo-name>-<branch-name>`
If you wish to set a pipeline for another branch without checking out, you can run the following:
```bash
./concourse/scripts/set_pipeline.sh github-scraper <branch_name>
```

If the branch you are deploying is "main" or "master", it will trigger a deployment to the sdp-prod environment. To set the ECR image tag, you must draft a Github release pointing to the latest release of the main/master branch that has a tag in the form of vX.Y.Z. Drafting up a release will automatically deploy the latest version of the main/master branch with the associated release tag, but you can also manually trigger a build through the Concourse UI or the terminal prompt.

#### Triggering a pipeline
Once the pipeline has been set, you can manually trigger a build on the Concourse UI, or run the following command:
```bash
fly -t aws-sdp trigger-job -j github-scraper-<branch-name>/build-and-push
```