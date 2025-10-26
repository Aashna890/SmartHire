from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Job
from accounts.models import DeveloperProfile
import json
from django.db.models import Q
from datetime import datetime, timedelta
import re
from collections import Counter
import math


@login_required
def create_job(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        department = request.POST.get('department')
        job_type = request.POST.get('job_type')
        location = request.POST.get('location')
        salary_min = request.POST.get('salary_min') or None
        salary_max = request.POST.get('salary_max') or None
        description = request.POST.get('description')
        requirements = json.loads(request.POST.get('requirements', '[]'))
        benefits = json.loads(request.POST.get('benefits', '[]'))
        status = request.POST.get('status', 'draft')

        Job.objects.create(
            recruiter=request.user,
            title=title,
            department=department,
            job_type=job_type,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            description=description,
            requirements=requirements,
            benefits=benefits,
            status=status
        )
        return redirect('recruiter:dashboard')
    return redirect('recruiter:dashboard')


class JobMatchingAI:
    """AI-powered job matching system using multiple scoring algorithms"""
    
    def __init__(self):
        # Experience level mappings
        self.experience_levels = {
            'entry': ['intern', 'junior', 'entry', 'graduate', 'trainee', '0-1', '0-2'],
            'mid': ['mid', 'intermediate', '2-5', '3-5', '2-4'],
            'senior': ['senior', 'lead', 'principal', '5+', '5-8', '6+'],
            'expert': ['expert', 'architect', 'director', '8+', '10+', 'staff']
        }
        
        # Skill category weights for different job types
        self.skill_weights = {
            'frontend': {
                'react': 1.5, 'vue': 1.5, 'angular': 1.5, 'javascript': 1.8, 'typescript': 1.6,
                'html': 1.2, 'css': 1.2, 'sass': 1.1, 'bootstrap': 1.0
            },
            'backend': {
                'python': 1.6, 'java': 1.6, 'node.js': 1.5, 'django': 1.4, 'flask': 1.3,
                'spring': 1.4, 'express': 1.3, 'php': 1.2, 'laravel': 1.2
            },
            'fullstack': {
                'javascript': 1.4, 'python': 1.4, 'react': 1.3, 'node.js': 1.3,
                'django': 1.2, 'mongodb': 1.1, 'postgresql': 1.1
            },
            'data': {
                'python': 1.8, 'pandas': 1.6, 'numpy': 1.5, 'scikit-learn': 1.5,
                'tensorflow': 1.7, 'pytorch': 1.7, 'sql': 1.4, 'r': 1.3
            },
            'mobile': {
                'react native': 1.6, 'flutter': 1.6, 'swift': 1.5, 'kotlin': 1.5,
                'java': 1.3, 'objective-c': 1.2
            },
            'devops': {
                'docker': 1.6, 'kubernetes': 1.6, 'aws': 1.5, 'jenkins': 1.4,
                'terraform': 1.4, 'ansible': 1.3, 'linux': 1.3
            }
        }

    def extract_experience_level(self, text):
        """Extract experience level from job title or description"""
        text_lower = text.lower()
        
        for level, keywords in self.experience_levels.items():
            if any(keyword in text_lower for keyword in keywords):
                return level
        
        # Default based on common patterns
        if any(word in text_lower for word in ['intern', 'graduate', 'entry', 'junior']):
            return 'entry'
        elif any(word in text_lower for word in ['senior', 'lead', 'principal']):
            return 'senior'
        elif any(word in text_lower for word in ['architect', 'director', 'staff']):
            return 'expert'
        else:
            return 'mid'

    def calculate_skill_match_score(self, user_skills, job_requirements, job_title):
        """Calculate skill matching score with weighted importance"""
        if not user_skills or not job_requirements:
            return 0.0
        
        user_skills_lower = [skill.lower() for skill in user_skills]
        job_requirements_lower = [req.lower() for req in job_requirements]
        
        # Determine job category for weighted scoring
        job_category = self.determine_job_category(job_title)
        weights = self.skill_weights.get(job_category, {})
        
        matched_skills = []
        total_weight = 0
        matched_weight = 0
        
        for req in job_requirements_lower:
            weight = weights.get(req, 1.0)  # Default weight is 1.0
            total_weight += weight
            
            # Exact match
            if req in user_skills_lower:
                matched_skills.append(req)
                matched_weight += weight
            # Partial/similar match
            else:
                similarity_score = self.calculate_skill_similarity(req, user_skills_lower)
                if similarity_score > 0.7:
                    matched_skills.append(req)
                    matched_weight += weight * similarity_score
        
        # Calculate percentage match with weighted scoring
        if total_weight == 0:
            return 0.0
        
        skill_match_percentage = (matched_weight / total_weight) * 100
        return min(skill_match_percentage, 100.0)

    def calculate_skill_similarity(self, target_skill, user_skills):
        """Calculate similarity between skills using string matching"""
        target_lower = target_skill.lower()
        
        for user_skill in user_skills:
            user_lower = user_skill.lower()
            
            # Exact match
            if target_lower == user_lower:
                return 1.0
            
            # Substring match
            if target_lower in user_lower or user_lower in target_lower:
                return 0.8
            
            # Similar technologies (you can expand this mapping)
            similar_skills = {
                'react': ['reactjs', 'react.js'],
                'node': ['nodejs', 'node.js'],
                'javascript': ['js', 'ecmascript'],
                'typescript': ['ts'],
                'python': ['py'],
                'postgresql': ['postgres', 'psql'],
                'mongodb': ['mongo'],
                'machine learning': ['ml', 'artificial intelligence', 'ai'],
            }
            
            for key, variants in similar_skills.items():
                if (target_lower == key and user_lower in variants) or \
                   (target_lower in variants and user_lower == key):
                    return 0.9
        
        return 0.0

    def determine_job_category(self, job_title):
        """Determine job category from title for weighted scoring"""
        title_lower = job_title.lower()
        
        if any(word in title_lower for word in ['frontend', 'front-end', 'ui', 'react', 'vue', 'angular']):
            return 'frontend'
        elif any(word in title_lower for word in ['backend', 'back-end', 'api', 'server']):
            return 'backend'
        elif any(word in title_lower for word in ['fullstack', 'full-stack', 'full stack']):
            return 'fullstack'
        elif any(word in title_lower for word in ['data', 'ml', 'machine learning', 'ai', 'scientist', 'analyst']):
            return 'data'
        elif any(word in title_lower for word in ['mobile', 'android', 'ios', 'flutter', 'react native']):
            return 'mobile'
        elif any(word in title_lower for word in ['devops', 'sre', 'infrastructure', 'cloud', 'deployment']):
            return 'devops'
        else:
            return 'general'

    def calculate_experience_match(self, user_experience, job_title, job_description):
        """Calculate experience level compatibility"""
        job_exp_level = self.extract_experience_level(f"{job_title} {job_description}")
        
        # Convert user experience to years
        user_years = self.extract_years_from_experience(user_experience)
        
        # Map job requirements to year ranges
        job_year_ranges = {
            'entry': (0, 2),
            'mid': (2, 5),
            'senior': (5, 8),
            'expert': (8, 15)
        }
        
        required_min, required_max = job_year_ranges.get(job_exp_level, (0, 5))
        
        if required_min <= user_years <= required_max:
            return 100.0  # Perfect match
        elif user_years > required_max:
            # Overqualified but still good
            return max(70.0, 100.0 - (user_years - required_max) * 5)
        else:
            # Underqualified
            gap = required_min - user_years
            return max(30.0, 100.0 - gap * 20)

    def extract_years_from_experience(self, experience_str):
        """Extract years of experience from string"""
        if not experience_str:
            return 0
        
        # Look for patterns like "3 years", "2-5 years", "5+ years"
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)-\d+\s*years?',
            r'(\d+)\s*yrs?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, experience_str.lower())
            if match:
                return int(match.group(1))
        
        # Default mapping for common phrases
        experience_mapping = {
            'entry': 0, 'junior': 1, 'mid': 3, 'intermediate': 3,
            'senior': 6, 'lead': 7, 'principal': 8, 'expert': 10
        }
        
        for key, years in experience_mapping.items():
            if key in experience_str.lower():
                return years
        
        return 2  # Default assumption

    def calculate_location_score(self, user_location, job_location, job_type):
        """Calculate location compatibility score"""
        if not user_location or not job_location:
            return 50.0  # Neutral score for missing data
        
        user_loc_lower = user_location.lower()
        job_loc_lower = job_location.lower()
        
        # Remote work gets high score regardless of location
        if 'remote' in job_loc_lower or job_type.lower() == 'remote':
            return 100.0
        
        # Exact city match
        if user_loc_lower in job_loc_lower or job_loc_lower in user_loc_lower:
            return 100.0
        
        # Same country/region (basic implementation - you can enhance this)
        # You might want to integrate with a geocoding API for better location matching
        common_locations = ['india', 'usa', 'uk', 'canada', 'australia', 'germany']
        for location in common_locations:
            if location in user_loc_lower and location in job_loc_lower:
                return 70.0
        
        return 30.0  # Different locations

    def calculate_salary_score(self, user_expected_salary, job_salary_min, job_salary_max):
        """Calculate salary compatibility score"""
        if not user_expected_salary or not job_salary_min:
            return 50.0  # Neutral score for missing data
        
        user_salary = float(user_expected_salary)
        job_min = float(job_salary_min)
        job_max = float(job_salary_max) if job_salary_max else job_min * 1.5
        
        if job_min <= user_salary <= job_max:
            return 100.0  # Perfect salary match
        elif user_salary < job_min:
            # Salary is lower than expected, still good opportunity
            gap_percentage = ((job_min - user_salary) / user_salary) * 100
            return max(60.0, 100.0 - gap_percentage / 2)
        else:
            # User expects more than offered
            gap_percentage = ((user_salary - job_max) / job_max) * 100
            return max(20.0, 100.0 - gap_percentage)

    def calculate_comprehensive_match_score(self, user_profile, job):
        """Calculate comprehensive matching score using multiple factors"""
        
        # Extract user data
        user_skills = user_profile.skills or []
        user_experience = user_profile.experience or ""
        user_location = user_profile.location or ""
        user_salary = user_profile.salary
        
        # Extract job data
        job_requirements = job.requirements or []
        job_title = job.title or ""
        job_description = job.description or ""
        job_location = job.location or ""
        job_type = job.job_type or ""
        job_salary_min = job.salary_min
        job_salary_max = job.salary_max
        
        # Calculate individual scores
        skill_score = self.calculate_skill_match_score(user_skills, job_requirements, job_title)
        experience_score = self.calculate_experience_match(user_experience, job_title, job_description)
        location_score = self.calculate_location_score(user_location, job_location, job_type)
        salary_score = self.calculate_salary_score(user_salary, job_salary_min, job_salary_max)
        
        # Weighted combination of scores
        weights = {
            'skills': 0.4,      # 40% - Most important
            'experience': 0.25, # 25% - Very important
            'location': 0.20,   # 20% - Important for logistics
            'salary': 0.15      # 15% - Important but negotiable
        }
        
        final_score = (
            skill_score * weights['skills'] +
            experience_score * weights['experience'] +
            location_score * weights['location'] +
            salary_score * weights['salary']
        )
        
        return {
            'overall_score': round(final_score, 2),
            'skill_score': round(skill_score, 2),
            'experience_score': round(experience_score, 2),
            'location_score': round(location_score, 2),
            'salary_score': round(salary_score, 2),
            'matched_skills': self.get_matched_skills(user_skills, job_requirements),
            'missing_skills': self.get_missing_skills(user_skills, job_requirements),
            'match_category': self.categorize_match(final_score)
        }
    
    def get_matched_skills(self, user_skills, job_requirements):
        """Get list of skills that match between user and job"""
        if not user_skills or not job_requirements:
            return []
        
        user_skills_lower = [skill.lower() for skill in user_skills]
        job_requirements_lower = [req.lower() for req in job_requirements]
        
        matched = []
        for req in job_requirements_lower:
            if req in user_skills_lower:
                matched.append(req)
            else:
                # Check for similar skills
                for user_skill in user_skills_lower:
                    if self.calculate_skill_similarity(req, [user_skill]) > 0.7:
                        matched.append(f"{req} (similar to {user_skill})")
                        break
        
        return matched
    
    def get_missing_skills(self, user_skills, job_requirements):
        """Get list of skills required by job but missing from user profile"""
        if not job_requirements:
            return []
        if not user_skills:
            return job_requirements
        
        user_skills_lower = [skill.lower() for skill in user_skills]
        job_requirements_lower = [req.lower() for req in job_requirements]
        
        missing = []
        for req in job_requirements_lower:
            if req not in user_skills_lower:
                # Check if there's a similar skill
                has_similar = any(
                    self.calculate_skill_similarity(req, [user_skill]) > 0.7
                    for user_skill in user_skills_lower
                )
                if not has_similar:
                    missing.append(req)
        
        return missing
    
    def categorize_match(self, score):
        """Categorize match quality based on score"""
        if score >= 85:
            return "Excellent Match"
        elif score >= 70:
            return "Good Match"
        elif score >= 55:
            return "Fair Match"
        elif score >= 40:
            return "Potential Match"
        else:
            return "Poor Match"


