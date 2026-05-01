import logging
from celery import shared_task
from .models import AnalysisJob, CallAnalysis
from .llm import get_llm_provider
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def format_transcript(transcript: list) -> str:
    lines = []
    for turn in transcript:
        speaker = turn['speaker']
        text = turn['text']
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def run_analysis(self, job_id):
    try:
        job = AnalysisJob.objects.select_related('call').get(id=job_id)
    except AnalysisJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return

    try:
        job.status = AnalysisJob.Status.RUNNING
        job.save(update_fields=['status'])

        transcript = job.call.transcript
        formatted = format_transcript(transcript)

        provider = get_llm_provider()
        data = provider.analyse(formatted)

        CallAnalysis.objects.create(
            job=job,
            summary=data['summary'],
            sentiment=data['sentiment'],
            key_topics=data['key_topics'],
            score=data['score'],
            score_rationale=data['score_rationale'],
            action_items=data['action_items'],
            objections_raised=data['objections_raised'],
            missed_opportunities=data['missed_opportunities'],
            coaching_tips=data['coaching_tips'],
            deal_stage_assessment=data['deal_stage_assessment'],
            recommended_manager_action=data['recommended_manager_action'],
            skill_gaps=data['skill_gaps'],
        )

        job.status = AnalysisJob.Status.COMPLETED
        job.save(update_fields=['status'])

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}")
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            job.status = AnalysisJob.Status.FAILED
            job.error_message = str(exc)
            job.save(update_fields=['status', 'error_message'])


@shared_task
def cleanup_stale_jobs():
    """
    Periodic task to catch jobs stuck in PENDING or RUNNING.
    
    PENDING threshold — job was never picked up by a worker.
    RUNNING threshold — worker died mid-execution.
    
    We use updated_at not created_at because a job could legitimately
    sit in PENDING briefly before being picked up. updated_at tells us
    when the state last changed — more accurate than when the job was created.
    """
    threshold = timezone.now() - timedelta(minutes=10)

    stale_jobs = AnalysisJob.objects.filter(
        status__in=[
            AnalysisJob.Status.PENDING,
            AnalysisJob.Status.RUNNING
        ],
        updated_at__lt=threshold
    )

    count = stale_jobs.count()

    if count == 0:
        logger.info("No stale jobs found")
        return

    stale_jobs.update(
        status=AnalysisJob.Status.FAILED,
        error_message="Job timed out — worker likely crashed or queue backed up"
    )

    logger.info(f"Cleaned up {count} stale jobs")

def dispatch_analysis(job_id):
    run_analysis.delay(str(job_id))