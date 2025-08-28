import streamlit as st
import os
import json
import requests
import re
import pandas as pd
import asyncio
from firecrawl import AsyncFirecrawlApp
from pydantic import BaseModel, Field
from typing import Any, Optional, List
from datetime import datetime 
import io 
import zipfile 
#

from utils.utils import clone_repo, summarize_codebase, cleanup_repo
from utils.gemini_helpers import (
    generate_repo_insights,
    generate_all_difficulty_tasks,
    extract_technologies_from_digest
)
from utils.scraper import get_trending_repos
from utils.utils import remove_emojis, append_auto_helpful_links

from dotenv import load_dotenv
load_dotenv()

st.set_page_config(layout="wide", page_title="Repo Task Generator")
st.title("GitHub Repo Learning Task Generator")
st.markdown("Generate detailed learning tasks and insights for any GitHub repository or job description.")

class NestedModel1(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str
    industry: Optional[str] = None
    url: Optional[str] = None 
    source: Optional[str] = None 

class ExtractSchema(BaseModel):
    job_descriptions: List[NestedModel1]

def process_inputs_and_generate_tasks(repo_url_input, jd_txt_file, jd_csv_excel_file):
    repo_path = None
    try:
        job_descriptions_to_process = []
        main_digest = None
        main_repo_info = None

        if jd_txt_file:
            main_digest = jd_txt_file.read().decode("utf-8")
            main_repo_info = {
                "title": "Uploaded_JD",
                "url": "N/A",
                "description": "Job description from uploaded file",
                "language": "N/A",
                "stars": "N/A"
            }
            job_descriptions_to_process.append({
                "title": "Uploaded_JD",
                "company": "N/A",
                "location": "N/A",
                "description": main_digest,
                "industry": "N/A"
            })
        elif jd_csv_excel_file:
            if jd_csv_excel_file.name.endswith('.csv'):
                df = pd.read_csv(jd_csv_excel_file)
            else: 
                df = pd.read_excel(jd_csv_excel_file)

            title_col = 'title' if 'title' in df.columns else 'job_title' if 'job_title' in df.columns else None
            company_col = 'company' if 'company' in df.columns else None
            location_col = 'location' if 'location' in df.columns else None
            industry_col = 'industry' if 'industry' in df.columns else None
            description_col = 'description' if 'description' in df.columns else 'job_description' if 'job_description' in df.columns else None

            if not description_col:
                st.error("Could not find a 'description' or 'job_description' column in the uploaded file.")
                return 

            for index, row in df.iterrows():
                job_descriptions_to_process.append({
                    "title": row[title_col] if title_col and pd.notna(row[title_col]) else f"Job_Description_{index+1}",
                    "company": row[company_col] if company_col and pd.notna(row[company_col]) else "N/A",
                    "location": row[location_col] if location_col and pd.notna(row[location_col]) else "N/A",
                    "description": row[description_col] if pd.notna(row[description_col]) else "No description provided.",
                    "industry": row[industry_col] if industry_col and pd.notna(row[industry_col]) else "N/A"
                })
        elif repo_url_input:
            parts = repo_url_input.split('/')
            main_repo_info = {
                "title": f"{parts[-2]}/{parts[-1]}",
                "url": repo_url_input,
                "description": "Custom repo analysis",
                "language": "Python",
                "stars": "N/A"
            }
            with st.spinner(f"Cloning {repo_url_input}..."):
                repo_path = clone_repo(repo_url_input)
            with st.spinner("Summarizing codebase..."):
                main_digest = summarize_codebase(repo_path)

        if main_digest and main_repo_info:
            st.subheader("Digest")
            st.text_area("Preview", main_digest[:5000] + "..." if len(main_digest) > 5000 else main_digest, height=300)

            with st.spinner("Generating insights with Gemini..."):
                insights = generate_repo_insights(main_digest)

            st.subheader("Repository Insights")
            if insights.get("error_type"):
                st.error(f"Could not generate insights: {insights.get('message', 'Unknown error')}")
                st.text_area("Raw LLM Response", insights.get("raw_response", ""), height=200)
            else:
                st.json(insights)

            with st.spinner("Extracting tech terms & helpful links..."):
                is_repo_input = (main_repo_info.get('url') != "N/A")
                techs = extract_technologies_from_digest(main_digest, is_repo_input)
                helpful_links = append_auto_helpful_links(techs)

            with st.spinner("Generating learning tasks..."):
                tasks = generate_all_difficulty_tasks(main_digest, main_repo_info)

            st.subheader("Generated Learning Tasks")
            for difficulty, task in tasks.items():
                task["description"] = remove_emojis(task.get("description", "")) + helpful_links

                with st.expander(f"{difficulty.capitalize()} Task: {task.get('title', 'Untitled')}"):
                    st.json(task)
                    st.markdown(f"**Difficulty:** {task.get('difficulty', 'N/A')} / 3")
                    st.markdown(f"**Estimated Time:** {task.get('estimated_time_hours', 'N/A')} hours")
                    st.markdown("---")
                    st.markdown(task.get("description", "No description available"))
        
        if job_descriptions_to_process:
            all_generated_tasks = []
            for i, jd in enumerate(job_descriptions_to_process):
                st.markdown(f"**Job {i+1}: {jd.get('title', 'Untitled')} at {jd.get('company', 'N/A')}**")
                st.json(jd)

                digest = f"Job Title: {jd.get('title', 'N/A')}\n" \
                         f"Company: {jd.get('company', 'N/A')}\n" \
                         f"Location: {jd.get('location', 'N/A')}\n" \
                         f"Industry: {jd.get('industry', 'N/A')}\n\n" \
                         f"Description:\n{jd.get('description', 'No description provided.')}"

                repo_info = {
                    "title": jd.get('title', f"Job_Description_{i+1}"),
                    "url": "N/A",
                    "description": f"Job description for {jd.get('title', 'Untitled')}",
                    "language": "N/A",
                    "stars": "N/A"
                }

                with st.spinner(f"Generating tasks for {jd.get('title', 'Untitled')}..."):
                    tasks = generate_all_difficulty_tasks(digest, repo_info)
                    
                    is_repo_input_jd = (repo_info.get('url') != "N/A") 
                    techs_used = extract_technologies_from_digest(digest, is_repo_input_jd)
                    helpful_links = append_auto_helpful_links(techs_used)

                    for difficulty, task in tasks.items():
                        task["description"] = remove_emojis(task.get("description", "")) + helpful_links
                        all_generated_tasks.append(task)
                        with st.expander(f"{difficulty.capitalize()} Task: {task.get('title', 'Untitled')}"):
                            st.json(task)
                            st.markdown(f"**Difficulty:** {task.get('difficulty', 'N/A')} / 3")
                            st.markdown(f"**Estimated Time:** {task.get('estimated_time_hours', 'N/A')} hours")
                            st.markdown("---")
                            st.markdown(task.get("description", "No description available"))
                            
                            task_json = json.dumps(task, indent=2)
                            st.download_button(
                                label=f"Download {difficulty.capitalize()} Task JSON",
                                data=task_json,
                                file_name=f"{task['title'].replace(' ', '_').replace('/', '_')}_{difficulty}.json",
                                mime="application/json",
                                key=f"download_task_{task.get('task_id', i)}_{difficulty}"
                            )
            
            st.markdown("---")

            if all_generated_tasks:
                all_tasks_json = json.dumps(all_generated_tasks, indent=2)
                st.download_button(
                    label="Download All Generated Tasks (Single JSON)",
                    data=all_tasks_json,
                    file_name=f"all_job_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_all_tasks_single"
                )

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for i, jd in enumerate(job_descriptions_to_process):
                        jd_title_safe = jd.get('title', f"Job_Description_{i+1}").replace(' ', '_').replace('/', '_')
                        jd_filename = f"extracted_jd_{jd_title_safe}.json"
                        zip_file.writestr(jd_filename, json.dumps(jd, indent=2))

                    for task in all_generated_tasks:
                        task_title_safe = task['title'].replace(' ', '_').replace('/', '_')
                        task_filename = f"generated_task_{task_title_safe}_{task['difficulty']}.json"
                        zip_file.writestr(task_filename, json.dumps(task, indent=2))
                
                st.download_button(
                    label="Download All Data (Tasks & JDs as ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"job_scraper_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    key="download_all_data_zip_from_file"
                )

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        if repo_path:
            cleanup_repo(repo_path)

st.header("Generate Tasks from a GitHub URL or Upload a JD File")
repo_url_input = st.text_input("Enter GitHub Repository URL:")
jd_txt_file = st.file_uploader("Or upload a Single Job Description (.txt):", type=["txt"], key="jd_txt_uploader")

st.markdown("---")
st.header("Or Upload Multiple Job Descriptions from CSV/Excel")
jd_csv_excel_file = st.file_uploader("Upload a CSV or Excel file with Job Descriptions:", type=["csv", "xlsx"], key="jd_csv_excel_uploader")

if st.button("Generate Tasks & Digest"):
    if not repo_url_input and not jd_txt_file and not jd_csv_excel_file:
        st.error("Please enter a GitHub URL, upload a .txt file, or upload a CSV/Excel file.")
    else:
        process_inputs_and_generate_tasks(repo_url_input, jd_txt_file, jd_csv_excel_file)

st.header("Scrape Job Descriptions from Websites")

available_keywords = ["SaaS", "Blockchain", "AI", "Longevity", "Web3", "Fintech", "Cybersecurity"]
available_platforms = {
    "Animoca Brands Careers": "https://careers.animocabrands.com/jobs",
    "Indeed.com (General)": "https://indeed.com/*",
    "Base.org Jobs": "https://base.org/jobs",
    "Prospera Jobs": "https://jobs.prospera.co/",
    "Longevity List": "https://longevitylist.com/",
    "Wellfound (AngelList)": "https://wellfound.com/",
    "Naukri.com (India)": "https://www.naukri.com/"
}

selected_keywords = st.multiselect(
    "Select keywords for job descriptions:",
    options=available_keywords,
    default=["SaaS", "Blockchain", "AI", "Longevity"]
)

selected_platform_names = st.multiselect(
    "Select platforms to scrape from:",
    options=list(available_platforms.keys()),
    default=list(available_platforms.keys())
)

firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_api_key:
    st.warning("FIRECRAWL_API_KEY not found in environment variables. Job scraping will not work.")
else:
    if st.button("Scrape Job Descriptions"):
        if not selected_platform_names:
            st.error("Please select at least one platform to scrape from.")
        else:
            st.info("Scraping may take a few minutes depending on the number of URLs and content size.")
            try:
                app = AsyncFirecrawlApp(api_key=firecrawl_api_key)
                
                urls_to_scrape = [available_platforms[name] for name in selected_platform_names]
                
                prompt_keywords = ", ".join(selected_keywords)
                scrape_prompt = f'Extract job descriptions related to {prompt_keywords}. Ensure to capture the job title, job description, company, location, and industry if available. I need the complete job description, with key responsibilities and requirements and everything. No summaries of job descriptions'

                with st.spinner("Scraping job descriptions..."):
                    response = asyncio.run(app.extract(
                        urls=urls_to_scrape,
                        prompt=scrape_prompt, 
                        schema=ExtractSchema.model_json_schema()
                    ))
                
                job_descriptions = []
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    job_descriptions = response.data.get("job_descriptions", [])
                elif isinstance(response, dict): 
                    job_descriptions = response.get("job_descriptions", [])
                elif hasattr(response, 'job_descriptions'):
                    job_descriptions = response.job_descriptions
                else:
                    st.error("Could not determine the structure of the Firecrawl response. Please check the Firecrawl API documentation.")
                    st.json(response) 
                if not job_descriptions:
                    st.warning("No job descriptions were extracted.")
                else:
                    st.subheader(f"Extracted {len(job_descriptions)} Job Descriptions")
                    all_generated_tasks = []
                    for i, jd in enumerate(job_descriptions):
                        jd['url'] = jd.get('url', 'N/A')
                        jd['source'] = jd.get('source', selected_platform_names[0] if selected_platform_names else 'N/A') # Assuming first selected platform as source if not in JD

                        description_content = jd.get('description', '')
                        if len(description_content) <= 500:
                            st.warning(f"Skipping job '{jd.get('title', 'Untitled')}' from {jd.get('source', 'N/A')} due to description length ({len(description_content)} chars <= 500).")
                            continue 

                        st.markdown(f"**Job {i+1}: {jd.get('title', 'Untitled')} at {jd.get('company', 'N/A')}**")
                        st.json(jd)

                        digest = f"Job Title: {jd.get('title', 'N/A')}\n" \
                                 f"Company: {jd.get('company', 'N/A')}\n" \
                                 f"Location: {jd.get('location', 'N/A')}\n" \
                                 f"Industry: {jd.get('industry', 'N/A')}\n" \
                                 f"URL: {jd.get('url', 'N/A')}\n" \
                                 f"Source: {jd.get('source', 'N/A')}\n\n" \
                                 f"Description:\n{description_content}" 

                        repo_info = {
                            "title": jd.get('title', f"Job_Description_{i+1}"),
                            "url": jd.get('url', 'N/A'), 
                            "description": f"Job description for {jd.get('title', 'Untitled')}",
                            "language": "N/A",
                            "stars": "N/A"
                        }

                        with st.spinner(f"Generating tasks for {jd.get('title', 'Untitled')}..."):
                            tasks = generate_all_difficulty_tasks(digest, repo_info)
                            
                            is_repo_input_jd = (repo_info.get('url') != "N/A") 
                            techs_used = extract_technologies_from_digest(digest, is_repo_input_jd)
                            helpful_links = append_auto_helpful_links(techs_used)

                            for difficulty, task in tasks.items():
                                task["description"] = remove_emojis(task.get("description", "")) + helpful_links
                                all_generated_tasks.append(task)
                                with st.expander(f"{difficulty.capitalize()} Task: {task.get('title', 'Untitled')}"):
                                    st.json(task)
                                    st.markdown(f"**Difficulty:** {task.get('difficulty', 'N/A')} / 3")
                                    st.markdown(f"**Estimated Time:** {task.get('estimated_time_hours', 'N/A')} hours")
                                    st.markdown("---")
                                    st.markdown(task.get("description", "No description available"))
                                    
                                    task_json = json.dumps(task, indent=2)
                                    st.download_button(
                                        label=f"Download {difficulty.capitalize()} Task JSON",
                                        data=task_json,
                                        file_name=f"{task['title'].replace(' ', '_').replace('/', '_')}_{difficulty}.json",
                                        mime="application/json",
                                        key=f"download_task_{task.get('task_id', i)}_{difficulty}"
                                    )
            
                    if all_generated_tasks:
                        all_tasks_json = json.dumps(all_generated_tasks, indent=2)
                        st.download_button(
                            label="Download All Generated Tasks (Single JSON)",
                            data=all_tasks_json,
                            file_name=f"all_job_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            key="download_all_tasks_single"
                        )

                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                            processed_jds = [jd for jd in job_descriptions if len(jd.get('description', '')) > 500]
                            for i, jd in enumerate(processed_jds):
                                jd_title_safe = jd.get('title', f"Job_Description_{i+1}").replace(' ', '_').replace('/', '_')
                                jd_filename = f"extracted_jd_{jd_title_safe}.json"
                                zip_file.writestr(jd_filename, json.dumps(jd, indent=2))

                            for task in all_generated_tasks:
                                task_title_safe = task['title'].replace(' ', '_').replace('/', '_')
                                task_filename = f"generated_task_{task_title_safe}_{task['difficulty']}.json"
                                zip_file.writestr(task_filename, json.dumps(task, indent=2))
                        
                        st.download_button(
                            label="Download All Data (Tasks & JDs as ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=f"job_scraper_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip",
                            key="download_all_data_zip"
                        )
            except Exception as e:
                st.error(f"An error occurred during scraping or task generation: {e}")

st.header("Explore Trending GitHub Repositories")
if st.button("Fetch Trending Repos"):
    with st.spinner("Fetching..."):
        try:
            trending_repos = get_trending_repos()
            st.session_state['trending_repos'] = trending_repos
        except Exception as e:
            st.error(f"Failed to fetch: {e}")
            st.session_state['trending_repos'] = []

if 'trending_repos' in st.session_state and st.session_state['trending_repos']:
    st.subheader("Select a Trending Repo")
    repo_options = [f"{repo['title']} ({repo['language']} - {repo['stars']} stars)" for repo in st.session_state['trending_repos']]
    selected_display = st.selectbox("Choose:", options=repo_options)
    selected_index = repo_options.index(selected_display)
    selected_repo = st.session_state['trending_repos'][selected_index]

    st.markdown(f"**Selected:** [{selected_repo['title']}]({selected_repo['url']})")
    st.markdown(f"**Language:** {selected_repo['language']} | **Stars:** {selected_repo['stars']}")

    if st.button(f"Generate Tasks & Digest for {selected_repo['title']}"):
        repo_path = None
        try:
            with st.spinner(f"Cloning {selected_repo['url']}..."):
                repo_path = clone_repo(selected_repo['url'])
            with st.spinner("Summarizing codebase..."):
                digest = summarize_codebase(repo_path)

            st.subheader("Digest")
            st.text_area("Preview", digest[:5000] + "..." if len(digest) > 5000 else digest, height=300)

            with st.spinner("Generating insights with Gemini..."):
                insights = generate_repo_insights(digest)

            st.subheader("Repository Insights")
            if insights.get("error_type"):
                st.error(f"Could not generate insights: {insights.get('message', 'Unknown error')}")
                st.text_area("Raw LLM Response", insights.get("raw_response", ""), height=200)
            else:
                st.json(insights)

            with st.spinner("Extracting tech terms & helpful links..."):
                is_repo_input = (selected_repo.get('url') != "N/A")
                techs = extract_technologies_from_digest(digest, is_repo_input)
                helpful_links = append_auto_helpful_links(techs)

            with st.spinner("Generating learning tasks..."):
                tasks = generate_all_difficulty_tasks(digest, selected_repo)

            st.subheader("Generated Learning Tasks")
            for difficulty, task in tasks.items():
                task["description"] = remove_emojis(task.get("description", "")) + helpful_links
                with st.expander(f"{difficulty.capitalize()} Task: {task.get('title', 'Untitled')}"):
                    st.json(task)
                    st.markdown(f"**Difficulty:** {task.get('difficulty', 'N/A')} / 3")
                    st.markdown(f"**Estimated Time:** {task.get('estimated_time_hours', 'N/A')} hours")
                    st.markdown("---")
                    st.markdown(task.get("description", "No description available"))
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if repo_path:
                cleanup_repo(repo_path)
