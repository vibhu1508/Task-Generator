import requests
from bs4 import BeautifulSoup

def get_trending_repos():
    resp = requests.get("https://github.com/trending", headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise Exception(f"Failed: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    trending = []

    for repo in soup.select("article.Box-row"):
        a = repo.select_one("h2.h3.lh-condensed a")
        if not a or not a.get("href"):
            print("Skipped a repo due to missing link or href.")
            continue

        href = a["href"].strip()
        name = href.lstrip("/")
        url = "https://github.com" + href

        desc_tag = repo.select_one("p.col-9.color-fg-muted.my-1.pr-4")
        desc = desc_tag.text.strip() if desc_tag else ""

        lang_tag = repo.select_one("span[itemprop='programmingLanguage']")
        lang = lang_tag.text.strip() if lang_tag else ""

        stars_tag = repo.select_one("a[href$='/stargazers']")
        stars = stars_tag.text.strip() if stars_tag else "0"

        forks_tag = repo.select_one("a[href$='/network/members']")
        forks = forks_tag.text.strip() if forks_tag else "0"

        trending.append({
            "title": name,
            "url": url,
            "description": desc,
            "language": lang,
            "stars": stars,
        })

    print(f"Found {len(trending)} repos")
    if len(trending) == 0:
        print("Here’s a sample article snippet:\n", soup.select_one("article.Box-row"))
    return trending
