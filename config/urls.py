from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


# Импорт всех views
from groups import views
from journal.views import (
    admin_schedule,
    delete_lesson,
    discipline_create,
    export_semester_report,
    schedule_create,
    schedule_edit,
    student_delete,
    student_list,
    teacher_dashboard, 
    lesson_grades, 
    admin_dashboard,    
    group_list,
    group_create,      
    home_redirect,
    student_create,
    student_edit,
    teacher_create,
    teacher_list,   
    student_dashboard,
    student_schedule,
    import_schedule,
    download_template,
    discipline_list,
    discipline_edit,
    discipline_delete,
    group_edit,
    group_delete,
    teacher_edit,
    teacher_delete,
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

    
    # Администратор / Завуч
    path('admin-panel/', admin_dashboard, name='admin_dashboard'),
    path('admin-panel/groups/', group_list, name='group_list'),
    path('admin-panel/groups/add/', group_create, name='group_create'),
    path('admin-panel/students/add/', student_create, name='student_create'),
    path('admin-panel/teachers/add/', teacher_create, name='teacher_create'),
    path('admin-panel/disciplines/add/', discipline_create, name='discipline_create'),
    path('admin-panel/schedule/create/', schedule_create, name='schedule_create'),
    path('admin-panel/schedule/', admin_schedule, name='admin_schedule'),
    path('admin-panel/schedule/<str:date>/', admin_schedule, name='admin_schedule'),
    path('admin-panel/schedule/<int:lesson_id>/edit/', schedule_edit, name='schedule_edit'),
    path('admin-panel/students/', student_list, name='student_list'),
    path('admin-panel/teachers/', teacher_list, name='teacher_list'),
    path('admin-panel/disciplines/', discipline_list, name='discipline_list'),
    path('admin-panel/import/', import_schedule, name='import_schedule'),
    path('admin-panel/template/', download_template, name='download_template'),
    path('admin-panel/students/<int:student_id>/', student_edit, name='student_edit'),
    path('students/<int:student_id>/delete/', student_delete, name='student_delete'),
    path('discipline/<int:pk>/edit/', discipline_edit, name='discipline_edit'),
    path('discipline/<int:pk>/delete/', discipline_delete, name='discipline_delete'),
    path('admin-panel/groups/<int:pk>/edit/', group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', group_delete, name='group_delete'),
    path('lesson/<int:lesson_id>/delete/', delete_lesson, name='delete_lesson'),
    path('teacher/<int:teacher_id>/edit/', teacher_edit, name='teacher_edit'),
    path('teachers/<int:teacher_id>/delete/', teacher_delete, name='teacher_delete'),
    path('export/semester/', export_semester_report, name='export_semester_report'),
]