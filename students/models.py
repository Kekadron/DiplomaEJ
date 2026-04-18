from django.db import models
from django.contrib.auth.models import User

class Institution(models.Model):
    name = models.CharField(max_length=200, verbose_name="Полное название учебного заведения")
    short_name = models.CharField(max_length=100, verbose_name="Короткое название")
    address = models.TextField(blank=True, verbose_name="Адрес")
    director = models.CharField(max_length=150, blank=True, verbose_name="Директор")

    def __str__(self):
        return self.short_name or self.name

    class Meta:
        verbose_name = "Учебное заведение"
        verbose_name_plural = "Учебные заведения"


class Group(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="groups", verbose_name="Учебное заведение")
    name = models.CharField(max_length=100, verbose_name="Название группы")
    specialty = models.CharField(max_length=200, verbose_name="Специальность")
    start_year = models.IntegerField(verbose_name="Год начала обучения")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return f"{self.name} ({self.institution.short_name})"

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="teachers", verbose_name="Учебное заведение")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    middle_name = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.institution.short_name})"

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Аккаунт пользователя")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="students", verbose_name="Группа")
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    middle_name = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    student_id = models.CharField(max_length=20, unique=True, verbose_name="Номер студенческого")

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.group.name if self.group else 'Без группы'})"

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"
    
