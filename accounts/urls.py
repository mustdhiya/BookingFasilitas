from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # API
    path('register/',        views.register_view,         name='register'),
    path('login/',           views.login_view,             name='login'),
    path('logout/',          views.logout_view,            name='logout'),
    path('profile/',         views.profile_view,           name='profile'),
    path('profile/update/',  views.profile_update_view,    name='profile-update'),
    path('change-password/', views.change_password_view,   name='change-password'),
    path('login-history/',   views.login_history_view,     name='login-history'),
]
