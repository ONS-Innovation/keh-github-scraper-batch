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




