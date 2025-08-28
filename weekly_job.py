from utils.scraper import get_trending_repos
from utils.processor import process_repositories
import json
from datetime import datetime
import os
import shutil

def weekly_job():
    trending_repos = get_trending_repos()
    
    results = process_repositories(trending_repos)
    
    filename = f"trending_report_{datetime.now().strftime('%Y%m%d')}.json"
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Weekly job completed. Report saved as {filename}")

    process_report_by_domain(filepath)

    send_email_report(filepath)

def send_email_report(filepath):
    print(f"Email report would be sent using: {filepath}")
    pass

def process_report_by_domain(input_filepath):
    """
    Processes the generated report, grouping tasks by domain into separate JSON files.
    """
    try:
        with open(input_filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_filepath}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_filepath}")
        return

    for repo_data in data:
        task = repo_data.get("task")
        if not task:
            continue

        domain = task.get("domain", "misc")
        domain = "".join(c for c in domain if c.isalnum() or c in (' ', '.', '_')).strip()
        domain = domain.replace(" ", "_")

        title = task.get("title", "untitled").replace(" ", "_").replace("/", "_")
        
        domain_dir = os.path.join(os.path.dirname(input_filepath), domain)
        os.makedirs(domain_dir, exist_ok=True)

        filename = f"{title}.json"
        output_filepath = os.path.join(domain_dir, filename)

        with open(output_filepath, 'w') as out_f:
            json.dump(task, out_f, indent=2)

    print("Tasks successfully grouped by domain.")

if __name__ == "__main__":
    weekly_job()