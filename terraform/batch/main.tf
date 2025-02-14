# Compute Environment
resource "aws_batch_compute_environment" "github_scraper" {
  compute_environment_name = "${var.domain}-${var.service_subdomain}-compute-env"

  compute_resources {
    max_vcpus = 16
    min_vcpus = 0

    security_group_ids = [aws_security_group.batch_sg.id]
    subnets            = data.terraform_remote_state.vpc.outputs.private_subnets
    type               = "FARGATE"
  }

  service_role = aws_iam_role.batch_service_role.arn
  type         = "MANAGED"
  state        = "ENABLED"

  depends_on = [aws_iam_role_policy_attachment.batch_service_role]
}

# Job Queue
resource "aws_batch_job_queue" "github_scraper" {
  name     = "${var.domain}-${var.service_subdomain}-job-queue"
  state    = "ENABLED"
  priority = 1
  scheduling_policy_arn = null

  compute_environment_order {
    compute_environment = aws_batch_compute_environment.github_scraper.arn
    order = 1
  }
}

# Job Definition
resource "aws_batch_job_definition" "github_scraper" {
  name = "${var.domain}-${var.service_subdomain}-job-def"
  type = "container"
  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image = "${var.aws_account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_repository_name}:${var.container_ver}"
    
    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }
    
    resourceRequirements = [
      {
        type  = "VCPU"
        value = "1"
      },
      {
        type  = "MEMORY"
        value = "2048"
      }
    ]

    environment = [
      {
        name  = "SOURCE_BUCKET"
        value = var.source_bucket
      },
      {
        name  = "SOURCE_KEY"
        value = var.source_key
      },
      {
        name  = "GITHUB_APP_CLIENT_ID"
        value = var.github_app_client_id
      },
      {
        name  = "AWS_SECRET_NAME"
        value = var.aws_secret_name
      },
      {
        name  = "GITHUB_ORG"
        value = var.github_org
      },
      {
        name  = "BATCH_SIZE"
        value = tostring(var.batch_size)
      }
    ]

    networkConfiguration = {
      assignPublicIp = "DISABLED"
    }

    executionRoleArn = aws_iam_role.batch_execution_role.arn
    jobRoleArn       = aws_iam_role.batch_job_role.arn
  })
}

# Security Group
resource "aws_security_group" "batch_sg" {
  name        = "${var.domain}-${var.service_subdomain}-batch-sg"
  description = "Security group for Batch compute environment"
  vpc_id      = data.terraform_remote_state.vpc.outputs.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.domain}-${var.service_subdomain}-batch-sg"
  }
}
