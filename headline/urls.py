from django.urls import path
from . import views

urlpatterns = [
    path('languages/', views.list_languages, name='list_languages'),
]
