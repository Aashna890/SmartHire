from django.urls import path
from . import views

app_name = 'developer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path("applications/", views.my_applications, name="applications"),
    path("apply/<int:job_id>/", views.apply_to_job, name="apply_to_job"),
]