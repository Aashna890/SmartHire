from django.db import models
from django.conf import settings

JOB_TYPE_CHOICES = [
    ('full-time', 'Full-time'),
    ('part-time', 'Part-time'),
    ('contract', 'Contract'),
    ('internship', 'Internship'),
]

STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('published', 'Published'),
]

class Job(models.Model):
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, null=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full-time')
    location = models.CharField(max_length=255, blank=True, null=True)
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    requirements = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
# Add this to your jobs/models.py file


from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Application(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('interview', 'Interview'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]
    
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='applications')
    developer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)  # For internal recruiter notes
    
    class Meta:
        unique_together = ('job', 'developer')  # Prevent duplicate applications
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.developer.email} - {self.job.title}"
    
    @property
    def days_since_applied(self):
        return (timezone.now() - self.applied_at).days