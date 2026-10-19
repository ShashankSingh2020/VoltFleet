from rest_framework import serializers


class ChatQueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, required=True)


class ChatQueryResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    answer = serializers.CharField()
    provider = serializers.CharField()