from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings


class Enrollment(models.Model):
    user = models.ForeignKey(get_user_model(),on_delete=models.CASCADE,blank=False)
    thinkific_user_id = models.IntegerField(('thinkific user id'),blank=False)
    course_id = models.IntegerField('Course id',blank=False)
    activated_at = models.DateTimeField(('activated at'),blank=False)
    expiry_date = models.DateTimeField(('expiry date'), blank=False)


LANGUAGE_CHOICES = [(code, name) for code, name in settings.LANGUAGES]


class CourseTranslation(models.Model):
    """Traductions locales pour les cours provenant de Thinkific."""
    course_id = models.IntegerField('Thinkific course ID', db_index=True)
    language = models.CharField('Langue', max_length=5, choices=LANGUAGE_CHOICES)
    name = models.CharField('Nom du cours', max_length=255, blank=True)
    description = models.TextField('Description', blank=True)

    class Meta:
        unique_together = ('course_id', 'language')
        verbose_name = 'Traduction de cours'
        verbose_name_plural = 'Traductions de cours'

    def __str__(self):
        return f'Cours {self.course_id} [{self.language}]'
