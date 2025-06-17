set -euo pipefail

apk add --no-cache aws-cli jq

aws_account_id=$(echo "$github_scraper_secrets" | jq -r .aws_account_id)
aws_access_key_id=$(echo "$github_scraper_secrets" | jq -r .aws_access_key_id)

aws_secret_access_key=$(echo "$github_scraper_secrets" | jq -r .aws_secret_access_key)
domain=$(echo "$github_scraper_secrets" | jq -r .domain)

source_bucket=$(echo "$github_scraper_secrets" | jq -r .source_bucket)
source_key=$(echo "$github_scraper_secrets" | jq -r .source_key)

github_app_client_id=$(echo "$github_scraper_secrets" | jq -r .github_app_client_id)
aws_secret_name=$(echo "$github_scraper_secrets" | jq -r .aws_secret_name)

github_org=$(echo "$github_scraper_secrets" | jq -r .github_org)
container_image=$(echo "$github_scraper_secrets" | jq -r .container_image)

batch_size=$(echo "$github_scraper_secrets" | jq -r .batch_size)

export AWS_ACCESS_KEY_ID=$aws_access_key_id
export AWS_SECRET_ACCESS_KEY=$aws_secret_access_key

git config --global url."https://x-access-token:$github_access_token@github.com/".insteadOf "https://github.com/"

if [[ ${env} != "prod" ]]; then
    env="dev"
fi

aws sts get-caller-identity --output=json

cd resource-repo/terraform/batch
terraform init -backend-config=env/${env}/backend-${env}.tfbackend -reconfigure
terraform apply \
-var "aws_account_id=$aws_account_id" \
-var "aws_access_key_id=$aws_access_key_id" \
-var "aws_secret_access_key=$aws_secret_access_key" \
-var "domain=$domain" \
-var "container_ver=${tag}" \
-var "source_bucket=$source_bucket" \
-var "source_key=$source_key" \
-var "github_app_client_id=$github_app_client_id" \
-var "aws_secret_name=$aws_secret_name" \
-var "github_org=$github_org" \
-var "batch_size=$batch_size" \
-auto-approve