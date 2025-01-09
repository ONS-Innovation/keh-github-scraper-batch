import sys
import os
import json
import logging
import boto3
from github_api_toolkit import github_graphql_interface, github_interface
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

def get_repository_technologies(ql, gh, org, batch_size=30):
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
    
    while has_next_page:
        variables = {"org": org, "limit": batch_size, "cursor": cursor}
        result = ql.make_ql_request(query, variables)
        
        if not result.ok:
            logger.error(f"GraphQL query failed: {result.status_code}")
            break
            
        data = result.json()
        if "errors" in data:
            logger.error(f"GraphQL query returned errors: {data['errors']}")
            break
            
        repos = data["data"]["organization"]["repositories"]["nodes"]
        
        for repo in repos:
            try:
                # Process languages
                languages = []
                if repo["languages"]["edges"]:
                    total_size = repo["languages"]["totalSize"]
                    languages = [
                        {
                            "name": edge["node"]["name"],
                            "size": edge["size"],
                            "percentage": (edge["size"] / total_size) * 100
                        }
                        for edge in repo["languages"]["edges"]
                    ]

                repo_info = {
                    "name": repo["name"],
                    "url": repo["url"],
                    "visibility": repo["visibility"],
                    "technologies": {
                        "languages": languages
                    }
                }
                
                all_repos.append(repo_info)
                
            except Exception as e:
                logger.error(f"Error processing repository {repo.get('name', 'unknown')}: {str(e)}")

        logger.info(f"Processed {len(all_repos)} repositories")

        try:
            with open("repositories.json", "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {"repositories": []}
        
        with open("repositories.json", "w") as file:
            data["repositories"] = all_repos
            json.dump(data, file, indent=2)
            file.write("\n")
            
        page_info = data["data"]["organization"]["repositories"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]
        
    return all_repos

def main():
    """Main function to run the GitHub technology audit"""
    try:
        # Configuration
        org = os.getenv("GITHUB_ORG")
        client_id = os.getenv("GITHUB_APP_CLIENT_ID")
        secret_name = os.getenv("AWS_SECRET_NAME")
        secret_region = os.getenv("AWS_DEFAULT_REGION")
        print(org, client_id, secret_name, secret_region)
        
        logger.info("Starting GitHub technology audit")
        
        # Set up AWS session
        session = boto3.Session()
        secret_manager = session.client("secretsmanager", region_name=secret_region)
        
        # Get GitHub token
        logger.info("Getting GitHub token from AWS Secrets Manager")
        secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]
        
        token = github_api_toolkit.get_token_as_installation(org, secret, client_id)
        if not token:
            logger.error("Error getting GitHub token")
            return {"statusCode": 500, "body": json.dumps("Failed to get GitHub token")}
            
        logger.info("Successfully obtained GitHub token")
        ql = github_graphql_interface(str(token[0]))
        gh = github_interface(str(token[0]))
        
        # Get repository technology information
        repos = get_repository_technologies(ql, gh, org)
        
        # Print or save results
        output = {
            "message": "Successfully analyzed repository technologies",
            "repository_count": len(repos),
            "repositories": repos
        }
        
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")

if __name__ == "__main__":
    main()
