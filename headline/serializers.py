from rest_framework import serializers
from .models import Headline


class HeadlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Headline
        fields = ['id', 'wellcome_message', 'language', 'input_placeholder']
