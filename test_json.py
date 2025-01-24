import sys
import os
import json
import logging
import datetime
import boto3
from github_api_toolkit import github_graphql_interface, get_token_as_installation


def get_repository_technologies(ql, org, batch_size=30):
    query = """
    query($org: String!, $limit: Int!, $cursor: String) {
      organization(login: $org) {
        repositories(first: $limit, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            url
            visibility
            isArchived
            defaultBranchRef {
              target {
                ... on Commit {
                  committedDate
                  history(first: 1) {
                    nodes {
                      committedDate
                    }
                  }
                }
              }
            }
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
              totalSize
            }
            object(expression: "HEAD:") {
          ... on Tree {
            entries {
              name
              type
              object {
                ... on Blob {
                    text
                }
                ... on Tree {
                    entries {
                        name
                        type
                    }
                }
              }
            }
          }
        }
          }
        }
      }
    }
    """
    cursor = None
    variables = {"org": org, "limit": batch_size, "cursor": cursor}
    result = ql.make_ql_request(query, variables)

    if not result.ok:
        print("GraphQL query failed: {}", result.status_code)
        return ""

    data = result.json()
    print(json.dumps(data, indent=4))
    return data

def main():
    """Main function to run the GitHub technology audit"""
    # Configuration
    org = os.getenv("GITHUB_ORG")
    client_id = os.getenv("GITHUB_APP_CLIENT_ID")
    secret_name = os.getenv("AWS_SECRET_NAME")
    secret_region = os.getenv("AWS_DEFAULT_REGION")

    print("Starting GitHub technology audit")

    # Set up AWS session
    session = boto3.Session()
    secret_manager = session.client("secretsmanager", region_name=secret_region)

    # Get GitHub token
    print("Getting GitHub token from AWS Secrets Manager")
    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    token = get_token_as_installation(org, secret, client_id)
    if not token:
        print('Error getting GitHub token')
        return {"statusCode": 500, "body": json.dumps("Failed to get GitHub token")}

    print("Successfully obtained GitHub token")
    ql = github_graphql_interface(str(token[0]))

    # Get repository technology information
    repos = get_repository_technologies(ql, org)

    with open("jsontest.json", "w") as f:
        json.dump(repos, f, indent=4)

    # Print or save results
    """
    output = {
        "message": "Successfully analyzed repository technologies",
        "repository_count": len(repos),
        "repositories": repos,
    }
    """


if __name__ == "__main__":
    main()
