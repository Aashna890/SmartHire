from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .models import User
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import DeveloperProfile
from django.core.files import File
from django.conf import settings
import os
import requests
from .utils import get_github_data, get_leetcode_data  # import above functions
import re
from django.db import transaction
from .models import RecruiterProfile
from .utils import extract_skills_from_resume
from resume import ResumeParser  # Import the resume parser

# password for developer Password123#

User = get_user_model()

def developer_signup(request):
    return render(request,'developer/signup_1.html')

# Helper: Store file temporarily
def handle_uploaded_file(f):
    tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f.name)
    with open(tmp_path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return tmp_path

def signup_step1(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        # ✅ Email check
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please log in.")
            return redirect('signup_step1')

        # Save Step 1 data in session
        request.session['signup_data'] = {
            'email': email,
            'password': request.POST.get('password'),
            'username': request.POST.get('username'),
            'phone': request.POST.get('phone'),
            'location': request.POST.get('location'),
            'title': request.POST.get('title'),
            'experience': request.POST.get('experience'),
            'salary': request.POST.get('salary'),
            'summary': request.POST.get('summary'),
        }

        # Store resume file temporarily and parse it
        resume_file = request.FILES.get('resume')
        if resume_file:
            tmp_path = handle_uploaded_file(resume_file)
            request.session['resume_path'] = tmp_path
            request.session['resume_name'] = resume_file.name
            
            # Parse the resume immediately after upload
            try:
                parser = ResumeParser()
                parsed_resume = parser.parse_resume(tmp_path)
                
                # Store parsed data in session
                request.session['parsed_resume_data'] = {
                    'skills': parsed_resume.skills or [],
                    'technical_skills': parsed_resume.technical_skills or [],
                    'soft_skills': parsed_resume.soft_skills or [],
                    'work_experience': [
                        {
                            'job_title': exp.job_title,
                            'company': exp.company,
                            'duration': exp.duration,
                            'start_date': exp.start_date,
                            'end_date': exp.end_date,
                            'description': exp.description,
                            'responsibilities': exp.responsibilities or [],
                            'experience_type': exp.experience_type,
                            'location': exp.location,
                            'is_current': exp.is_current
                        } for exp in (parsed_resume.work_experience or [])
                    ],
                    'internship_experience': [
                        {
                            'job_title': exp.job_title,
                            'company': exp.company,
                            'duration': exp.duration,
                            'start_date': exp.start_date,
                            'end_date': exp.end_date,
                            'description': exp.description,
                            'responsibilities': exp.responsibilities or [],
                            'experience_type': exp.experience_type,
                            'location': exp.location,
                            'is_current': exp.is_current
                        } for exp in (parsed_resume.internship_experience or [])
                    ],
                    'education': [
                        {
                            'degree': edu.degree,
                            'institution': edu.institution,
                            'year': edu.year,
                            'gpa': edu.gpa,
                            'field_of_study': edu.field_of_study
                        } for edu in (parsed_resume.education or [])
                    ],
                    'years_of_experience': parsed_resume.years_of_experience or 0,
                    'total_internship_months': parsed_resume.total_internship_months or 0,
                    'contact_info': {
                        'name': parsed_resume.contact_info.name,
                        'email': parsed_resume.contact_info.email,
                        'phone': parsed_resume.contact_info.phone,
                        'address': parsed_resume.contact_info.address,
                        'linkedin': parsed_resume.contact_info.linkedin,
                        'github': parsed_resume.contact_info.github,
                        'website': parsed_resume.contact_info.website
                    },
                    'extracted_summary': parsed_resume.summary,
                    'certifications': parsed_resume.certifications or [],
                    'projects': parsed_resume.projects or [],
                    'languages': parsed_resume.languages or []
                }
                
                messages.success(request, "Resume parsed successfully! Review the extracted information in the next steps.")
                
            except Exception as e:
                messages.warning(request, f"Resume uploaded but parsing failed: {str(e)}. You can still continue with manual entry.")
                request.session['parsed_resume_data'] = {}

        request.session.modified = True
        return redirect('signup_step2')

    return render(request, 'developer/signup_1.html')


def is_leetcode_url(url):
    pattern = r'^https://leetcode\.com/u/[A-Za-z0-9_-]+/?$'
    return re.match(pattern, url) is not None

def is_github_url(url):
    pattern = r'^https://github\.com/[A-Za-z0-9_-]+/?$'
    return re.match(pattern, url) is not None


def signup_step2(request):
    if request.method == 'POST':
        github_url = request.POST.get('github_url', '').strip()
        leetcode_url = request.POST.get('leetcode_url', '').strip()

        if not is_github_url(github_url):
            messages.error(request, 'Enter a valid GitHub profile URL.')
            return render(request, 'developer/signup_2.html', {
                'github_url': github_url, 
                'leetcode_url': leetcode_url
            })

        if not is_leetcode_url(leetcode_url):
            messages.error(request, 'Enter a valid LeetCode profile URL.')
            return render(request, 'developer/signup_2.html', {
                'github_url': github_url, 
                'leetcode_url': leetcode_url
            })

        # Store in session
        signup_data = request.session.get('signup_data', {})
        signup_data['github_url'] = github_url
        signup_data['leetcode_url'] = leetcode_url
        request.session['signup_data'] = signup_data
        request.session.modified = True

        return redirect('signup_step3')

    return render(request, 'developer/signup_2.html')

def extract_github_username(url):
    """
    Extracts the GitHub username from a profile URL.
    Example: https://github.com/SunilSaini123 -> SunilSaini123
    """
    match = re.search(r'github\.com/([^/]+)/?', url)
    if match:
        return match.group(1)
    return None

def extract_leetcode_username(url):
    """
    Extracts the LeetCode username from a profile URL.
    """
    match = re.search(r'leetcode\.com/(?:u|profile)/([^/]+)/?', url)
    if match:
        return match.group(1)
    return None

def signup_step3(request):
    signup_data = request.session.get('signup_data', {})
    parsed_resume_data = request.session.get('parsed_resume_data', {})
    resume_name = request.session.get('resume_name', None)
    resume_path = request.session.get('resume_path', None)

    # Fetch URLs from session
    github_url = signup_data.get('github_url')
    leetcode_url = signup_data.get('leetcode_url')

    # Extract usernames
    github_username = extract_github_username(github_url) if github_url else None
    leetcode_username = extract_leetcode_username(leetcode_url) if leetcode_url else None

    # Fetch GitHub and LeetCode data
    github_data = get_github_data(github_username) if github_username else {}
    leetcode_data = get_leetcode_data(leetcode_username) if leetcode_username else {}

    if request.method == 'POST':
        # Check if email exists
        if User.objects.filter(email=signup_data['email']).exists():
            messages.error(request, "Email already registered. Please log in.")
            return redirect('signup_step1')

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=signup_data['email'],
                    password=signup_data['password'],
                    user_type='developer'
                )

                # Prepare enhanced profile data with parsed resume information
                profile_data = {
                    'user': user,
                    'username': signup_data['username'],
                    'phone': signup_data.get('phone') or parsed_resume_data.get('contact_info', {}).get('phone', ''),
                    'location': signup_data['location'],
                    'title': signup_data['title'],
                    'experience': signup_data['experience'],
                    'salary': signup_data.get('salary'),
                    'summary': signup_data.get('summary') or parsed_resume_data.get('extracted_summary', ''),
                    'github_url': github_url,
                    'leetcode_url': leetcode_url,
                    'skills': parsed_resume_data.get('skills', [])
                }

                # Create profile with resume file if available
                if resume_path and os.path.exists(resume_path):
                    with open(resume_path, 'rb') as f:
                        profile = DeveloperProfile.objects.create(**profile_data)
                        profile.resume.save(resume_name, File(f), save=True)
                else:
                    profile = DeveloperProfile.objects.create(**profile_data)

                # Store additional parsed data in profile's extended fields (if you have them)
                # You might want to add these fields to your DeveloperProfile model:
                # - parsed_work_experience (JSONField)
                # - parsed_education (JSONField)
                # - years_of_experience (IntegerField)
                # - total_internship_months (IntegerField)
                
                # Auto-login
                login(request, user)

                # Cleanup session and temp file
                request.session.pop('signup_data', None)
                request.session.pop('resume_name', None)
                request.session.pop('resume_path', None)
                request.session.pop('parsed_resume_data', None)
                
                if resume_path and os.path.exists(resume_path):
                    os.remove(resume_path)

                messages.success(request, "Account created successfully with parsed resume data!")
                return redirect('developer:dashboard')
                
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return redirect('signup_step1')

    # Merge signup data with parsed resume data for display
    display_data = signup_data.copy()
    if parsed_resume_data:
        contact_info = parsed_resume_data.get('contact_info', {})
        # Enhance display data with parsed information
        if not display_data.get('phone') and contact_info.get('phone'):
            display_data['suggested_phone'] = contact_info['phone']
        if not display_data.get('summary') and parsed_resume_data.get('extracted_summary'):
            display_data['suggested_summary'] = parsed_resume_data['extracted_summary']

    return render(request, 'developer/signup_3.html', {
        'data': display_data,
        'github_data': github_data,
        'leetcode_data': leetcode_data,
        'parsed_resume_data': parsed_resume_data,
        'skills_count': len(parsed_resume_data.get('skills', [])),
        'work_experience_count': len(parsed_resume_data.get('work_experience', [])),
        'internship_count': len(parsed_resume_data.get('internship_experience', [])),
        'education_count': len(parsed_resume_data.get('education', []))
    })


def developer_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        print(f"Login attempt - Email: {email}")

        user = authenticate(request, email=email, password=password)

        if user and user.user_type == 'developer':
            login(request, user)
            
            # # Optional: Re-parse resume on login if needed for updates
            # try:
            #     profile = user.developerprofile
            #     if profile.resume and not profile.skills:
            #         # If skills are empty, try to parse resume again
            #         resume_path = profile.resume.path
            #         parser = ResumeParser()
            #         parsed_resume = parser.parse_resume(resume_path)
                    
            #         # Update profile with parsed skills
            #         profile.skills = parsed_resume.skills or []
            #         profile.save()
                    
            #         messages.info(request, "Profile updated with parsed resume data.")
                    
            # except Exception as e:
            #     print(f"Error re-parsing resume on login: {e}")
            
            return redirect('developer:dashboard')
        else:
            messages.error(request, 'Invalid email, password, or account type.')

    return render(request, 'dev_signin.html')


# Recruiter views remain the same
def recruiter_signup(request):
    return render(request,'recruiter/signup.html')

def recruiter_signup1(request):
    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('firstName')
        last_name = request.POST.get('lastName')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        company = request.POST.get('company')
        industry = request.POST.get('industry')
        password = request.POST.get('password')

        # Create User
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type='recruiter'
        )
        
        print(user)
        # Generate unique username for RecruiterProfile
        base_username = f"{first_name.lower()}.{last_name.lower()}"
        username = base_username
        counter = 1
        while RecruiterProfile.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create RecruiterProfile
        RecruiterProfile.objects.create(
            user=user,
            username=username,
            phone=phone,
            company=company,
            industry=industry
        )

        # Add success message and redirect to dashboard
        messages.success(request, "Registration successful!")
        return redirect('recruiter_login')

    # For GET requests, render the empty form
    return render(request, 'recruiter/signup.html', {})

def recruiter_login(request):
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['email'], password=request.POST['password'])
        if user and user.user_type == 'recruiter':
            login(request, user)
            return redirect('recruiter:dashboard')
    return render(request, 'rec_signin.html')

def logout_view(request):
    logout(request)
    return redirect('index')