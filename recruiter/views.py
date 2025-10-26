# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, get_object_or_404, redirect
# from django.http import JsonResponse
# from django.contrib import messages
# from django.views.decorators.http import require_POST
# from jobs.models import Job, Application
# from accounts.models import DeveloperProfile
# from django.db.models import Count, Q
# import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from jobs.models import Job, Application
from jobs.views import JobMatchingAI  # Import your existing AI matcher
from accounts.models import DeveloperProfile, User
from django.db.models import Count, Q
import json


# Simple matching class if JobMatchingAI is not available
class SimpleJobMatcher:
    def calculate_comprehensive_match_score(self, profile, job):
        """Simple matching algorithm"""
        score = 0
        max_score = 100
        
        # Check skills match
        if hasattr(profile, 'skills') and profile.skills:
            job_requirements = job.requirements if job.requirements else []
            profile_skills = [skill.lower() for skill in profile.skills]
            job_skills = [req.lower() for req in job_requirements]
            
            matched_skills = len(set(profile_skills) & set(job_skills))
            total_required = len(job_skills) if job_skills else 1
            skill_score = (matched_skills / total_required) * 70
            score += min(skill_score, 70)
        
        # Location match
        if hasattr(profile, 'location') and profile.location and job.location:
            if profile.location.lower() in job.location.lower():
                score += 15
        
        # Add base score for having a complete profile
        score += 15
        
        return {
            'overall_score': min(score, max_score),
            'skill_match': min(skill_score if 'skill_score' in locals() else 0, 70),
            'location_match': 15 if hasattr(profile, 'location') and profile.location and job.location and profile.location.lower() in job.location.lower() else 0,
        }
@login_required
def dashboard(request):
    recruiter = request.user
    jobs = Job.objects.filter(recruiter=recruiter).order_by('-created_at')

    # Annotate application counts for each job
    for job in jobs:
        job.total_applications = job.applications.count()
        job.applied_count = job.applications.filter(status="applied").count()
        job.shortlisted_count = job.applications.filter(status="shortlisted").count()
        job.rejected_count = job.applications.filter(status="rejected").count()

    total_jobs = jobs.count()
    published_jobs = jobs.filter(status='published').count()
    total_applications = sum(job.total_applications for job in jobs)
    avg_applications = total_applications // total_jobs if total_jobs else 0

    context = {
        'jobs': jobs,
        'total_jobs': total_jobs,
        'published_jobs': published_jobs,
        'total_applications': total_applications,
        'avg_applications': avg_applications,
    }
    return render(request, 'recruiter/dashboard.html', context)



@login_required
def all_candidates(request):
    """Display all candidates who applied to recruiter's jobs with AI analysis"""
    recruiter = request.user
    
    # Get all applications for this recruiter's jobs
    applications = Application.objects.filter(
        job__recruiter=recruiter
    ).select_related(
        'job', 'developer'
    ).order_by('-applied_at')
    
    # Calculate statistics
    stats = {
        'applied': applications.filter(status='applied').count(),
        'under_review': applications.filter(status='under_review').count(),
        'interview': applications.filter(status='interview').count(),
        'hired': applications.filter(status='hired').count(),
        'rejected': applications.filter(status='rejected').count(),
    }
    
    # Initialize AI matching system (use your existing JobMatchingAI)
    ai_matcher = JobMatchingAI()
    
    # Process applications with analysis
    processed_applications = []
    for app in applications:
        # Try to get developer profile, create basic one if doesn't exist
        try:
            profile = DeveloperProfile.objects.get(user=app.developer)
        except DeveloperProfile.DoesNotExist:
            # Create a basic profile object for display
            profile = type('Profile', (), {
                'username': app.developer.email.split('@')[0],  # Use email prefix as fallback
                'title': 'Developer',
                'location': 'Not specified',
                'skills': [],
            })()
        
        # Calculate match score using AI
        match_analysis = ai_matcher.calculate_comprehensive_match_score(profile, app.job)
        
        # Get candidate skills
        candidate_skills = getattr(profile, 'skills', []) or []
        if isinstance(candidate_skills, str):
            try:
                candidate_skills = json.loads(candidate_skills)
            except:
                candidate_skills = []
        
        processed_applications.append({
            'application': app,
            'profile': profile,
            'match_score': int(match_analysis.get('overall_score', 0)),
            'skills': candidate_skills[:4] if candidate_skills else [],
            'extra_skills_count': max(0, len(candidate_skills) - 4) if candidate_skills else 0,
            'match_analysis': match_analysis,
        })
    
    # Sort by match score (highest first)
    processed_applications.sort(key=lambda x: x['match_score'], reverse=True)
    
    context = {
        'applications': processed_applications,
        'stats': stats,
        'total_candidates': len(processed_applications),
    }
    
    return render(request, 'recruiter/all_candidates.html', context)


