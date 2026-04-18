from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, timedelta
from .models import Lesson, Grade, Discipline
from students.models import Teacher, Group, Student, Institution
from datetime import date as dt_date, timedelta
from openpyxl import Workbook
from django.http import HttpResponse

@login_required
def teacher_dashboard(request, date=None):
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin_dashboard')

    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "У вас нет прав преподавателя.")
        return redirect('login')

    # Текущая дата
    if date:
        current_date = dt_date.fromisoformat(date)
    else:
        current_date = dt_date.today()

    previous_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)

    lessons = Lesson.objects.filter(
        teacher=teacher,
        date=current_date
    ).select_related('discipline', 'group')\
     .order_by('pair_number')

    context = {
        'teacher': teacher,
        'lessons': lessons,
        'date': current_date,
        'previous_date': previous_date,
        'next_date': next_date,
    }

    return render(request, 'journal/teacher_dashboard.html', context)


@login_required
def lesson_grades(request, lesson_id):
    """Просмотр и редактирование журнала оценок по занятию"""
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Проверка прав доступа
    is_owner = hasattr(request.user, 'teacher') and request.user.teacher == lesson.teacher
    if not (request.user.is_superuser or request.user.is_staff or is_owner):
        messages.error(request, "У вас нет доступа к этому занятию.")
        return redirect('teacher_dashboard')

    # === АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ОЦЕНОК ДЛЯ НОВЫХ СТУДЕНТОВ ===
    students = lesson.group.students.all()
    for student in students:
        Grade.objects.get_or_create(
            student=student,
            lesson=lesson
        )
    # ========================================================

    # Получаем все оценки (уже с новыми студентами)
    grades = Grade.objects.filter(lesson=lesson).select_related('student').order_by(
        'student__last_name', 'student__first_name'
    )

    if request.method == 'POST':
        saved = 0
        for grade in grades:
            value = request.POST.get(f'grade_{grade.id}', '')
            comment = request.POST.get(f'comment_{grade.id}', '')

            if grade.value != value or grade.comment != comment:
                grade.value = value
                grade.comment = comment
                grade.save()
                saved += 1

        if saved > 0:
            messages.success(request, f'Сохранено {saved} изменений!')
        else:
            messages.info(request, 'Изменений не было')

        return redirect('lesson_grades', lesson_id=lesson.id)

    context = {
        'lesson': lesson,
        'grades': grades,
    }
    return render(request, 'journal/lesson_grades.html', context)

@login_required
def lesson_new(request):
    """Форма создания нового занятия с автоматическим созданием записей оценок"""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "У вас нет прав преподавателя")
        return redirect('login')

    if request.method == 'POST':
        discipline_id = request.POST.get('discipline')
        group_id = request.POST.get('group')
        date_str = request.POST.get('date')
        topic = request.POST.get('topic', '')

        try:
            lesson = Lesson.objects.create(
                discipline_id=discipline_id,
                group_id=group_id,
                teacher=teacher,
                date=date_str,
                topic=topic
            )

            # === АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ЗАПИСЕЙ GRADE ДЛЯ ВСЕХ СТУДЕНТОВ ===
            group = lesson.group
            students = group.students.all()

            for student in students:
                Grade.objects.get_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={'value': '', 'comment': ''}
                )

            messages.success(request, f'Занятие "{lesson.discipline} — {lesson.date}" успешно создано! Добавлено {students.count()} студентов.')
            return redirect('lesson_grades', lesson_id=lesson.id)

        except Exception as e:
            messages.error(request, f"Ошибка создания занятия: {e}")
            return redirect('lesson_new')

    disciplines = Discipline.objects.all()
    groups = Group.objects.all()

    context = {
        'teacher': teacher,
        'disciplines': disciplines,
        'groups': groups,
    }
    return render(request, 'journal/lesson_new.html', context)

