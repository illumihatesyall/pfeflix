from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('questionnaire/', views.questionnaire, name='questionnaire'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('rate/<str:title>/', views.rate_movie, name='rate_movie'),
    path('chatbot/', views.chatbot, name='chatbot'),
]