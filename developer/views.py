from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from accounts.models import DeveloperProfile
from accounts.utils import get_github_data, get_leetcode_data
from jobs.models import Job, Application
from jobs.views import JobMatchingAI  # Import the AI matching system
import re
from datetime import datetime
import requests


# ---------- Helpers ----------
def extract_github_username(url):
    if not url:
        return None
    m = re.search(r"github\.com/([^/?#]+)/?", url.strip())
    return m.group(1) if m else None

def extract_leetcode_username(url):
    if not url:
        return None
    m = re.search(r"leetcode\.com/(?:u|profile)/([^/?#]+)/?", url.strip())
    return m.group(1) if m else None

def pct(n, d, cap=100):
    try:
        if d <= 0:
            return 0
        v = int(round((float(n) / float(d)) * 100))
        return max(0, min(cap, v))
    except Exception:
        return 0

def coerce_date(s):
    if not s:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return s

def get_leetcode_rating(username):
    url = 'https://leetcode.com/graphql'
    query = {
        "query": """
        query getContestRating($username: String!) {
          userContestRanking(username: $username) {
            rating
            globalRanking
            topPercentage
          }
        }
        """,
        "variables": {"username": username}
    }

    res = requests.post(url, json=query)
    if res.status_code != 200:
        return {}

    rating_data = res.json().get('data', {}).get('userContestRanking')
    if not rating_data:
        return {}

    return {
        "rating": rating_data.get("rating", 0),
        "contest_rank": rating_data.get("globalRanking", 0),
        "top_percent": rating_data.get("topPercentage", 0)
    }

