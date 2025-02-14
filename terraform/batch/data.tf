
# Remote state for VPC
data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = {
    bucket = "sdp-dev-tf-state"
    key    = "sdp-dev-ecs-infra/terraform.tfstate"
    region = "eu-west-2"
  }
}
