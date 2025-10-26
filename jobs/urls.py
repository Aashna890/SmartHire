from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('create/', views.create_job, name='create_job'),
    path('find_jobs/', views.find_jobs, name='find_jobs'),
    
]