def get_problem_difficulty(title_slug):
    url = "https://leetcode.com/graphql"
    query = {
        "query": """
        query getQuestionDetail($titleSlug: String!) {
          question(titleSlug: $titleSlug) {
            difficulty
          }
        }
        """,
        "variables": {"titleSlug": title_slug}
    }

    res = requests.post(url, json=query, headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        return "Easy"  # fallback

    data = res.json().get("data", {}).get("question")
    if not data:
        return "Easy"

    return data.get("difficulty", "Easy")


# ---------- Normalizers ----------
def build_github_view_model(raw, username):
    raw = raw or {}

    public_repos = raw.get("public_repos", 0)
    contributions = raw.get("contributions", raw.get("followers", 0))  # fallback

    # language distribution
    lang_dist = raw.get("top_languages") or {}
    if not lang_dist:
        lang_dist = {"Other": 100}

    # top repositories (fallback empty)
    top_repos = raw.get("top_repositories", [])
    norm_repos = []
    for r in top_repos:
        norm_repos.append({
            "name": r.get("name", ""),
            "url": r.get("html_url", ""),
            "language": r.get("language", "—"),
            "description": r.get("description", ""),
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "updated_at": coerce_date(r.get("updated_at", "")),
        })

    repos_progress = pct(public_repos, 50)
    contributions_progress = pct(contributions, 1000)
    score = int(round(0.4 * repos_progress + 0.6 * contributions_progress))

    if score >= 85: gh_label = "Excellent"
    elif score >= 65: gh_label = "Very Good"
    elif score >= 45: gh_label = "Good"
    else: gh_label = "Fair"

    return {
        "username": username or "",
        "public_repos": public_repos,
        "contributions": contributions,
        "repos_progress": repos_progress,
        "contributions_progress": contributions_progress,
        "language_distribution": lang_dist,
        "top_repositories": norm_repos,
        "score": score,
        "activity_label": gh_label,
    }

def build_leetcode_view_model(raw, username):
    raw = raw or {}

    total = raw.get("total_problems_solved", raw.get("totalSolved", 0))
    easy = raw.get("easy_solved", raw.get("easy", 0))
    medium = raw.get("medium_solved", raw.get("medium", 0))
    hard = raw.get("hard_solved", raw.get("hard", 0))

    
    # ✅ fetch rating separately
    rating_info = get_leetcode_rating(username)
    rating = int(rating_info.get("rating", 0))

    solved_progress = pct(total, 3000)  # ~3000 total problems
    rating_progress = pct(rating, 3000)

    # ✅ label based on rating
    if rating >= 2000: lc_label = "Excellent"
    elif rating >= 1700: lc_label = "Very Good"
    elif rating >= 1400: lc_label = "Good"
    else: lc_label = "Growing"

    return {
        "username": username or "",
        "total_problems_solved": total,
        "easy_solved": easy,
        "medium_solved": medium,
        "hard_solved": hard,
        "rating": rating,
        "solved_progress": solved_progress,
        "rating_progress": rating_progress,
        "performance_label": lc_label,
        "recent_submissions": raw.get("recent_submissions", []),
        "categories": raw.get("categories", []),
    }


# ---------- Dashboard View ----------
@login_required
def dashboard(request):
    profile = get_object_or_404(DeveloperProfile, user=request.user)

    gh_username = extract_github_username(profile.github_url)
    lc_username = extract_leetcode_username(profile.leetcode_url)
    print(lc_username)

    try:
        gh_raw = get_github_data(gh_username) if gh_username else {}
    except Exception:
        gh_raw = {}

    try:
        lc_raw = get_leetcode_data(lc_username) if lc_username else {}
        print(lc_raw)
    except Exception:
        lc_raw = {}

    github_data = build_github_view_model(gh_raw, gh_username)
    leetcode_data = build_leetcode_view_model(lc_raw, lc_username)

    # Preprocess recent submissions (latest 5)
    recent_subs = []
    for sub in leetcode_data.get("recent_submissions", [])[:5]:
        difficulty = get_problem_difficulty(sub["titleSlug"])  # fetch difficulty dynamically

        difficulty_badge = {
            "chip": difficulty,
            "wrap": {
                "Easy": "bg-green-100 text-green-800",
                "Medium": "bg-yellow-100 text-yellow-800",
                "Hard": "bg-red-100 text-red-800",
            }.get(difficulty, "bg-gray-100 text-gray-800"),
        }

        recent_subs.append({
            "title": sub["title"],
            "runtime": sub.get("runtime"),
            "memory": sub.get("memory"),
            "status": sub.get("statusDisplay"),
            "difficulty_badge": difficulty_badge,
        })

    leetcode_data["recent_submissions"] = recent_subs

    # Preprocess categories: sort by problems solved and take top 10
    total_solved = leetcode_data.get("total_problems_solved", 1)
    categories = sorted(
        leetcode_data.get("categories", []),
        key=lambda x: x["solved"],
        reverse=True
    )[:10]

    categories_processed = []
    for c in categories:
        percent = round(c["solved"] / total_solved * 100)
        categories_processed.append({
            "name": c["tag"],
            "count": c["solved"],
            "percent": percent,
        })

    leetcode_data["categories"] = categories_processed

    profile_strength = int(round((github_data["score"]*0.4 + leetcode_data["rating_progress"]*0.6)))
    category_bonus = min(int(sum(c['solved'] for c in categories[:3]) / total_solved * 10), 10)
    profile_strength += category_bonus

    context = {
        "profile": profile,
        "github_data": github_data,
        "leetcode_data": leetcode_data,
        "profile_strength": profile_strength,
        "github_activity_label": github_data["activity_label"],
        "leetcode_performance_label": leetcode_data["performance_label"],
        "code_quality_label": "Good",  # placeholder
    }
    return render(request, "developer/dashboard_1.html", context)


# ---------- Job Application Views ----------
@login_required
@require_POST
def apply_to_job(request, job_id):
    """Apply to a specific job"""
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user has a complete profile
    try:
        profile = DeveloperProfile.objects.get(user=request.user)
    except DeveloperProfile.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'message': 'Please complete your profile before applying to jobs.'
            }, status=400)
        messages.error(request, "Please complete your profile before applying to jobs.")
        return redirect("developer:dashboard")
    
    # Check if already applied
    existing_application = Application.objects.filter(job=job, developer=request.user).first()
    if existing_application:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'message': 'You have already applied to this job.',
                'application_date': existing_application.applied_at.strftime('%B %d, %Y')
            })
        messages.warning(request, "You have already applied to this job.")
        return redirect("jobs:find_jobs")
    
    # Create new application
    try:
        application = Application.objects.create(
            job=job, 
            developer=request.user,
            status='applied'  # Set initial status
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': 'Application submitted successfully!',
                'application_id': application.id,
                'job_title': job.title,
                'company': getattr(job.recruiter, 'recruiterprofile', None) and job.recruiter.recruiterprofile.company or 'Company',
                'applied_date': application.applied_at.strftime('%B %d, %Y')
            })
        
        messages.success(request, f"Successfully applied to {job.title}!")
        return redirect("developer:applications")
        
    except Exception as e:
        print(f"Error creating application: {e}")  # Debug log
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'message': 'An error occurred while submitting your application. Please try again.'
            }, status=500)
        messages.error(request, "An error occurred while submitting your application. Please try again.")
        return redirect("jobs:find_jobs")


