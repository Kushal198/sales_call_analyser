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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Sentiment(models.TextChoices):
        POSITIVE = 'positive'
        NEUTRAL = 'neutral'
        NEGATIVE = 'negative'
    
    class ManagerAction(models.TextChoices):
        NO_ACTION = 'no_action', 'No Action'
        REVIEW_WITH_REP = 'review_with_rep', 'Review With Rep'
        FLAG_FOR_PIPELINE = 'flag_for_pipeline_review', 'Flag for Pipeline Review'

    job = models.OneToOneField(AnalysisJob, on_delete=models.CASCADE, related_name='analysis')
    summary = models.TextField()
    sentiment = models.CharField(max_length=20, choices=Sentiment.choices)
    key_topics = models.JSONField(default=list)
    score = models.IntegerField()
    score_rationale = models.TextField()
    skill_gaps = models.JSONField(default=list)  # ["objection handling", "discovery questioning"]
    action_items = models.JSONField(default=list)
    objections_raised = models.JSONField(default=list)
    missed_opportunities = models.JSONField(default=list)
    coaching_tips = models.JSONField(default=list)
    deal_stage_assessment = models.CharField(max_length=255, blank=True)
    recommended_manager_action = models.CharField(
        max_length=50,
        choices=ManagerAction.choices,
        default=ManagerAction.NO_ACTION
    )

    def __str__(self):
        return f"Analysis for Job {self.job.id}"