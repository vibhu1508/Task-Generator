import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime, timezone
import json
from utils.utils import remove_emojis, append_auto_helpful_links
#

load_dotenv()

def configure_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def generate_repo_insights(digest):
    try:
        configure_gemini()
        model = genai.GenerativeModel('gemini-1.5-flash')

        repo_insights_schema = {
            "type": "object",
            "properties": {
                "main_technologies": {"type": "array", "items": {"type": "string"}},
                "architecture_overview": {"type": "string"},
                "notable_patterns": {"type": "array", "items": {"type": "string"}},
                "complexity_estimate": {"type": "string", "enum": ["low", "medium", "high"]},
                "learning_opportunities": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["main_technologies", "architecture_overview", "notable_patterns", "complexity_estimate", "learning_opportunities"]
        }

        prompt = f"""
        Analyze this codebase digest and extract key insights:

        {digest[:10000]}
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "response_schema": repo_insights_schema}
        )
        text = response.text.strip()

        if not text:
            return {"error_type": "LLM_EMPTY_RESPONSE", "message": "LLM response for repo insights was empty.", "raw_response": text}

        return json.loads(text)
    except Exception as e:
        return {"error_type": "LLM_API_CALL_ERROR", "message": f"Error calling Gemini for repo insights: {e}", "raw_response": "N/A"}

def generate_job_insights(digest):
    try:
        configure_gemini()
        model = genai.GenerativeModel('gemini-1.5-flash')

        job_insights_schema = {
            "type": "object",
            "properties": {
                "main_technologies": {"type": "array", "items": {"type": "string"}},
                "required_skills": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"},
                "role_level": {"type": "string", "enum": ["junior", "mid", "senior"]},
                "common_challenges": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["main_technologies", "required_skills", "domain", "role_level", "common_challenges"]
        }

        prompt = f"""
        Analyze this job description digest and extract key insights:

        {digest[:10000]}
        """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "response_schema": job_insights_schema}
        )
        text = response.text.strip()

        if not text:
            return {"error_type": "LLM_EMPTY_RESPONSE", "message": "LLM response for job insights was empty.", "raw_response": text}

        return json.loads(text)
    except Exception as e:
        return {"error_type": "LLM_API_CALL_ERROR", "message": f"Error calling Gemini for job insights: {e}", "raw_response": "N/A"}

def generate_real_world_build_task(digest, insights_dict, difficulty_level="hard", is_repo_input=True):
    try:
        configure_gemini()
        model = genai.GenerativeModel('gemini-2.5-flash')

        difficulty_text = {
            "easy": "small, self-contained feature",
            "medium": "moderately integrated functionality",
            "hard": "complex core module or integration"
        }

        insights_str = json.dumps(insights_dict, indent=2)

        task_output_schema = {
            "type": "object",
            "properties": {
                "problem_statement": {"type": "string"},
                "proposed_solution_idea": {"type": "string"},
                "specific_build_task": {"type": "string"},
                "required_skills_for_build": {"type": "array", "items": {"type": "string"}},
                "potential_deliverables": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"},
                "task_type": {"type": "string"}
            },
            "required": ["problem_statement", "proposed_solution_idea", "specific_build_task", "required_skills_for_build", "potential_deliverables", "domain", "task_type"]
        }

        if is_repo_input:
            prompt = f"""
            You're a senior dev. Given this codebase digest:

            {digest[:7000]}

            And these codebase insights:

            {insights_str}

            Generate a real-world build task.
            Use this difficulty: {difficulty_text.get(difficulty_level, "medium")}
            """
        else: 
            prompt = f"""
            You're a senior dev. Given this job description:

            {digest[:7000]}

            And these job insights:

            {insights_str}

            Generate a real-world learning task that helps a developer acquire skills relevant to this job description.
            Focus on a {difficulty_text.get(difficulty_level, "medium")} level task.
            """

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "response_schema": task_output_schema}
        )
        text = response.text.strip()

        if not text:
            return {"error_type": "LLM_EMPTY_RESPONSE", "message": "LLM response was empty.", "raw_response": text}

        return json.loads(text)
    except Exception as e:
        return {"error_type": "LLM_API_CALL_ERROR", "message": str(e), "raw_response": "N/A"}

def extract_technologies_from_digest(digest, is_repo_input=True):
    try:
        configure_gemini()
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        tech_extract_schema = {
            "type": "array",
            "items": {"type": "string"}
        }

        if is_repo_input:
            prompt = f"""
            Extract technologies/libraries used in this codebase digest.
            """
        else:
            prompt = f"""
            Extract key technologies, languages, and tools mentioned in this job description.
            """
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "response_schema": tech_extract_schema}
        )
        text = response.text.strip()

        if not text:
            return {"error_type": "LLM_EMPTY_RESPONSE", "message": "LLM response for tech extraction was empty.", "raw_response": text}

        return json.loads(text)
    except Exception as e:
        print(f"[Tech Extract Error] {e}")
        return []

def generate_learning_task(digest, repo, difficulty_level="medium"):
    now_utc = datetime.now(timezone.utc).isoformat()
    
    is_repo_input = (repo.get('url') != "N/A") 
    
    if is_repo_input:
        intro = f"### Task Overview\nDevelop a new product feature for **{repo['title']}**."
        has_readme = "## README.md" in digest
        if has_readme:
            intro += "\nThis repository has a README.md for reference."
        else:
            intro += "\nThis repository lacks a README.md."
    else: 
        intro = f"### Task Overview\nBased on the job description for **{repo['title']}** at **{repo.get('company', 'N/A')}**."
        intro += "\nThis task is designed to help you acquire skills relevant to this job description."

    insights = {}
    if is_repo_input:
        insights = generate_repo_insights(digest)
        if "error_type" in insights:
            print(f"[Repo Insights Error] {insights['message']}")
            insights = {"main_technologies": [], "architecture_overview": "", "notable_patterns": [], "complexity_estimate": "unknown", "learning_opportunities": []}
    else:
        insights = generate_job_insights(digest)
        if "error_type" in insights:
            print(f"[Job Insights Error] {insights['message']}")
            insights = {"main_technologies": [], "required_skills": [], "domain": "unknown", "role_level": "unknown", "common_challenges": []}

    task_info = generate_real_world_build_task(digest, insights, difficulty_level, is_repo_input) 

    config = {
        "title_suffix": " (Feature Build)" if is_repo_input else " (Learning Task)",
        "duration_hours": {"easy": 8, "medium": 16, "hard": 24}[difficulty_level],
        "difficulty": difficulty_level, 
        "task_type": "product-development-task" if is_repo_input else "learning-task",
        "inferred_domain": insights.get("domain", "software-development"), 
        "skills": [], 
        "tools": [], 
        "datasets": [] 
    }

    techs_from_digest = extract_technologies_from_digest(digest, is_repo_input)
    
    for tech in techs_from_digest:
        if {"name": tech, "subskills": []} not in config['skills']:
            config['skills'].append({"name": tech, "subskills": []})
        if {"name": tech, "type": "technology", "proficiency_level": "intermediate"} not in config['tools']:
            config['tools'].append({"name": tech, "type": "technology", "proficiency_level": "intermediate"})

    if is_repo_input:
        for tech in insights.get("main_technologies", []):
            if {"name": tech, "subskills": []} not in config['skills']:
                config['skills'].append({"name": tech, "subskills": []})
            if {"name": tech, "type": "technology", "proficiency_level": "intermediate"} not in config['tools']:
                config['tools'].append({"name": tech, "type": "technology", "proficiency_level": "intermediate"})
        
        if repo['language'] != "N/A":
            lang_lower = repo['language'].lower()
            if {"name": lang_lower, "subskills": []} not in config['skills']:
                config['skills'].append({"name": lang_lower, "subskills": []})
            if {"name": lang_lower, "type": "language", "proficiency_level": "intermediate"} not in config['tools']:
                config['tools'].append({"name": lang_lower, "type": "language", "proficiency_level": "intermediate"})
    else:
        for skill in insights.get("required_skills", []):
            if {"name": skill, "subskills": []} not in config['skills']:
                config['skills'].append({"name": skill, "subskills": []})
        for tech in insights.get("main_technologies", []):
            if {"name": tech, "type": "technology", "proficiency_level": "intermediate"} not in config['tools']:
                config['tools'].append({"name": tech, "type": "technology", "proficiency_level": "intermediate"})

    if "error_type" in task_info:
        if is_repo_input:
            config['description_intro'] = f"Could not auto-generate task: {task_info['message']}. Create a small improvement feature in {repo['language']}."
        else:
            config['description_intro'] = f"Could not auto-generate task: {task_info['message']}. Create a small learning project related to {repo['title']}."
        config['goals'] = ["- Build a new utility function or module."]
        config['deliverables'] = ["- Working code", "- Tests", "- Documentation"]
        if {"name": "general dev", "subskills": []} not in config['skills']:
            config['skills'].append({"name": "general dev", "subskills": []})
    else:
        config['description_intro'] = f"**Problem:** {task_info['problem_statement']}\n\n**Solution Idea:** {task_info['proposed_solution_idea']}"
        config['goals'] = [f"- {task_info['specific_build_task']}"]
        config['deliverables'] = [f"- {d}" for d in task_info['potential_deliverables']]
        for s in task_info['required_skills_for_build']:
            if {"name": s, "subskills": []} not in config['skills']:
                config['skills'].append({"name": s, "subskills": []})
        config['inferred_domain'] = task_info.get("domain", config['inferred_domain']) 
        config['task_type'] = task_info.get("task_type", config['task_type'])

    description_resources = ""
    if is_repo_input:
        description_resources = "\n\n### Resources\n" + f"- Repository: {repo['url']}" + \
                                ("\n- README included in digest" if has_readme else "")
    else:
        description_resources = "\n\n### Resources\n" + f"- Original Job Posting: {repo.get('url', 'N/A')}" + \
                                f"\n- Job Source: {repo.get('source', 'N/A')}"

    description = (
        intro +
        f"\n\n{config['description_intro']}\n\n" +
        "### Build Task\n" + "\n".join(config['goals']) +
        description_resources
    )

    helpful_links = append_auto_helpful_links(techs_from_digest) 
    description += helpful_links  
    description += "\n\n### Deliverables\n" + "\n".join(config['deliverables'])
    description += "\n\n### Next Steps\n- Open a Pull Request if relevant."

    final_task = {
        "task_id": str(uuid.uuid4()),
        "title": f"Build: {repo['title']}{config['title_suffix']}",
        "description": remove_emojis(description),
        "domain": config['inferred_domain'],
        "task_type": config['task_type'],
        "difficulty": config['difficulty'], 
        "duration_hours": config['duration_hours'],
        "skills": config['skills'],
        "tools": config['tools'],
        "datasets": config['datasets'],
        "real_world_mapping": {
            "source": "github" if is_repo_input else "job-description",
            "source_url": repo["url"] if is_repo_input else "N/A",
            "source_job_url": "N/A" if is_repo_input else repo.get("url", "N/A"),
            "source_job_role": "Software Engineer" if is_repo_input else repo.get("title", "N/A")
        },
        "author": {
            "type": "auto-generated",
            "source": "github" if is_repo_input else "job-description",
            "created_by": f"gemini-taskgen-{difficulty_level}"
        },
        "created_at": now_utc,
        "last_updated": now_utc
    }

    return final_task

def generate_all_difficulty_tasks(digest, repo):
    return {
        "easy": generate_learning_task(digest, repo, "easy"),
        "medium": generate_learning_task(digest, repo, "medium"),
        "hard": generate_learning_task(digest, repo, "hard"),
    }