@login_required
def my_applications(request):
    """Display user's job applications with real AI-powered analysis"""
    
    # Get user profile for AI analysis
    try:
        profile = DeveloperProfile.objects.get(user=request.user)
    except DeveloperProfile.DoesNotExist:
        return render(request, 'developer/application.html', {
            'applications': [],
            'total_applications': 0,
            'under_review': 0,
            'avg_match_score': 0,
            'technical_score': 0,
        })
    
    # Get user's applications
    applications = Application.objects.filter(
        developer=request.user
    ).select_related('job', 'job__recruiter').order_by('-applied_at')
    
    # Initialize AI matching system
    ai_matcher = JobMatchingAI()
    
    # Process applications with real AI analysis
    processed_applications = []
    total_match_scores = []
    technical_scores = []
    
    for app in applications:
        # Get company name from recruiter profile
        company_name = "Company Name"
        try:
            if hasattr(app.job.recruiter, 'recruiterprofile'):
                company_name = app.job.recruiter.recruiterprofile.company
        except:
            pass
        
        # Calculate real match scores using AI
        match_analysis = ai_matcher.calculate_comprehensive_match_score(profile, app.job)
        
        # Extract scores
        overall_score = match_analysis.get('overall_score', 0)
        skill_score = match_analysis.get('skill_score', 0)
        experience_score = match_analysis.get('experience_score', 0)
        location_score = match_analysis.get('location_score', 0)
        salary_score = match_analysis.get('salary_score', 0)
        
        total_match_scores.append(overall_score)
        technical_scores.append(skill_score)
        
        # Calculate profile analysis scores based on GitHub and LeetCode data
        gh_username = extract_github_username(profile.github_url)
        lc_username = extract_leetcode_username(profile.leetcode_url)
        
        # Get GitHub data for profile analysis
        try:
            gh_raw = get_github_data(gh_username) if gh_username else {}
        except:
            gh_raw = {}
        
        try:
            lc_raw = get_leetcode_data(lc_username) if lc_username else {}
        except:
            lc_raw = {}
        
        github_data = build_github_view_model(gh_raw, gh_username)
        leetcode_data = build_leetcode_view_model(lc_raw, lc_username)
        
        # Calculate profile scores based on real data
        profile_scores = {
            'code_quality': min(100, github_data['score'] + 10),  # GitHub score + bonus
            'activity_level': github_data['contributions_progress'],
            'project_complexity': min(100, github_data['repos_progress'] + 15),
            'problem_solving': leetcode_data['solved_progress'],
            'algorithmic_thinking': leetcode_data['rating_progress'],
        }
        
        # Ensure all scores are integers
        for key in profile_scores:
            profile_scores[key] = int(profile_scores[key])
        
        processed_applications.append({
            'application': app,
            'company_name': company_name,
            'match_scores': {
                'overall': int(overall_score),
                'technical': int(skill_score),
                'skills': int(skill_score),
                'experience': int(experience_score),
                'location': int(location_score),
                'salary': int(salary_score) if salary_score else 0,
            },
            'profile_scores': profile_scores,
            'matched_skills': match_analysis.get('matched_skills', []),
            'missing_skills': match_analysis.get('missing_skills', []),
            'match_category': match_analysis.get('match_category', 'Fair Match'),
            'status_display': {
                'applied': {'class': 'bg-blue-100 text-blue-700', 'text': 'Under Review'},
                'under_review': {'class': 'bg-yellow-100 text-yellow-700', 'text': 'In Progress'},
                'interview': {'class': 'bg-green-100 text-green-700', 'text': 'Interview'},
                'hired': {'class': 'bg-green-100 text-green-700', 'text': 'Hired'},
                'rejected': {'class': 'bg-red-100 text-red-700', 'text': 'Not Selected'},
            }.get(app.status, {'class': 'bg-gray-100 text-gray-700', 'text': 'Unknown'})
        })
    
    # Calculate real statistics
    total_applications = applications.count()
    under_review = applications.filter(status__in=['applied', 'under_review', 'interview']).count()
    avg_match_score = int(sum(total_match_scores) / len(total_match_scores)) if total_match_scores else 0
    avg_technical_score = int(sum(technical_scores) / len(technical_scores)) if technical_scores else 0
    
    context = {
        'applications': processed_applications,
        'total_applications': total_applications,
        'under_review': under_review,
        'avg_match_score': avg_match_score,
        'technical_score': avg_technical_score,
    }
    
    return render(request, 'developer/application.html', context)

