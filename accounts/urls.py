from django.urls import path
from . import views
from .session_views import session_check, extend_session, SessionManagementView, session_info


app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp-verify/', views.otp_verify, name='otp_verify'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('register/<str:token>/', views.register, name='register'),
    path('send-invitation/', views.send_invitation, name='send_invitation'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('change-password/', views.change_password, name='change_password'),

    path('session-check/', session_check, name='session_check'),
    path('extend-session/', extend_session, name='extend_session'),
    path('session-management/', SessionManagementView.as_view(), name='session_management'),
    path('session-info/', session_info, name='session_info'),

]