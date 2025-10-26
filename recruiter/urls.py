from django.urls import path
from . import views

app_name = 'recruiter'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('candidates/', views.all_candidates, name='all_candidates'),
    path('candidate/<int:application_id>/', views.candidate_detail, name='candidate_detail'),
    path('application/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),
    path('job/<int:job_id>/applications/', views.applications_by_job, name='job_applications'),
]