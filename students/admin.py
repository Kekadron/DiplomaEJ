from django.contrib import admin
from .models import Group, Student, Teacher, Institution

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'director']
    search_fields = ['name', 'short_name']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialty', 'institution', 'start_year', 'is_active']
    list_filter = ['institution', 'is_active']
    search_fields = ['name', 'specialty']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'group', 'student_id']
    list_filter = ['group__institution', 'group']
    search_fields = ['last_name', 'first_name', 'student_id']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'institution', 'phone']
    list_filter = ['institution']
    search_fields = ['last_name', 'first_name']