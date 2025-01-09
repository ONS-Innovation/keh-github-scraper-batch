import sys
import os
import json
import logging
import datetime
import boto3
from github_api_toolkit import github_graphql_interface
import github_api_toolkit

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear any existing handlers
for handler in logger.handlers:
    logger.removeHandler(handler)

# Add stdout handler
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(stdout_handler)


def get_repository_technologies(ql, org, batch_size=30):
    """Gets technology information for all repositories in an organization"""

    query = """
    query($org: String!, $limit: Int!, $cursor: String) {
      organization(login: $org) {
        repositories(first: $limit, after: $cursor, isArchived: false) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            url
            visibility
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
          }
        }
      }
    }
    """

    has_next_page = True
    cursor = None
    all_repos = []

    # Statistics tracking
    total_repos = 0
    private_repos = 0
    public_repos = 0
    internal_repos = 0
    language_stats = {}

    while has_next_page:
        variables = {"org": org, "limit": batch_size, "cursor": cursor}
        result = ql.make_ql_request(query, variables)

        if not result.ok:
            logger.error("GraphQL query failed: {}", result.status_code)
            break

        data = result.json()
        if "errors" in data:
            logger.error("GraphQL query returned errors: {}", data['errors'])
            break

        repos = data["data"]["organization"]["repositories"]["nodes"]

        for repo in repos:
            try:
                # Count repository visibility
                total_repos += 1
                if repo["visibility"] == "PRIVATE":
                    private_repos += 1
                elif repo["visibility"] == "PUBLIC":
                    public_repos += 1
                elif repo["visibility"] == "INTERNAL":
                    internal_repos += 1

                # Process languages
                languages = []
                if repo["languages"]["edges"]:
                    total_size = repo["languages"]["totalSize"]
                    for edge in repo["languages"]["edges"]:
                        lang_name = edge["node"]["name"]
                        percentage = (edge["size"] / total_size) * 100

                        # Update language statistics
                        if lang_name not in language_stats:
                            language_stats[lang_name] = {
                                "repo_count": 0,
                                "total_percentage": 0,
                                "total_lines": 0,
                            }
                        language_stats[lang_name]["repo_count"] += 1
                        language_stats[lang_name]["total_percentage"] += percentage
                        language_stats[lang_name]["total_lines"] += edge["size"]

                        languages.append(
                            {
                                "name": lang_name,
                                "size": edge["size"],
                                "percentage": percentage,
                            }
                        )

                repo_info = {
                    "name": repo["name"],
                    "url": repo["url"],
                    "visibility": repo["visibility"],
                    "technologies": {"languages": languages},
                }

                all_repos.append(repo_info)

            except Exception as e:
                logger.error(
                    "Error processing repository {}: {}".format(
                        repo.get("name", "unknown"), str(e)
                    )
                )

        logger.info("Processed {} repositories".format(len(all_repos)))

        page_info = data["data"]["organization"]["repositories"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]

    # Calculate language averages
    language_averages = {}
    for lang, stats in language_stats.items():
        language_averages[lang] = {
            "repo_count": stats["repo_count"],
            "average_percentage": round(
                stats["total_percentage"] / stats["repo_count"], 3
            ),
            "average_lines": round(stats["total_lines"] / stats["repo_count"], 3),
        }

    # Create final output
    output = {
        "repositories": all_repos,
        "stats": {
            "total_repos": total_repos,
            "total_private_repos": private_repos,
            "total_public_repos": public_repos,
            "total_internal_repos": internal_repos,
        },
        "language_statistics": language_averages,
        "metadata": {"last_updated": datetime.datetime.now().strftime("%Y-%m-%d")},
    }

    # Write everything to file at once
    with open("repositories.json", "w") as file:
        json.dump(output, file, indent=2)
        file.write("\n")

    return all_repos


def main():
    """Main function to run the GitHub technology audit"""
    try:
        # Configuration
        org = os.getenv("GITHUB_ORG")
        client_id = os.getenv("GITHUB_APP_CLIENT_ID")
        secret_name = os.getenv("AWS_SECRET_NAME")
        secret_region = os.getenv("AWS_DEFAULT_REGION")

        logger.info("Starting GitHub technology audit")

        # Set up AWS session
        session = boto3.Session()
        secret_manager = session.client("secretsmanager", region_name=secret_region)

        # Get GitHub token
        logger.info("Getting GitHub token from AWS Secrets Manager")
        secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

        token = github_api_toolkit.get_token_as_installation(org, secret, client_id)
        if not token:
            logger.error('Error getting GitHub token')
            return {"statusCode": 500, "body": json.dumps("Failed to get GitHub token")}

        logger.info("Successfully obtained GitHub token")
        ql = github_graphql_interface(str(token[0]))

        # Get repository technology information
        repos = get_repository_technologies(ql, org)

        # Print or save results
        output = {
            "message": "Successfully analyzed repository technologies",
            "repository_count": len(repos),
            "repositories": repos,
        }

        logger.info("Results: %s", output)

    except Exception as e:
        logger.error("Execution failed: %s", str(e))


if __name__ == "__main__":
    main()
