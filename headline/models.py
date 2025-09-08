from django.db import models

# Create your models here.
from django.db import models


from django.db import models


class Headline(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('he', 'Hebrew'),
    ]

    wellcome_message = models.TextField(blank=True, null=True)
    input_placeholder = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)

    def save(self, *args, **kwargs):
        # Delete existing headline of the same language before saving
        Headline.objects.filter(
            language=self.language).exclude(pk=self.pk).delete()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wellcome_message} ({self.get_language_display()})"
