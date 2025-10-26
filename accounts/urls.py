from django.urls import path
from . import views

urlpatterns = [
    path('login/developer/', views.developer_login, name='developer_login'),
    path('login/recruiter/', views.recruiter_login, name='recruiter_login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/developer/', views.developer_signup, name='developer_signup'),
    path('signup/developer/step1/', views.signup_step1, name='signup_step1'),
    path('signup/developer/step2/', views.signup_step2, name='signup_step2'),
    path('signup/developer/step3/', views.signup_step3, name='signup_step3'),

    path('signup/recruiter/', views.recruiter_signup, name='recruiter_signup'),
    path('signup/recruiter/step1', views.recruiter_signup1, name='recruiter_signup1'),
]


