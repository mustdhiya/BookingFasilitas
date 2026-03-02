from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Page Views (HTML) ──────────────────────────────────────────────
    path('login/',    views.LoginPageView.as_view(),   name='login'),
    path('register/', views.RegisterPageView.as_view(), name='register'),
    path('logout/',   views.LogoutView.as_view(),       name='logout'),
    path('profile/',  views.ProfilePageView.as_view(),  name='profile'),
    path('change-password/', views.change_password_view,   name='change_password'),

    # ── profile/update/ → arahkan ke ProfilePageView (POST handler sudah ada di sana)
    path('profile/update/', views.ProfilePageView.as_view(), name='profile_update'),

    # ── REST API (untuk Postman / mobile) ─────────────────────────────
    path('api/profile/',         views.profile_view,             name='api_profile'),
    path('api/profile/update/',  views.profile_update_view,      name='api_profile_update'),
    path('api/register/',        views.register_view,            name='api_register'),
    path('api/login/',           views.login_view,               name='api_login'),
    path('api/logout/',          views.logout_view,              name='api_logout'),
    path('api/change-password/', views.change_password_view,     name='api_change_password'),
    path('api/login-history/',   views.login_history_view,       name='api_login_history'),
    path('titles/slots/', views.TitleSlotsView.as_view(), name='title-slots'),

]
