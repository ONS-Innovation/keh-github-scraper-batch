"""GitHub Scraper Script

This script performs a comprehensive technology audit of GitHub repositories within an organization.
It collects information about programming languages, infrastructure as code (IaC) usage,
repository visibility, archival status, and activity metrics.

The script:
- Authenticates with GitHub using an installation token from AWS Secrets Manager
- Queries repository data via GitHub's GraphQL API
- Analyzes language usage and calculates statistics
- Tracks repository activity over different time periods
- Outputs results to a JSON file with repository details and aggregated metrics

Environment Variables Required:
    GITHUB_ORG: GitHub organization name
    GITHUB_APP_CLIENT_ID: GitHub App client ID
    AWS_SECRET_NAME: Name of AWS secret containing GitHub credentials
    AWS_DEFAULT_REGION: AWS region for Secrets Manager
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key

Output:
    repositories.json: Contains detailed repository data and statistics
"""

import sys
import os
import json
import logging
import datetime
import boto3
import time
from requests.exceptions import ChunkedEncodingError, RequestException
from github_api_toolkit import github_graphql_interface, get_token_as_installation

KEYWORDS_FILE = {
    "keywords": {
        "documentation": ["Confluence", "MKDocs", "Sphinx", "ReadTheDocs"],
        "cloud_services": ["AWS", "Azure", "GCP"],
        "frameworks": ["React", "Angular", "Vue", "Django", "Streamlit", "Flask", "Spring", "Hibernate", "Express", "Next.js", "Play", "Akka", "Lagom"],
        "ci_cd": ["Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "Travis CI", "Azure DevOps", "Concourse"]
    }
}

MAX_RETRIES = int(os.getenv("MAX_RETRIES", 5))

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

def make_request_with_retry(ql, query, variables):
    """Make a GraphQL request with retry logic

    Args:
        ql: GraphQL client
        query (str): GraphQL query
        variables (dict): Query variables

    Returns:
        requests.Response: The API response
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = ql.make_ql_request(query, variables)
            if result.ok:
                return result
            else:
                logger.warning(f"Request failed with status {result.status_code}, attempt {attempt + 1} of {MAX_RETRIES}")
            
        except (ChunkedEncodingError, RequestException) as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Final retry attempt failed: {str(e)}")
                raise
            
            logger.warning(f"Request failed with error: {str(e)}, attempt {attempt + 1} of {MAX_RETRIES}")
        
        # Exponential backoff
        delay = 2 ** attempt
        logger.info(f"Waiting {delay} seconds before retrying...")
        time.sleep(delay)
    
    raise Exception(f"Failed after {MAX_RETRIES} attempts")

def find_keywords_in_file(file, keywords_list):
    """Find keywords in a file

    Args:
        file (str): File contents that you are interested in searching
        keywords_list (list): List of keywords that you want to search through the file

    Returns:
        list: List of keywords that were found in the file
    """    
    keywords = []
    if file is None:
        return []

    for keyword in keywords_list:
        if (keyword.lower() in file.lower()) and (keyword.lower() not in keywords):
            keywords.append(keyword)
    return keywords

def get_repository_technologies(ql, org, batch_size=5):
    """Get technology information for all repositories in an organization

    Args:
        ql (github_graphql_interface): GraphQL interface object
        org (str): GitHub organization name
        batch_size (int, optional): How many respositories to be processed in one request. Defaults to 5.

    Returns:
        list: List of repositories
    """    

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

    has_next_page = True
    cursor = None
    all_repos = []
    # test CI

    # Statistics tracking
    total_repos = 0
    private_repos = 0
    public_repos = 0
    internal_repos = 0
    archived_repos = 0
    archived_private = 0
    archived_public = 0
    archived_internal = 0
    language_stats = {}
    archived_language_stats = {}  # New dictionary for archived repos
                    
    while has_next_page:
        variables = {"org": org, "limit": batch_size, "cursor": cursor}
        
        try:
            result = make_request_with_retry(ql, query, variables)
            data = result.json()
            
            if "errors" in data:
                logger.error(f"GraphQL query returned errors: {data['errors']}")
                break

            repos = data["data"]["organization"]["repositories"]["nodes"]

            for repo in repos:
                try:
                    # Count repository visibility
                    total_repos += 1
                    is_archived = repo.get("isArchived", False)

                    if is_archived:
                        archived_repos += 1
                        if repo["visibility"] == "PRIVATE":
                            archived_private += 1
                        elif repo["visibility"] == "PUBLIC":
                            archived_public += 1
                        elif repo["visibility"] == "INTERNAL":
                            archived_internal += 1

                    if repo["visibility"] == "PRIVATE":
                        private_repos += 1
                    elif repo["visibility"] == "PUBLIC":
                        public_repos += 1
                    elif repo["visibility"] == "INTERNAL":
                        internal_repos += 1

                    # Get last commit date
                    last_commit_date = None
                    if repo.get("defaultBranchRef") and repo["defaultBranchRef"].get(
                        "target"
                    ):
                        last_commit_date = repo["defaultBranchRef"]["target"].get(
                            "committedDate"
                        )

                    # Process languages
                    languages = []
                    IAC = []
                    if repo["languages"]["edges"]:
                        total_size = repo["languages"]["totalSize"]
                        for edge in repo["languages"]["edges"]:
                            lang_name = edge["node"]["name"]
                            if lang_name == "HCL":
                                IAC.append("Terraform")
                            if lang_name == "Dockerfile":
                                IAC.append("Docker")
                            percentage = (edge["size"] / total_size) * 100

                            # Choose which statistics dictionary to update based on archive status
                            stats_dict = (
                                archived_language_stats if is_archived else language_stats
                            )

                            # Update language statistics
                            if lang_name not in stats_dict:
                                stats_dict[lang_name] = {
                                    "repo_count": 0,
                                    "average_percentage": 0,
                                    "total_size": 0,
                                }
                            stats_dict[lang_name]["repo_count"] += 1
                            stats_dict[lang_name]["average_percentage"] += percentage
                            stats_dict[lang_name]["total_size"] += edge["size"]

                            languages.append(
                                {
                                    "name": lang_name,
                                    "size": edge["size"],
                                    "percentage": percentage,
                                }
                            )

                    documentation_list = KEYWORDS_FILE["keywords"]["documentation"]
                    cloud_services_list = KEYWORDS_FILE["keywords"]["cloud_services"]
                    frameworks_list = KEYWORDS_FILE["keywords"]["frameworks"]
                    ci_cd = []
                    docs = []
                    cloud = []
                    if repo["object"] is not None:
                        # json.dump(repo["object"]["entries"], file, indent=4)
                        # repo["object"]["entries"] is a LIST of dictionaries
                        # Get README content
                        readme_content = pyproject_content = package_json_content = None
                        if repo["object"]["entries"]:
                            for entry in repo["object"]["entries"]:
                                if entry["name"].lower() == "readme.md":
                                    readme_content = entry["object"]["text"]
                                if entry["name"].lower() == "pyproject.toml":
                                    pyproject_content = entry["object"]["text"]
                        
                        frameworks_pyproject = find_keywords_in_file(pyproject_content, frameworks_list)
                        frameworks_package_json = find_keywords_in_file(package_json_content, frameworks_list)
                        frameworks = frameworks_pyproject + frameworks_package_json
                        # Check if "confluence" is present in README
                        if readme_content is not None:
                            for doc, cl in zip(documentation_list, cloud_services_list):
                                if doc.lower() in readme_content.lower():
                                    docs.append(doc)
                                if cl.lower() in readme_content.lower():
                                    cloud.append(cl)
                        
                        # TODO: Extremely hardcoded, will need to write a general tree traversal to find things in all directories
                        if repo["object"]["entries"]:
                            for entry in repo["object"]["entries"]:
                                if entry["name"] == ".github":
                                    if entry["object"]["entries"]:
                                        for gh_entry in entry["object"]["entries"]:
                                            if gh_entry["name"] == "workflows":
                                                ci_cd.append("GitHub Actions")
                                                break
                                if entry["name"] == "ci":
                                    if entry["object"]["entries"]:
                                        for ci_entry in entry["object"]["entries"]:
                                            if "pipeline.yml" in ci_entry["name"]:
                                                ci_cd.append("Concourse")
                                                break

                    repo_info = {
                        "name": repo["name"],
                        "url": repo["url"],
                        "visibility": repo["visibility"],
                        "is_archived": is_archived,
                        "last_commit": last_commit_date,
                        "technologies": {
                                        "languages": languages, 
                                        "IAC": IAC, 
                                        "docs": docs, "cloud": cloud, 
                                        "frameworks": frameworks, 
                                        "ci_cd": ci_cd
                                    },
                        }

                    all_repos.append(repo_info)

                except Exception as e:
                    logger.error(
                        f"Error processing repository {repo.get('name', 'unknown')}: {str(e)}"
                    )
                    continue

            logger.info(f"Processed {len(all_repos)} repositories")

            page_info = data["data"]["organization"]["repositories"]["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"]

        except Exception as e:
            logger.error(f"Error fetching repositories: {str(e)}")
            # If we hit an unrecoverable error, save what we have so far
            break

    # Calculate language averages for non-archived repos
    language_averages = {}
    for lang, stats in language_stats.items():
        language_averages[lang] = {
            "repo_count": stats["repo_count"],
            "average_percentage": round(
                stats["average_percentage"] / stats["repo_count"], 3
            ),
            "total_size": stats["total_size"],
        }

    # Calculate language averages for archived repos
    archived_language_averages = {}
    for lang, stats in archived_language_stats.items():
        archived_language_averages[lang] = {
            "repo_count": stats["repo_count"],
            "average_percentage": round(
                stats["average_percentage"] / stats["repo_count"], 3
            ),
            "total_size": stats["total_size"],
        }

    # Create final output
    output = {
        "repositories": all_repos,
        "stats_unarchived": {
            "total": total_repos - archived_repos,
            "private": private_repos - archived_private,
            "public": public_repos - archived_public,
            "internal": internal_repos - archived_internal,
            "active_last_month": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and not repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 30
            ),
            "active_last_3months": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and not repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 90
            ),
            "active_last_6months": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and not repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 180
            ),
        },
        "stats_archived": {
            "total": archived_repos,
            "private": archived_private,
            "public": archived_public,
            "internal": archived_internal,
            "active_last_month": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 30
            ),
            "active_last_3months": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 90
            ),
            "active_last_6months": sum(
                1
                for repo in all_repos
                if repo["last_commit"]
                and repo["is_archived"]
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime.fromisoformat(
                        repo["last_commit"].replace("Z", "+00:00")
                    )
                ).days
                <= 180
            ),
        },
        "language_statistics_unarchived": language_averages,
        "language_statistics_archived": archived_language_averages,
        "metadata": {
            "last_updated": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%d"
            )
        },
    }

    return output

def get_github_client():
    """Get authenticated GitHub GraphQL client"""
    org = os.getenv("GITHUB_ORG")
    client_id = os.getenv("GITHUB_APP_CLIENT_ID")
    secret_name = os.getenv("AWS_SECRET_NAME")
    secret_region = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")

    # Set up AWS session
    session = boto3.Session()
    secret_manager = session.client("secretsmanager", region_name=secret_region)

    # Get GitHub token
    logger.info("Getting GitHub token from AWS Secrets Manager")
    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    token = get_token_as_installation(org, secret, client_id)
    if not token:
        raise Exception("Failed to get GitHub token")

    return github_graphql_interface(str(token[0])), org

def main():
    """Main entry point for the batch job"""
    try:
        logger.info("Starting GitHub repository scraper")
        
        # Get GitHub client
        ql, org = get_github_client()
        
        # Get repository data
        batch_size = int(os.getenv("BATCH_SIZE", "30"))
        logger.info(f"Processing repositories with batch size: {batch_size}")
        
        output = get_repository_technologies(ql, org, batch_size)
        
        # Save to S3
        bucket = os.getenv("SOURCE_BUCKET")
        key = os.getenv("SOURCE_KEY")
        
        logger.info(f"Saving results to S3: {bucket}/{key}")
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(output, indent=2),
            ContentType='application/json'
        )
        
        logger.info("Successfully completed repository scanning")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()