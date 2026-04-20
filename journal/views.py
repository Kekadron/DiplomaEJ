from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db import IntegrityError
from datetime import datetime, timedelta
from .models import Lesson, Grade, Discipline
from students.models import Teacher, Group, Student, Institution
from datetime import date as dt_date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font
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
        total_disciplines = Discipline.objects.count()
    else:
        # Завуч видит только своё заведение
        teacher = Teacher.objects.get(user=request.user)
        institution = teacher.institution
        total_institutions = 1
        total_groups = Group.objects.filter(institution=institution).count()
        total_students = Student.objects.filter(group__institution=institution).count()
        total_teachers = Teacher.objects.filter(institution=institution).count()
        total_disciplines = Discipline.objects.filter(institution=institution).count()

    context = {
        'total_institutions': total_institutions,
        'total_groups': total_groups,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_disciplines': total_disciplines,
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
        name = request.POST.get('name')
        specialty = request.POST.get('specialty')
        start_year = request.POST.get('start_year')
        
        # Определяем institution_id
        if request.user.is_superuser:
            institution_id = request.POST.get('institution')
        else:
            try:
                teacher = Teacher.objects.get(user=request.user)
                institution_id = teacher.institution.id
            except Teacher.DoesNotExist:
                messages.error(request, 'У вас не привязано учебное заведение')
                return redirect('group_list')

        # Проверка на пустые значения
        if not name or not specialty or not start_year:
            messages.error(request, 'Заполните все поля')
            return redirect('group_create') 
        
        if not institution_id:
            messages.error(request, 'Не указано учебное заведение')
            return redirect('group_create')

        Group.objects.create(
            institution_id=institution_id,
            name=name,
            specialty=specialty,
            start_year=start_year
        )
        messages.success(request, 'Группа успешно создана!')
        return redirect('group_list')

    institutions = Institution.objects.all()
    context = {
        'institutions': institutions,
        'is_superuser': request.user.is_superuser,
    }
    
    if not request.user.is_superuser:
        try:
            teacher = Teacher.objects.get(user=request.user)
            context['teacher'] = teacher
        except Teacher.DoesNotExist:
            pass
    
    return render(request, 'journal/group_create.html', context)

@login_required
def group_edit(request, pk):
    if not request.user.is_staff:
        return redirect('student_schedule')

    group = Group.objects.get(id=pk)
    institutions = Institution.objects.all()

    if request.method == "POST":
        group.name = request.POST.get("name")
        group.specialty = request.POST.get("specialty")
        group.start_year = request.POST.get("start_year")
        group.institution_id = request.POST.get("institution")
        group.save()
        return redirect('group_list')

    return render(request, "journal/group_edit.html", {
        "group": group,
        "institutions": institutions
    })

@login_required
def group_delete(request, pk):
    Group.objects.get(id=pk).delete()
    return redirect('group_list')

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
        return redirect('admin_dashboard')

    if request.user.is_superuser:
        # Суперпользователь видит все группы
        groups = Group.objects.all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        groups = Group.objects.filter(institution=teacher.institution)
    context = {'groups': groups}
    return render(request, 'journal/student_create.html', context)

@login_required
def student_edit(request, student_id):
    """Редактирование данных студента"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        student.last_name = request.POST.get('last_name')
        student.first_name = request.POST.get('first_name')
        student.middle_name = request.POST.get('middle_name', '')
        student.student_id = request.POST.get('student_id')
        student.group_id = request.POST.get('group')
        student.save()
        messages.success(request, 'Данные студента успешно обновлены!')
        return redirect('admin_dashboard')

    if request.user.is_superuser:
        groups = Group.objects.all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        groups = Group.objects.filter(institution=teacher.institution)
    
    context = {
        'student': student,
        'groups': groups,
    }
    return render(request, 'journal/student_edit.html', context)

@login_required
def student_delete(request, student_id):
    """Удаление студента"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)
    student.delete()
    messages.success(request, 'Студент успешно удалён!')
    return redirect('admin_dashboard')

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
        user.is_staff = False  # по умолчанию — не админ
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

    if request.user.is_superuser:
        # Суперпользователь видит все группы
        institutions = Institution.objects.all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        institutions = Institution.objects.filter(id=teacher.institution.id)
    context = {'institutions': institutions}
    return render(request, 'journal/teacher_create.html', context)

@login_required
def teacher_edit(request, teacher_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    teacher = Teacher.objects.get(id=teacher_id)

    if request.method == 'POST':
        teacher.last_name = request.POST.get('last_name')
        teacher.first_name = request.POST.get('first_name')
        teacher.middle_name = request.POST.get('middle_name', '')
        teacher.phone = request.POST.get('phone', '')
        teacher.save()
        messages.success(request, 'Данные преподавателя успешно обновлены!')
        return redirect('teacher_list')

    context = {
        'teacher': teacher,
    }
    return render(request, 'journal/teacher_edit.html', context)

@login_required
def teacher_delete(request, teacher_id):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    teacher = Teacher.objects.get(id=teacher_id)
    user = teacher.user
    teacher.delete()
    user.delete()  # удаляем связанный аккаунт
    messages.success(request, 'Преподаватель успешно удалён!')
    return redirect('teacher_list')

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
    if request.user.is_superuser:
        disciplines = Discipline.objects.all()
    else:
        disciplines = Discipline.objects.filter(institution__in=institutions)
    groups = Group.objects.filter(institution__in=institutions)
    teachers = Teacher.objects.filter(
        institution__in=institutions,
        user__is_staff=False  # исключаем сотрудников (завучей, админов)
    )

    context = {
        'disciplines': disciplines,
        'groups': groups,
        'teachers': teachers,
        'institutions': institutions,
    }
    return render(request, 'journal/schedule_create.html', context)

@login_required
def schedule_edit(request, lesson_id):
    """Редактирование занятия"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Доступ запрещён.")
        return redirect('login')

    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Определяем заведение завуча
    if request.user.is_superuser:
        institutions = Institution.objects.all()
    else:
        teacher = Teacher.objects.get(user=request.user)
        institutions = Institution.objects.filter(id=teacher.institution.id)

    if request.method == 'POST':
        lesson.discipline_id = request.POST.get('discipline')
        lesson.group_id = request.POST.get('group')
        lesson.teacher_id = request.POST.get('teacher')
        lesson.date = request.POST.get('date')
        lesson.pair_number = request.POST.get('pair_number')
        lesson.topic = request.POST.get('topic', '')
        lesson.save()

        messages.success(request, f'Занятие "{lesson.discipline}" на {lesson.date} успешно обновлено!')
        return redirect('admin_dashboard')

    # Формируем данные для формы
    if request.user.is_superuser:
        disciplines = Discipline.objects.all()
    else:
        disciplines = Discipline.objects.filter(institution__in=institutions)
    groups = Group.objects.filter(institution__in=institutions)
    teachers = Teacher.objects.filter(
        institution__in=institutions,
        user__is_staff=False  # исключаем сотрудников (завучей, админов)
    )

    context = {
        'lesson': lesson,
        'disciplines': disciplines,
        'groups': groups,
        'teachers': teachers,
        'institutions': institutions,
    }
    return render(request, 'journal/schedule_edit.html', context)

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
    created = 0
    skipped = 0
    errors = 0
    conflicts = []
    
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
                try:
                    date = pd.to_datetime(row['Дата']).date()
                    pair = int(row['Пара'])
                    group = Group.objects.filter(name=row['Группа']).first()
                    discipline = Discipline.objects.filter(name=row['Дисциплина']).first()

                    if not group or not discipline:
                        errors += 1
                        continue

                    teacher_parts = str(row['Преподаватель']).split()
                    teacher = Teacher.objects.filter(last_name=teacher_parts[0]).first()

                    if not teacher:
                        errors += 1
                        continue

                    # === ПРОВЕРКА КОНФЛИКТА ===
                    existing_lesson = Lesson.objects.filter(
                        date=date,
                        pair_number=pair,
                        group=group
                    ).first()

                    if existing_lesson:
                        conflicts.append(
                            f"{date} | пара {pair} | {group.name} уже занята ({existing_lesson.discipline})"
                        )
                        skipped += 1
                        continue

                    # === СОЗДАЕМ ЕСЛИ НЕТ ===
                    lesson = Lesson.objects.create(
                        date=date,
                        pair_number=pair,
                        group=group,
                        discipline=discipline,
                        teacher=teacher,
                        topic=row.get('Тема', '')
                    )

                    # создаем оценки
                    students = group.students.all()
                    for student in students:
                        Grade.objects.get_or_create(student=student, lesson=lesson)

                    created += 1

                except Exception as e:
                    errors += 1

            messages.success(request, f"Импортировано занятий: {created}")
            if conflicts:
                messages.warning(request, f"Пропущено (конфликты): {skipped}\n" + "\n".join(conflicts[:5]))
            if errors:
                messages.error(request, f"Ошибок: {errors}")

        except Exception as e:
            messages.error(request, f"Ошибка при чтении файла: {e}")

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

@login_required
def export_semester_report(request):
    teacher = request.user.teacher
    semester = int(request.GET.get('semester', 1))

    if semester == 1:
        months = [9,10,11,12]
    else:
        months = [1,2,3,4,5,6]

    lessons = Lesson.objects.filter(
        teacher=teacher,
        date__month__in=months
    ).select_related('group', 'discipline')

    groups = set(l.group for l in lessons)

    wb = Workbook()
    ws = wb.active
    ws.title = "Отчёт"

    row = 1

    bold = Font(bold=True)

    for group in groups:
        students = group.students.all()

        for student in students:

            # === Заголовок студента ===
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            cell = ws.cell(row=row, column=1)
            cell.value = f"{student.last_name} {student.first_name} | {group.name} | Семестр {semester}"
            cell.font = Font(bold=True, size=14)
            row += 1

            # === Таблица ===
            ws.cell(row=row, column=1, value="Дисциплина").font = bold
            ws.cell(row=row, column=2, value="Средний балл").font = bold
            row += 1

            grades = Grade.objects.filter(
                student=student,
                lesson__group=group,
                lesson__date__month__in=months
            ).select_related('lesson__discipline')

            by_disc = {}

            for g in grades:
                name = g.lesson.discipline.name
                by_disc.setdefault(name, []).append(g)

            total = 0
            count = 0

            for d, g_list in by_disc.items():
                values = [int(x.value) for x in g_list if x.value.isdigit()]
                avg = round(sum(values)/len(values), 2) if values else 0

                ws.cell(row=row, column=1, value=d)
                ws.cell(row=row, column=2, value=avg)

                total += sum(values)
                count += len(values)

                row += 1

            overall = round(total/count, 2) if count else 0

            ws.cell(row=row, column=1, value="Общий средний").font = bold
            ws.cell(row=row, column=2, value=overall).font = bold
            row += 2

            # === РАЗДЕЛИТЕЛЬ (чтобы резать) ===
            for col in range(1, 5):
                ws.cell(row=row, column=col).value = "----------------------"
            row += 3

    # ширина колонок
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 20

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=semester_report.xlsx'

    wb.save(response)
    return response


    lesson = Lesson.objects.get(id=lesson_id)

    disciplines = Discipline.objects.all()
    groups = Group.objects.all()

    if request.method == "POST":
        lesson.discipline_id = request.POST.get("discipline")
        lesson.group_id = request.POST.get("group")
        lesson.date = request.POST.get("date")
        lesson.topic = request.POST.get("topic")

        lesson.save()

        return redirect("admin_dashboard")  # или куда тебе нужно

    return render(request, "journal/edit_lesson.html", {
        "lesson": lesson,
        "disciplines": disciplines,
        "groups": groups
    })

@login_required
def discipline_list(request):
    """Список дисциплин"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')
    
    if request.user.is_superuser:
        # Суперпользователь видит все дисциплины
        disciplines = Discipline.objects.all()
    else:
        try:
            teacher = Teacher.objects.get(user=request.user)
            disciplines = Discipline.objects.filter(institution=teacher.institution)
        except Teacher.DoesNotExist:
            disciplines = Discipline.objects.none()
            messages.warning(request, 'Профиль преподавателя не найден')
    
    context = {
        'disciplines': disciplines,
    }
    return render(request, 'journal/discipline_list.html', context)

@login_required
def discipline_create(request):
    """Создание новой дисциплины"""
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', '')
        
        # Определяем учебное заведение
        if request.user.is_superuser:
            institution_id = request.POST.get('institution')
            if not institution_id:
                messages.error(request, 'Выберите учебное заведение')
                institutions = Institution.objects.all()
                return render(request, 'journal/discipline_create.html', {'institutions': institutions})
            institution = get_object_or_404(Institution, id=institution_id)
        else:
            try:
                teacher = Teacher.objects.get(user=request.user)
                institution = teacher.institution
            except Teacher.DoesNotExist:
                messages.error(request, 'Профиль преподавателя не найден')
                return redirect('discipline_list')
        
        # Проверка на существование такой дисциплины в этом заведении
        if Discipline.objects.filter(name=name, institution=institution).exists():
            messages.error(request, f'Дисциплина "{name}" уже существует в вашем учебном заведении!')
            return redirect('discipline_create')
        
        # Создаём дисциплину
        Discipline.objects.create(
            name=name,
            code=code,
            institution=institution
        )
        messages.success(request, 'Дисциплина успешно создана!')
        return redirect('discipline_list')

    # GET запрос
    context = {}
    if request.user.is_superuser:
        context['institutions'] = Institution.objects.all()
    
    return render(request, 'journal/discipline_create.html', context)

@login_required
def discipline_edit(request, pk):
    discipline = Discipline.objects.get(id=pk)

    if request.method == "POST":
        discipline.name = request.POST.get("name")
        discipline.code = request.POST.get("code")
        discipline.save()
        return redirect('discipline_list')

    return render(request, 'journal/discipline_edit.html', {
        'discipline': discipline
    })
    
@login_required
def discipline_delete(request, pk):
    Discipline.objects.get(id=pk).delete()
    return redirect('discipline_list')

@login_required
def admin_schedule(request, date=None):
    """Расписание для администратора/завуча"""
    # проверка прав
    if not request.user.is_staff:
        return redirect('student_schedule')

    # дата
    if date:
        try:
            current_date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            current_date = datetime.today().date()
    else:
        current_date = datetime.today().date()

    previous_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

    # Базовый запрос
    lessons = Lesson.objects.filter(date=current_date)
    
    # Фильтрация по правам пользователя
    if request.user.is_superuser:
        # Суперпользователь видит все уроки
        lessons = lessons.select_related('discipline', 'teacher', 'group', 'group__institution')
    else:
        # Завуч (staff) видит только уроки своего учебного заведения
        try:
            teacher = Teacher.objects.get(user=request.user)
            lessons = lessons.filter(
                group__institution=teacher.institution
            ).select_related('discipline', 'teacher', 'group', 'group__institution')
        except Teacher.DoesNotExist:
            lessons = Lesson.objects.none()
            messages.warning(request, 'Ваш профиль не связан с учебным заведением')
    
    # Сортировка для правильной группировки
    lessons = lessons.order_by('group__name', 'pair_number')
    
    context = {
        'lessons': lessons,
        'date': current_date,
        'previous_date': previous_date,
        'next_date': next_date,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'journal/admin_schedule.html', context)
    
@login_required
def delete_lesson(request, lesson_id):
    if not request.user.is_staff:
        return redirect('student_schedule')

    lesson = Lesson.objects.get(id=lesson_id)

    if request.method == "POST":
        lesson.delete()
        return redirect('admin_schedule')