@login_required
def admin_dashboard(request):
    """Панель администратора / Завуча"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Доступ запрещён.")
        return redirect('login')

    if request.user.is_superuser:
        total_institutions = Institution.objects.count()
        total_groups = Group.objects.count()
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
    else:
        # Завуч видит только своё заведение
        teacher = Teacher.objects.get(user=request.user)
        institution = teacher.institution
        total_institutions = 1
        total_groups = Group.objects.filter(institution=institution).count()
        total_students = Student.objects.filter(group__institution=institution).count()
        total_teachers = Teacher.objects.filter(institution=institution).count()

    context = {
        'total_institutions': total_institutions,
        'total_groups': total_groups,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'is_superuser': request.user.is_superuser,   # передаём в шаблон
    }
    return render(request, 'journal/admin_dashboard.html', context)



@login_required
def group_list(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('login')

    if request.user.is_superuser:
        groups = Group.objects.select_related('institution').all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        groups = Group.objects.filter(institution=teacher.institution).select_related('institution')

    context = {'groups': groups}
    return render(request, 'journal/group_list.html', context)



@login_required
def group_create(request):
    """Создание новой группы"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        institution_id = request.POST.get('institution')
        name = request.POST.get('name')
        specialty = request.POST.get('specialty')
        start_year = request.POST.get('start_year')

        Group.objects.create(
            institution_id=institution_id,
            name=name,
            specialty=specialty,
            start_year=start_year
        )
        messages.success(request, 'Группа успешно создана!')
        return redirect('group_list')

    institutions = Institution.objects.all()
    context = {'institutions': institutions}
    return render(request, 'journal/group_create.html', context)

def home_redirect(request):
    """Самая простая версия для диагностики"""
    if not request.user.is_authenticated:
        return redirect('login')

    # Прямые проверки
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin_dashboard')

    if hasattr(request.user, 'teacher'):
        return redirect('teacher_dashboard_today')

    # Проверка студента
    try:
        student = Student.objects.get(user=request.user)
        return redirect('student_dashboard')
    except:
        pass

    # Если ничего не подошло
    messages.error(request, f"Роль не определена для пользователя {request.user.username}")
    return redirect('login')

@login_required
def student_create(request):
    """Создание нового студента"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        group_id = request.POST.get('group')
        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name', '')
        student_id = request.POST.get('student_id')

        Student.objects.create(
            group_id=group_id,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            student_id=student_id
        )
        messages.success(request, 'Студент успешно создан!')
        return redirect('group_list')  # или куда захочешь

    groups = Group.objects.all()
    context = {'groups': groups}
    return render(request, 'journal/student_create.html', context)


@login_required
def teacher_create(request):
    """Создание нового преподавателя"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        # Создаём пользователя Django
        username = request.POST.get('username')
        password = request.POST.get('password')
        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name', '')
        phone = request.POST.get('phone', '')
        institution_id = request.POST.get('institution')

        user = User.objects.create_user(username=username, password=password)
        user.is_staff = True
        user.save()

        Teacher.objects.create(
            user=user,
            institution_id=institution_id,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            phone=phone
        )
        messages.success(request, 'Преподаватель успешно создан!')
        return redirect('admin_dashboard')

    institutions = Institution.objects.all()
    context = {'institutions': institutions}
    return render(request, 'journal/teacher_create.html', context)

@staff_member_required
def protected_admin(request):
    return redirect('/admin/')

@login_required
def student_list(request):
    """Список студентов"""
    if request.user.is_superuser:
        students = Student.objects.select_related('group__institution').all()
    else:
        # Завуч видит только студентов своего заведения
        teacher = Teacher.objects.get(user=request.user)
        students = Student.objects.filter(group__institution=teacher.institution).select_related('group__institution')

    context = {'students': students}
    return render(request, 'journal/student_list.html', context)


@login_required
def teacher_list(request):
    """Список преподавателей"""
    if request.user.is_superuser:
        teachers = Teacher.objects.select_related('institution').all()
    else:
        # Завуч видит только преподавателей своего заведения
        teacher = Teacher.objects.get(user=request.user)
        teachers = Teacher.objects.filter(institution=teacher.institution).select_related('institution')

    context = {'teachers': teachers}
    return render(request, 'journal/teacher_list.html', context)

