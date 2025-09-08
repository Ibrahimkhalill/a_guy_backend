
# Register your models here.
from django.contrib import admin
from .models import Headline


@admin.register(Headline)
class LanguageOptionAdmin(admin.ModelAdmin):
    list_display = ('wellcome_message', 'input_placeholder', 'language')
    list_filter = ('language',)
    search_fields = ('wellcome_message',)
