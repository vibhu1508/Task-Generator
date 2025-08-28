import os
import git
import shutil
import tempfile
import stat
import gc
import re

def clone_repo(repo_url):
    """Clones a GitHub repository into a temporary directory."""
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"Cloning {repo_url} into {temp_dir}...")
        repo = git.Repo.clone_from(repo_url, temp_dir, depth=1)
        del repo
        print("Clone successful.")
        return temp_dir
    except git.GitCommandError as e:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            cleanup_repo(temp_dir)
        raise Exception(f"Failed to clone repository: {e.stderr if e.stderr else e}")
    except Exception as e:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            cleanup_repo(temp_dir)
        raise Exception(f"An unexpected error occurred during cloning: {e}")


def _is_text_file(filepath):
    """Check if a file is likely a text file."""
    text_extensions = [
        '.py', '.js', '.ts', '.html', '.css', '.scss', '.java', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rb', '.php', '.cs', '.swift', '.kt', '.rs', '.json', '.yaml', '.yml',
        '.xml', '.md', '.txt', '.toml', '.ini', '.cfg', '.conf', '.env', '.sh', '.bash',
        '.zsh', '.ps1', '.bat', '.sql', '.vue', '.svelte', '.jsx', '.tsx', '.mjs', '.cjs',
        '.rst', '.tex', '.toml', '.tsv', '.csv', '.lock', '.gitmodules', '.editorconfig',
        '.prettierrc', '.eslintrc', '.gitignore', '.gitattributes', 'Dockerfile', 'Makefile',
        '.env.example', '.nvmrc', '.terraform', '.tf', '.puml', '.drawio', '.mmd'
    ]
    name, ext = os.path.splitext(filepath)
    return ext.lower() in text_extensions or os.path.basename(filepath).lower() in ["dockerfile", "makefile", "license", "licence"]


def summarize_codebase(repo_path, max_file_size_kb=500, max_total_digest_chars=50000):
    """
    Summarizes the codebase by concatenating the content of relevant text files.
    Skips binary files and common build/dependency directories.
    """
    digest_parts = []
    total_chars = 0
    excluded_dirs = [
        '.git', '__pycache__', 'node_modules', 'venv', '.env', 'build', 'dist',
        '.vscode', '.idea', '.DS_Store', 'bin', 'obj', 'target', 'vendor',
        'tmp', 'temp', 'logs', 'log', 'coverage', '.pytest_cache', '.next',
        '.parcel-cache', '.nuxt', '.svelte-kit', '.cargo', '.gradle',
        '.mvn', '.vs', '.docusaurus', '.firebase', '.serverless', '.yarn'
    ]

    readme_content = ""
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                readme_content = f.read()
                digest_parts.append(f"## README.md\n\n{readme_content}\n\n")
                total_chars += len(readme_content)
        except Exception as e:
            print(f"Could not read README.md: {e}")

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)

            if any(part in relative_path.split(os.sep) for part in ['package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'Pipfile.lock', 'Gemfile.lock', 'pom.xml', 'gradlew', 'Makefile', 'Dockerfile', 'license']):
                continue

            if os.path.getsize(file_path) > max_file_size_kb * 1024 or not _is_text_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content) > max_file_size_kb * 5:
                        content = content[:max_file_size_kb * 5] + "\n... (truncated)"

                    if total_chars + len(content) > max_total_digest_chars:
                        break 

                    digest_parts.append(f"--- FILE: {relative_path} ---\n{content}\n")
                    total_chars += len(content)

            except Exception as e:
                print(f"Could not read {relative_path}: {e}")

        if total_chars > max_total_digest_chars:
            break

    full_digest = "\n\n".join(digest_parts)

    if len(full_digest) > max_total_digest_chars:
        full_digest = full_digest[:max_total_digest_chars] + "\n\n... (overall digest truncated)"

    return full_digest


def handle_remove_read_only(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files."""
    if func in (os.unlink, os.remove) and exc_info[0] is PermissionError:
        if os.path.exists(path):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception as e:
                print(f"Error changing permissions or retrying remove for {path}: {e}")
                raise exc_info[1]
    else:
        raise exc_info[1]


def cleanup_repo(repo_path):
    """Removes the cloned repository directory."""
    if os.path.exists(repo_path):
        print(f"Cleaning up {repo_path}")
        gc.collect()
        try:
            shutil.rmtree(repo_path, onerror=handle_remove_read_only)
            print(f"Successfully cleaned up {repo_path}")
        except Exception as e:
            print(f"Failed to clean up {repo_path}: {e}")
            print("Please manually delete the directory if it persists.")


def remove_emojis(text):
    """Remove emojis and non-ASCII characters."""
    return re.sub(r'[^\x00-\x7F]+', '', text)


TECH_LINKS = {
    "python": "https://docs.python.org/3/",
    "react": "https://react.dev/learn",
    "django": "https://docs.djangoproject.com/en/stable/",
    "nodejs": "https://nodejs.org/en/docs/",
    "flask": "https://flask.palletsprojects.com/",
    "pandas": "https://pandas.pydata.org/docs/",
    "numpy": "https://numpy.org/doc/",
    "kubernetes": "https://kubernetes.io/docs/home/",
    "docker": "https://docs.docker.com/",
    "fastapi": "https://fastapi.tiangolo.com/",
    "supabase": "https://supabase.com/docs",
    "langchain": "https://docs.langchain.com/",
    "tensorflow": "https://www.tensorflow.org/api_docs",
    "keras": "https://keras.io/",
    "scikit-learn": "https://scikit-learn.org/stable/user_guide.html",
    "huggingface": "https://huggingface.co/docs",
    "streamlit": "https://docs.streamlit.io/",
}

def append_auto_helpful_links(tech_keywords):
    found = []
    seen = set()

    for tech in tech_keywords:
        tech_clean = tech.strip()
        tech_lower = tech_clean.lower()

        if tech_lower in seen:
            continue
        seen.add(tech_lower)

        if tech_lower in TECH_LINKS:
            found.append(f"- [{tech_clean} Docs]({TECH_LINKS[tech_lower]})")

        found.append(f"- [GitHub Repositories for {tech_clean}](https://github.com/search?q={tech_clean}&type=repositories)")

        found.append(f"- [StackOverflow Q&A on {tech_clean}](https://stackoverflow.com/questions/tagged/{tech_lower})")

        found.append(f"- [YouTube Tutorials for {tech_clean}](https://www.youtube.com/results?search_query={tech_clean}+tutorial)")

    if found:
        return "\n\n### Helpful Links\n" + "\n".join(sorted(found))
    return ""
