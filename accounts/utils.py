import requests

def get_github_data(username):
    user_url = f'https://api.github.com/users/{username}'
    repos_url = f'https://api.github.com/users/{username}/repos?per_page=100'

    user_res = requests.get(user_url)
    repos_res = requests.get(repos_url)

    if user_res.status_code != 200 or repos_res.status_code != 200:
        return {}

    user_json = user_res.json()
    repos = repos_res.json()

    # Sort repos by stars (fallback: updated date)
    repos_sorted = sorted(
        repos,
        key=lambda r: (r.get("stargazers_count", 0), r.get("updated_at", "")),
        reverse=True
    )
    top_repositories = repos_sorted[:3]

    # Calculate top languages
    lang_count = {}
    for repo in repos:
        lang = repo.get('language')
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1

    total_langs = sum(lang_count.values())
    top_languages = {}
    if total_langs > 0:
        top_languages = {
            k: round((v / total_langs) * 100)
            for k, v in sorted(lang_count.items(), key=lambda x: x[1], reverse=True)
        }

    public_repos = user_json.get('public_repos', 0)
    followers = user_json.get('followers', 0)

    # Add safe extra fields for dashboard
    return {
        # original fields (used in signup)
        'public_repos': public_repos,
        'followers': followers,
        'top_languages': top_languages,

        # extra fields for dashboard
        'repos_progress': min(public_repos, 100),
        'contributions': followers,  # proxy for now
        'contributions_progress': min(followers, 100),
        'score': min((public_repos + followers) // 2, 100),
        'top_repositories': top_repositories,
    }

import requests

def get_leetcode_data(username):
    # --- GraphQL for profile, stats, categories ---
    graphql_url = 'https://leetcode.com/graphql'
    graphql_query = {
        "query": """
        query getUserProfile($username: String!) {
          matchedUser(username: $username) {
            submitStats {
              acSubmissionNum {
                difficulty
                count
              }
            }
            profile {
              ranking
              reputation
            }
            tagProblemCounts {
              advanced {
                tagName
                problemsSolved
              }
              intermediate {
                tagName
                problemsSolved
              }
              fundamental {
                tagName
                problemsSolved
              }
            }
          }
        }
        """,
        "variables": {"username": username}
    }

    res = requests.post(graphql_url, json=graphql_query, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        print("GraphQL error:", res.text[:200])
        return {}

    data = res.json().get('data', {}).get('matchedUser')
    if not data:
        print(f"⚠️ No matchedUser found for {username}")
        return {}

    # ✅ Submissions stats
    submissions = data['submitStats']['acSubmissionNum']
    stats = {}
    total_from_all = 0
    for sub in submissions:
        diff = (sub.get('difficulty') or '').lower()
        if diff in ('easy', 'medium', 'hard'):
            stats[diff] = sub.get('count', 0)
        elif diff in ('all', 'total'):
            total_from_all = sub.get('count', 0)

    total = total_from_all or (
        stats.get('easy', 0) + stats.get('medium', 0) + stats.get('hard', 0)
    )

    # ✅ Rank
    rank = int((data.get('profile') or {}).get('ranking') or 0)

    # ✅ Categories (merge advanced+intermediate+fundamental)
    categories = []
    for section in ("advanced", "intermediate", "fundamental"):
        for c in (data.get("tagProblemCounts") or {}).get(section, []):
            categories.append({"tag": c["tagName"], "solved": c["problemsSolved"]})

    # --- External API for recent submissions ---
    recent_subs = []
    try:
      api_url = f"https://leetcode-api-pied.vercel.app/user/{username}/submissions?limit=20"
      subs_res = requests.get(api_url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    
      if subs_res.status_code == 200:
        subs_json = subs_res.json()
        # The API directly returns a list, no "submission" key
        recent_subs = subs_json[:10]  # top 10
      else:
        print("⚠️ Submissions API failed:", subs_res.status_code)
    except Exception as e:
      print("⚠️ Error fetching submissions:", e)


    return {
        # original fields (signup use)
        'easy': stats.get('easy', 0),
        'medium': stats.get('medium', 0),
        'hard': stats.get('hard', 0),
        'ranking': rank,

        # dashboard extras
        'total_problems_solved': total,
        'easy_solved': stats.get('easy', 0),
        'medium_solved': stats.get('medium', 0),
        'hard_solved': stats.get('hard', 0),
        'recent_submissions': recent_subs,
        'categories': categories,
    }


import re
import fitz  # PyMuPDF

TECH_KEYWORDS = ["python", "java", "c++", "c#", "django", "flask", "react", "node.js",
                 "sql", "postgresql", "mongodb", "html", "css", "javascript", "aws",
                 "docker", "kubernetes", "git"]

def extract_text_from_pdf(path):
    text = ""
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text("text")
    return text.lower()

def extract_skills_from_resume(path):
    text = extract_text_from_pdf(path)
    found = [tech for tech in TECH_KEYWORDS if tech in text]
    return list(set(found))