@login_required
def student_dashboard(request):
    """Личный кабинет студента"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "У вас нет прав студента.")
        return redirect('login')

    # Группируем оценки по дисциплине
    from collections import defaultdict
    grades_by_discipline = defaultdict(list)
    avg_scores = {}  # Словарь для средних баллов

    grades = Grade.objects.filter(student=student).select_related('lesson__discipline').order_by('lesson__date')

    for grade in grades:
        discipline_name = grade.lesson.discipline.name
        grades_by_discipline[discipline_name].append(grade)

    # Рассчитываем средний балл по каждой дисциплине
    for discipline_name, grades_list in grades_by_discipline.items():
        total = 0
        count = 0
        for grade in grades_list:
            # Проверяем, является ли оценка числовой (2,3,4,5)
            if grade.value.isdigit() and grade.value in ['2', '3', '4', '5']:
                total += int(grade.value)
                count += 1
        
        if count > 0:
            avg = round(total / count, 2)
        else:
            avg = 0
        
        avg_scores[discipline_name] = avg

    context = {
        'student': student,
        'grades_by_discipline': dict(grades_by_discipline),
        'avg_scores': avg_scores,  # Добавляем средние баллы в контекст
    }
    return render(request, 'journal/student_dashboard.html', context)

@login_required
def schedule_create(request):
    """Завуч создаёт занятие для преподавателей своего заведения"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Доступ запрещён.")
        return redirect('login')

    # Определяем заведение завуча
    if request.user.is_superuser:
        institutions = Institution.objects.all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        institutions = Institution.objects.filter(id=teacher.institution.id)

    if request.method == 'POST':
        institution_id = request.POST.get('institution')
        discipline_id = request.POST.get('discipline')
        group_id = request.POST.get('group')
        teacher_id = request.POST.get('teacher')
        date = request.POST.get('date')
        topic = request.POST.get('topic', '')

        lesson = Lesson.objects.create(
            discipline_id=discipline_id,
            group_id=group_id,
            teacher_id=teacher_id,
            date=date,
            pair_number = request.POST.get('pair_number'),
            topic=topic
        )

        # Автоматически создаём записи Grade для всех студентов группы
        students = Group.objects.get(id=group_id).students.all()
        for student in students:
            Grade.objects.get_or_create(student=student, lesson=lesson)

        messages.success(request, f'Занятие "{lesson.discipline}" на {lesson.date} успешно создано!')
        return redirect('admin_dashboard')

    # Формируем данные для формы
    disciplines = Discipline.objects.all()
    groups = Group.objects.filter(institution__in=institutions)
    teachers = Teacher.objects.filter(institution__in=institutions)

    context = {
        'disciplines': disciplines,
        'groups': groups,
        'teachers': teachers,
        'institutions': institutions,
    }
    return render(request, 'journal/schedule_create.html', context)

@login_required
def student_schedule(request, date=None):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "У вас нет прав студента.")
        return redirect('login')

    # Если дата не передана → берём сегодня
    if date:
        try:
            current_date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            current_date = datetime.today().date()
    else:
        current_date = datetime.today().date()

    # Предыдущий и следующий день
    previous_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # Фильтрация занятий по дате
    lessons = Lesson.objects.filter(
        group=student.group,
        date=current_date
    ).select_related('discipline', 'teacher').order_by('pair_number')

    context = {
        'student': student,
        'lessons': lessons,
        'date': current_date,
        'previous_date': previous_date,
        'next_date': next_date,
    }

    return render(request, 'journal/student_schedule.html', context)

@login_required
def import_schedule(request):
    
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('login')

    if request.method == 'POST':
        file = request.FILES.get('file')

        if not file:
            messages.error(request, "Файл не выбран")
            return redirect('admin_dashboard')
            
        try:
            import pandas as pd

            df = pd.read_excel(file)
            created = 0

            for _, row in df.iterrows():
                date = pd.to_datetime(row['Дата']).date()
                pair = int(row['Пара'])
                group = Group.objects.filter(name=row['Группа']).first()
                discipline = Discipline.objects.filter(name=row['Дисциплина']).first()
                group_id = group.id
                
                if not group or not discipline:
                    continue

                teacher_parts = str(row['Преподаватель']).split()
                teacher = Teacher.objects.filter(last_name=teacher_parts[0]).first()

                if not teacher:
                    continue

                lesson, created_flag = Lesson.objects.get_or_create(
                    date=date,
                    pair_number=pair,
                    group=group,
                    defaults={
                        'discipline': discipline,
                        'teacher': teacher,
                        'topic': row.get('Тема', '')
                    }
                )
                students = Group.objects.get(id=group_id).students.all()
                for student in students:
                    Grade.objects.get_or_create(student=student, lesson=lesson)
                if created_flag:
                    created += 1

            messages.success(request, f"Импортировано занятий: {created}")

        except Exception as e:
            messages.error(request, f"Ошибка: {e}")

        return redirect('admin_dashboard')

    return redirect('admin_dashboard')

def download_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Расписание"

    headers = ["Дата", "Пара", "Группа", "Дисциплина", "Преподаватель", "Тема"]
    ws.append(headers)

    # пример строки
    ws.append(["2026-04-18", 1, "ИС-21", "Математика", "Иванов Иван", "Пределы"])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=template.xlsx'

    wb.save(response)
    return response