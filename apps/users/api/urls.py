from django.urls import path
from . import views
app_name = 'api-users'
urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('token/refresh/', views.RefreshAPIView.as_view(), name='refresh'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('me/', views.MeAPIView.as_view(), name='me'),
    path('profile/picture/', views.ProfilePictureAPIView.as_view(), name='profile-picture'),
    path('search/', views.UserSearchAPIView.as_view(), name='search'),
    path('password/change/', views.PasswordChangeAPIView.as_view(), name='password-change'),
]