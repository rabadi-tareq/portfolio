import os
import json
import re
from datetime import datetime
from urllib import request, parse

# Your exact GitHub account username
USERNAME = "rabadi-tareq"  

# GitHub REST API base URL
API_BASE_URL = "https://api.github.com"


def to_project_date(iso_datetime):
    dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
    return dt.strftime("%d/%m/%Y")


def to_topics_yaml(topics):
    if not topics:
        return "[]"

    sanitized = [topic.strip() for topic in topics if topic and topic.strip()]
    if not sanitized:
        return "[]"

    return "[" + ", ".join(sanitized) + "]"


def update_project_dates(repos_data):
    projects_dir = "_projects"
    if not os.path.isdir(projects_dir):
        print("Skipping markdown date sync: _projects folder was not found.")
        return

    matched_files = 0
    updated_files = 0

    for repo in repos_data:
        repo_name = repo.get("name")
        updated_at = repo.get("pushed_at")
        api_description = (repo.get("description") or "No description provided.").strip()
        api_topics = sorted(
            [topic for topic in repo.get("topics", []) if isinstance(topic, str)],
            key=str.lower,
        )
        if not repo_name or not updated_at:
            continue

        project_file = os.path.join(projects_dir, f"{repo_name}.md")
        if not os.path.isfile(project_file):
            # Ignore repos without a matching markdown file, per requirement.
            continue

        matched_files += 1
        new_date = to_project_date(updated_at)
        # Use JSON quoting to keep YAML-safe one-line text (e.g. colons, quotes).
        new_description = json.dumps(api_description, ensure_ascii=False)
        # Use YAML flow sequence without quoted list values.
        new_topics = to_topics_yaml(api_topics)

        with open(project_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Only touch front matter (between first and second --- lines).
        # Accept UTF-8 BOM and either LF or CRLF line endings.
        match = re.match(r"\A(?:\ufeff)?---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", content, re.DOTALL)
        if not match:
            continue

        front_matter_body = match.group(1)
        body = match.group(2)

        if re.search(r"(?m)^date:\s*.*$", front_matter_body):
            new_front_matter_body = re.sub(
                r"(?m)^date:\s*.*$",
                f"date: {new_date}",
                front_matter_body,
            )
        else:
            new_front_matter_body = front_matter_body + f"\ndate: {new_date}"

        if re.search(r"(?m)^description:\s*.*$", new_front_matter_body):
            new_front_matter_body = re.sub(
                r"(?m)^description:\s*.*$",
                f"description: {new_description}",
                new_front_matter_body,
            )
        else:
            new_front_matter_body = new_front_matter_body + f"\ndescription: {new_description}"

        if re.search(r"(?m)^(tech|topics):\s*.*$", new_front_matter_body):
            new_front_matter_body = re.sub(
                r"(?m)^(tech|topics):\s*.*$",
                f"topics: {new_topics}",
                new_front_matter_body,
            )
        else:
            new_front_matter_body = new_front_matter_body + f"\ntopics: {new_topics}"

        new_content = f"---\n{new_front_matter_body}\n---\n{body}"
        if new_content != content:
            with open(project_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_files += 1

    print(
        "Markdown date sync complete: "
        f"{updated_files} updated from {matched_files} matched repo/project files."
    )

def fetch_and_save_repos():
    try:
        print(f"Fetching public repositories for user: {USERNAME}...")
        repos_data = []
        page = 1

        # Paginate to ensure we fetch all public repositories.
        while True:
            query = parse.urlencode({
                "type": "public",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            })
            url = f"{API_BASE_URL}/users/{USERNAME}/repos?{query}"
            req = request.Request(
                url,
                headers={"Accept": "application/vnd.github+json"},
            )

            with request.urlopen(req, timeout=20) as response:
                page_repos = json.loads(response.read().decode("utf-8"))

            if not page_repos:
                break

            repos_data.extend(page_repos)
            page += 1
        
        update_project_dates(repos_data)
            
        print("Success! Matching project markdown files in _projects have been updated.")
        
    except Exception as e:
        print(f"An error occurred while fetching repository data: {e}")

if __name__ == "__main__":
    fetch_and_save_repos()