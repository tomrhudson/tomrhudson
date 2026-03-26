#!/usr/bin/env python3
"""
update_languages.py
Fetches language usage across all repos (public + private) for a GitHub user,
then rewrites the Languages & Tools section in README.md with shields.io badges.
"""

import os
import re
import requests

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_USER  = os.environ.get("GITHUB_USER", "tomrhudson")
README_PATH  = os.environ.get("README_PATH", "README.md")
TOP_N        = int(os.environ.get("TOP_N", "10"))

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Markers that wrap the auto-generated section in the README
START_MARKER = "<!-- LANGUAGES_START -->"
END_MARKER   = "<!-- LANGUAGES_END -->"

# ── Badge style config ────────────────────────────────────────────────────────
# Maps GitHub language name → (shields.io logo slug, hex color, logo color)
# Add / adjust entries here as needed.
LANG_META = {
    "Python":              ("python",           "3776AB", "white"),
    "JavaScript":          ("javascript",       "F7DF1E", "black"),
    "TypeScript":          ("typescript",       "3178C6", "white"),
    "Shell":               ("gnubash",          "4EAA25", "white"),
    "Bash":                ("gnubash",          "4EAA25", "white"),
    "HTML":                ("html5",            "E34F26", "white"),
    "CSS":                 ("css3",             "1572B6", "white"),
    "React":               ("react",            "61DAFB", "black"),
    "Node.js":             ("node.js",          "339933", "white"),
    "Ruby":                ("ruby",             "CC342D", "white"),
    "Go":                  ("go",               "00ADD8", "white"),
    "Rust":                ("rust",             "000000", "white"),
    "C":                   ("c",                "A8B9CC", "black"),
    "C++":                 ("cplusplus",        "00599C", "white"),
    "C#":                  ("csharp",           "239120", "white"),
    "Java":                ("java",             "007396", "white"),
    "Kotlin":              ("kotlin",           "7F52FF", "white"),
    "Swift":               ("swift",            "FA7343", "white"),
    "PHP":                 ("php",              "777BB4", "white"),
    "PowerShell":          ("powershell",       "5391FE", "white"),
    "Dockerfile":          ("docker",           "2496ED", "white"),
    "YAML":                ("yaml",             "CB171E", "white"),
    "Makefile":            ("gnu",              "A42E2B", "white"),
    "Jupyter Notebook":    ("jupyter",          "F37626", "white"),
    "Markdown":            ("markdown",         "000000", "white"),
    "SQL":                 ("postgresql",       "4169E1", "white"),
    "HCL":                 ("terraform",        "7B42BC", "white"),
    "Vue":                 ("vuedotjs",         "4FC08D", "white"),
}

def get_all_repos():
    """Paginate through all repos (public + private) for the authenticated user."""
    repos, page = [], 1
    while True:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos

def get_repo_languages(owner, repo_name):
    """Return the language byte counts for a single repo."""
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/languages",
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()

def build_badge(lang):
    """Return a shields.io badge markdown string for the given language name."""
    label = lang.replace("-", "--").replace("_", "__").replace(" ", "_")
    logo, color, logo_color = LANG_META.get(lang, (lang.lower().replace(" ", ""), "555555", "white"))
    url = (
        f"https://img.shields.io/badge/{label}-{color}"
        f"?style=flat-square&logo={logo}&logoColor={logo_color}"
    )
    return f"[![{lang}]({url})]({url})"

def main():
    print(f"Fetching repos for {GITHUB_USER}...")
    repos = get_all_repos()
    print(f"  Found {len(repos)} repos.")

    totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue  # skip forks — they'd skew the counts
        langs = get_repo_languages(GITHUB_USER, repo["name"])
        for lang, byte_count in langs.items():
            totals[lang] = totals.get(lang, 0) + byte_count

    # Sort by bytes descending, take top N
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    print(f"  Top {TOP_N} languages: {[l for l, _ in ranked]}")

    # Build badge block
    badges = "  ".join(build_badge(lang) for lang, _ in ranked)
    new_section = f"{START_MARKER}\n{badges}\n{END_MARKER}"

    # Read README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace between markers if they exist, otherwise warn
    if START_MARKER not in content or END_MARKER not in content:
        print("ERROR: Markers not found in README. Add the following manually:")
        print(f"  {START_MARKER}")
        print(f"  {END_MARKER}")
        raise SystemExit(1)

    updated = re.sub(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        new_section,
        content,
        flags=re.DOTALL,
    )

    if updated == content:
        print("No changes detected — README already up to date.")
        return

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README updated successfully.")

if __name__ == "__main__":
    main()