@login_required
def candidate_detail(request, application_id):
    """Detailed view of a specific candidate application"""
    application = get_object_or_404(
        Application.objects.select_related('job', 'developer'),
        id=application_id,
        job__recruiter=request.user
    )
    
    try:
        profile = DeveloperProfile.objects.get(user=application.developer)
    except DeveloperProfile.DoesNotExist:
        messages.error(request, "Candidate profile not found.")
        return redirect('recruiter:all_candidates')
    
    # Initialize matching system (use your existing JobMatchingAI)
    ai_matcher = JobMatchingAI()
    match_analysis = ai_matcher.calculate_comprehensive_match_score(profile, application.job)
    
    context = {
        'application': application,
        'profile': profile,
        'match_analysis': match_analysis,
        'job': application.job,
    }
    
    return render(request, 'recruiter/candidate_detail.html', context)


@login_required
@require_POST
def update_application_status(request, application_id):
    """Update the status of a candidate application"""
    application = get_object_or_404(
        Application,
        id=application_id,
        job__recruiter=request.user
    )
    
    new_status = request.POST.get('status')
    notes = request.POST.get('notes', '')
    
    # Valid status options
    valid_statuses = ['applied', 'under_review', 'interview', 'hired', 'rejected']
    
    if new_status not in valid_statuses:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        messages.error(request, 'Invalid status selected.')
        return redirect('recruiter:candidate_detail', application_id=application_id)
    
    # Update application
    old_status = application.status
    application.status = new_status
    if notes:
        application.notes = notes
    application.save()
    
    status_display_names = {
        'applied': 'Applied',
        'under_review': 'Under Review',
        'interview': 'Interview Scheduled',
        'hired': 'Hired',
        'rejected': 'Rejected',
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {status_display_names.get(new_status, new_status)}',
            'new_status': new_status,
            'status_display': status_display_names.get(new_status, new_status)
        })
    
    messages.success(request, f'Application status updated to {status_display_names.get(new_status, new_status)}')
    return redirect('recruiter:candidate_detail', application_id=application_id)


@login_required
def applications_by_job(request, job_id):
    """View all applications for a specific job"""
    job = get_object_or_404(Job, id=job_id, recruiter=request.user)
    
    applications = Application.objects.filter(job=job).select_related('developer').order_by('-applied_at')
    
    # Initialize matching system
    ai_matcher =  JobMatchingAI()
    
    # Process applications with analysis
    processed_applications = []
    for app in applications:
        try:
            profile = DeveloperProfile.objects.get(user=app.developer)
        except DeveloperProfile.DoesNotExist:
            continue
        
        match_analysis = ai_matcher.calculate_comprehensive_match_score(profile, job)
        candidate_skills = getattr(profile, 'skills', []) or []
        if isinstance(candidate_skills, str):
            try:
                candidate_skills = json.loads(candidate_skills)
            except:
                candidate_skills = []
        
        processed_applications.append({
            'application': app,
            'profile': profile,
            'match_score': int(match_analysis.get('overall_score', 0)),
            'skills': candidate_skills[:4] if candidate_skills else [],
            'extra_skills_count': max(0, len(candidate_skills) - 4) if candidate_skills else 0,
            'match_analysis': match_analysis,
        })
    
    # Sort by match score
    processed_applications.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Calculate statistics for this job
    stats = {
        'applied': applications.filter(status='applied').count(),
        'under_review': applications.filter(status='under_review').count(),
        'interview': applications.filter(status='interview').count(),
        'hired': applications.filter(status='hired').count(),
        'rejected': applications.filter(status='rejected').count(),
    }
    
    context = {
        'job': job,
        'applications': processed_applications,
        'stats': stats,
        'total_applications': len(processed_applications),
    }
    
    return render(request, 'recruiter/job_applications.html', context)