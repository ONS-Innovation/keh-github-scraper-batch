resource "aws_cloudwatch_event_rule" "batch_trigger" {
  name                = "${var.domain}-${var.service_subdomain}-batch-trigger"
  description         = "Triggers ${var.domain}-${var.service_subdomain} Batch Job"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "batch_target" {
  rule      = aws_cloudwatch_event_rule.batch_trigger.name
  target_id = "${var.domain}-${var.service_subdomain}-batch"
  arn       = aws_batch_job_queue.github_scraper.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  batch_target {
    job_definition = aws_batch_job_definition.github_scraper.arn
    job_name       = "${var.domain}-${var.service_subdomain}-job"
  }
}

# IAM role for EventBridge to submit Batch jobs
resource "aws_iam_role" "eventbridge_role" {
  name = "${var.domain}-${var.service_subdomain}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for EventBridge to submit Batch jobs
resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.domain}-${var.service_subdomain}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "batch:SubmitJob"
        ]
        Resource = [
          aws_batch_job_definition.github_scraper.arn,
          aws_batch_job_queue.github_scraper.arn
        ]
      }
    ]
  })
}
