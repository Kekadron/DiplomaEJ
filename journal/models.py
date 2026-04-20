from django.db import models
from students.models import Student, Group, Teacher
from django.contrib.auth.models import User

class Discipline(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название дисциплины")
    code = models.CharField(max_length=50, blank=True, verbose_name="Код дисциплины")
    institution = models.ForeignKey(
        'students.Institution', 
        on_delete=models.CASCADE, 
        verbose_name="Учебное заведение",
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Дисциплина"
        verbose_name_plural = "Дисциплины"


class Lesson(models.Model):
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, verbose_name="Дисциплина")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Группа")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE,null=True, blank=True, verbose_name="Преподаватель")
    date = models.DateField(verbose_name="Дата занятия")
    pair_number = models.PositiveSmallIntegerField(verbose_name="Номер пары", null=True, blank=True, choices=[(1,1),(2,2),(3,3),(4,4),(5,5),(6,6)])
    topic = models.CharField(max_length=300, blank=True, verbose_name="Тема занятия")

    def __str__(self):
        return f"{self.date} | {self.pair_number} пара | {self.discipline} | {self.group.name}"

    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Занятия"
        unique_together = ['date', 'pair_number', 'group']  # нельзя поставить две пары в одно время одной группе
        ordering = ['date', 'pair_number']


class Grade(models.Model):
    GRADE_CHOICES = [
        ('5', '5'),
        ('4', '4'),
        ('3', '3'),
        ('2', '2'),
        ('Н', 'Н (не был)'),
        ('зач', 'зач'),
        ('н/зач', 'н/зач'),
        ('', '—'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Студент")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, verbose_name="Занятие")
    value = models.CharField(
        max_length=10,
        choices=GRADE_CHOICES,
        blank=True,
        default='',
        verbose_name="Оценка"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")

    def __str__(self):
        return f"{self.student} — {self.lesson} — {self.value or '—'}"

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"
        unique_together = ['student', 'lesson']

