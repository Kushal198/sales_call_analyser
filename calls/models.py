import uuid
from django.db import models

# Create your models here.
class Call(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    transcript = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AnalysisJob(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        RUNNING = 'running'
        COMPLETED = 'completed'
        FAILED = 'failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


    def __str__(self):
        return f"Job {self.id} — {self.status}"


class CallAnalysis(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = 'positive'
        NEUTRAL = 'neutral'
        NEGATIVE = 'negative'

    job = models.OneToOneField(AnalysisJob, on_delete=models.CASCADE, related_name='analysis')
    summary = models.TextField()
    sentiment = models.CharField(max_length=20, choices=Sentiment.choices)
    key_topics = models.JSONField(default=list)
    action_items = models.JSONField(default=list)
    objections_raised = models.JSONField(default=list)
    next_steps = models.TextField()
    talk_ratio = models.JSONField(default=dict)
    score = models.IntegerField()
    score_rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for Job {self.job.id}"