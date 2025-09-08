from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Headline
from .serializers import HeadlineSerializer


@api_view(['GET'])
def list_languages(request):
    """
    List all language options.
    Optional query param: ?lang=en or ?lang=he to filter by language.
    """
    lang = request.query_params.get('lang')
    if lang in ['en', 'he']:
        options = Headline.objects.filter(language=lang).first()
    else:
        options = Headline.objects.all()
    serializer = HeadlineSerializer(options)
    return Response(serializer.data, status=status.HTTP_200_OK)