@login_required
def find_jobs(request):
    """AI-powered job recommendation system"""
    try:
        profile = DeveloperProfile.objects.get(user=request.user)
    except DeveloperProfile.DoesNotExist:
        return render(request, "developer/find_jobs.html", {
            "error": "Please complete your profile first to get job recommendations."
        })
    
    # Get all active jobs
    jobs = Job.objects.filter(status='published').select_related('recruiter')
    
    # Initialize AI matching system
    ai_matcher = JobMatchingAI()
    
    # Calculate match scores for all jobs
    job_matches = []
    for job in jobs:
        match_data = ai_matcher.calculate_comprehensive_match_score(profile, job)
        job_matches.append({
            'job': job,
            'match_data': match_data
        })
    
    # Sort by overall match score (descending)
    job_matches.sort(key=lambda x: x['match_data']['overall_score'], reverse=True)
    
    # Categorize jobs by match quality
    excellent_matches = [jm for jm in job_matches if jm['match_data']['overall_score'] >= 85]
    good_matches = [jm for jm in job_matches if 70 <= jm['match_data']['overall_score'] < 85]
    fair_matches = [jm for jm in job_matches if 55 <= jm['match_data']['overall_score'] < 70]
    potential_matches = [jm for jm in job_matches if 40 <= jm['match_data']['overall_score'] < 55]
    
    # Get top recommendations (limit to prevent overwhelm)
    top_recommendations = job_matches[:20]  # Top 20 matches
    
    # Calculate user statistics
    user_stats = {
        'total_skills': len(profile.skills) if profile.skills else 0,
        'experience_level': ai_matcher.extract_experience_level(profile.experience or ""),
        'location': profile.location,
        'preferred_salary': profile.salary
    }
    
    context = {
        'top_recommendations': top_recommendations,
        'excellent_matches': excellent_matches[:10],  # Limit to 10 each
        'good_matches': good_matches[:10],
        'fair_matches': fair_matches[:10],
        'potential_matches': potential_matches[:5],
        'user_stats': user_stats,
        'total_jobs_analyzed': len(jobs),
        'profile': profile
    }
    
    return render(request, "developer/find_jobs.html", context)


@login_required
def job_detail_with_analysis(request, job_id):
    """Detailed job view with AI analysis"""
    try:
        job = Job.objects.get(id=job_id)
        profile = DeveloperProfile.objects.get(user=request.user)
        ai_matcher = JobMatchingAI()
        match_analysis = ai_matcher.calculate_comprehensive_match_score(profile, job)

        # Skill gap recommendations
        recommendations = []
        missing_skills = match_analysis.get('missing_skills', [])
        if missing_skills:
            recommendations.append({
                'type': 'Skill Gap',
                'message': f"Consider learning: {', '.join(missing_skills)}"
            })

        context = {
            'job': job,
            'profile': profile,
            'match_analysis': match_analysis,
            'recommendations': recommendations
        }
        return render(request, "developer/job_detail.html", context)

    except Job.DoesNotExist:
        return redirect('developer:find_jobs')
