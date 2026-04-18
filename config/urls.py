from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


# Импорт всех views
from journal.views import (
    schedule_create,
    student_list,
    teacher_dashboard, 
    lesson_grades, 
    lesson_new,
    admin_dashboard,    
    group_list,
    group_create,      
    home_redirect,
    student_create,
    teacher_create,
    teacher_list,   
    student_dashboard,
    student_schedule,
    import_schedule,
    download_template,
)

urlpatterns = [
    path('', home_redirect, name='home'),                    # ← Главная страница
    path('admin/', admin.site.urls),
    
    # Авторизация
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='login',
        http_method_names=['get', 'post']  # разрешаем и GET, и POST
    ), name='logout'),

    path('student/', student_dashboard, name='student_dashboard'),
    path('student/schedule/', student_schedule, name='student_schedule_today'),
    path('student/schedule/<str:date>/', student_schedule, name='student_schedule'),

    # Преподаватель
    path('teacher/', teacher_dashboard, name='teacher_dashboard_today'),
    path('teacher/<str:date>/', teacher_dashboard, name='teacher_dashboard'),   
    path('lesson/<int:lesson_id>/grades/', lesson_grades, name='lesson_grades'),
    path('lesson/new/', lesson_new, name='lesson_new'),
    
    # Администратор / Завуч
    path('admin-panel/', admin_dashboard, name='admin_dashboard'),
    path('admin-panel/groups/', group_list, name='group_list'),
    path('admin-panel/groups/add/', group_create, name='group_create'),
    path('admin-panel/students/add/', student_create, name='student_create'),
    path('admin-panel/teachers/add/', teacher_create, name='teacher_create'),
    path('admin-panel/students/', student_list, name='student_list'),
    path('admin-panel/teachers/', teacher_list, name='teacher_list'),
    path('admin-panel/schedule/create/', schedule_create, name='schedule_create'),
    path('admin-panel/import/', import_schedule, name='import_schedule'),
    path('admin-panel/template/', download_template, name='download_template'),
    
    
]