# 'you'll need to implement match scoring logic)
#     avg_match_score = 82  # Placeholder - implement your matching algorithm
#     technical_score = 85   # Placeholder - calculate from profile analysis
    
#     # Process applications for display
#     processed_applications = []
#     for app in applications:
#         # Get company name from recruiter profile
#         company_name = "Company Name"
#         try:
#             if hasattr(app.job.recruiter, 'recruiterprofile'):
#                 company_name = app.job.recruiter.recruiterprofile.company
#         except:
#             pass
        
#         # Calculate match scores (implement your matching logic here)
#         match_scores = {
#             'overall': 84 if app.status != 'rejected' else 78,
#             'technical': 92 if app.status != 'rejected' else 78,
#             'skills': 90 if app.status != 'rejected' else 80,
#             'experience': 85 if app.status != 'rejected' else 75,
#         }
        
#         # Profile analysis scores
#         profile_scores = {
#             'code_quality': 91 if app.status != 'rejected' else 82,
#             'activity_level': 85 if app.status != 'rejected' else 71,
#             'project_complexity': 89 if app.status != 'rejected' else 75,
#             'problem_solving': 87 if app.status != 'rejected' else 74,
#             'algorithmic_thinking': 84 if app.status != 'rejected' else 79,
#         }
        
#         processed_applications.append({
#             'application': app,
#             'company_name': company_name,
#             'match_scores': match_scores,
#             'profile_scores': profile_scores,
#             'status_display': {
#                 'applied': {'class': 'bg-blue-100 text-blue-700', 'text': 'Under Review'},
#                 'under_review': {'class': 'bg-yellow-100 text-yellow-700', 'text': 'In Progress'},
#                 'interview': {'class': 'bg-green-100 text-green-700', 'text': 'Interview'},
#                 'hired': {'class': 'bg-green-100 text-green-700', 'text': 'Hired'},
#                 'rejected': {'class': 'bg-red-100 text-red-700', 'text': 'Not Selected'},
#             }.get(app.status, {'class': 'bg-gray-100 text-gray-700', 'text': 'Unknown'})
#         })
    
#     context = {
#         'applications': processed_applications,
#         'total_applications': total_applications,
#         'under_review': under_review,
#         'avg_match_score': avg_match_score,
#         'technical_score': technical_score,
#     }
    
#     return render(request, 'developer/application.html', context)