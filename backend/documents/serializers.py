from rest_framework import serializers
from .models import Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'user', 'filename', 'uploaded_at', 'chunk_count']
        read_only_fields = ['id', 'user', 'filename', 'uploaded_at', 'chunk_count']

    def get_chunk_count(self, obj):
        return obj.chunks.count()
