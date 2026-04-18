from django.contrib import admin
from .models import Discipline, Lesson, Grade
from students.models import Student

class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0
    fields = ['student', 'value', 'comment']
    ordering = ['student__last_name']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        if obj and obj.group:   # obj — это текущее занятие (Lesson)
            # Ограничиваем выбор студентов только теми, кто в группе этого занятия
            formset.form.base_fields['student'].queryset = Student.objects.filter(
                group=obj.group
            ).order_by('last_name', 'first_name')
        
        return formset


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['discipline', 'group', 'teacher', 'date', 'topic']
    list_filter = ['group', 'discipline', 'teacher']
    inlines = [GradeInline]


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'value']
    list_filter = ['lesson__discipline', 'value']