# processor.py

import os
import json
from utils.utils import clone_repo, summarize_codebase, cleanup_repo
from utils.gemini_helpers import generate_repo_insights, generate_all_difficulty_tasks

def process_repositories(repos):
    results = []
    for repo in repos:
        repo_path = None 
        try:
            repo_path = clone_repo(repo['url'])
            
            digest = summarize_codebase(repo_path)
            
            insights = generate_repo_insights(digest)
            
            tasks = generate_all_difficulty_tasks(digest, repo)
            
            repo_result = {
                'metadata': repo,
                'digest': digest[:5000] + "..." if len(digest) > 5000 else digest,
                'insights': insights,
                'tasks': tasks 
            }
            results.append(repo_result)
        except Exception as e:
            print(f"Error processing {repo['title']}: {str(e)}")
            results.append({
                'metadata': repo,
                'error': str(e)
            })
        finally:
            if repo_path:
                cleanup_repo(repo_path) 
    return results