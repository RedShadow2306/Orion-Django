from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/health/', views.health, name='health'),
    path('api/quizzes/', views.create_quiz, name='create_quiz'),
    path('api/questions/bulk/', views.bulk_questions, name='bulk_questions'),
    path('api/sessions/', views.create_session, name='create_session'),
    path('api/sessions/<str:join_code>/', views.get_session, name='get_session'),
    path('api/sessions/<str:join_code>/status/', views.session_status, name='session_status'),
    path('api/sessions/<str:join_code>/start/', views.start_session, name='start_session'),
    path('api/sessions/<str:join_code>/questions/', views.get_questions, name='get_questions'),
    path('api/join-session/', views.join_session, name='join_session'),
    path('api/responses/', views.submit_response, name='submit_response'),
    path('api/leaderboard/by-code/<str:join_code>/', views.leaderboard, name='leaderboard'),
]
