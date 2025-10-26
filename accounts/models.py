from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager
from django.conf import settings



class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('developer', 'Developer'),
        ('recruiter', 'Recruiter'),
    )

    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class DeveloperProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    location = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    experience = models.CharField(max_length=50)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    summary = models.TextField()
    github_url = models.URLField(blank=True, null=True)
    leetcode_url = models.URLField(blank=True, null=True)
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)  # ✅ store parsed keywords

    def __str__(self):
        return self.username
    
class RecruiterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    company = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)

    def __str__(self):
        return self.username
