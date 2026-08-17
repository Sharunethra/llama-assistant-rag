from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    """
    Represents an uploaded document (PDF or TXT) owned by a User.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.user.username} - {self.filename}"


class DocumentChunk(models.Model):
    """
    Represents a sequential text chunk extracted from a Document along with its dense vector embedding.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    content = models.TextField()
    chunk_index = models.IntegerField()
    embedding = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.filename}"
