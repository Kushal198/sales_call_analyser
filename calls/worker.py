import logging
from celery import shared_task
from .models import AnalysisJob, CallAnalysis
from .llm import get_llm_provider

logger = logging.getLogger(__name__)


def format_transcript(transcript: list) -> str:
    lines = []
    for turn in transcript:
        speaker = turn['speaker']
        text = turn['text']
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def compute_talk_ratio(transcript: list) -> dict:
    word_counts = {}
    for turn in transcript:
        speaker = turn['speaker']
        text = turn['text']
        word_counts[speaker] = word_counts.get(speaker, 0) + len(text.split())

    total = sum(word_counts.values())
    if total == 0:
        return {}

    return {speaker: round(count / total, 2) for speaker, count in word_counts.items()}


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def run_analysis(self, job_id):
    try:
        job = AnalysisJob.objects.get(id=job_id)
        job.status = AnalysisJob.Status.RUNNING
        job.save()

        transcript = job.call.transcript
        formatted = format_transcript(transcript)
        talk_ratio = compute_talk_ratio(transcript)

        provider = get_llm_provider()
        data = provider.analyse(formatted)

        CallAnalysis.objects.create(
            job=job,
            summary=data['summary'],
            sentiment=data['sentiment'],
            key_topics=data['key_topics'],
            action_items=data['action_items'],
            objections_raised=data['objections_raised'],
            next_steps=data['next_steps'],
            talk_ratio=talk_ratio,
            score=data['score'],
            score_rationale=data['score_rationale'],
        )

        job.status = AnalysisJob.Status.COMPLETED
        job.save()

    except AnalysisJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}")
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            job.status = AnalysisJob.Status.FAILED
            job.error_message = str(exc)
            job.save()


def dispatch_analysis(job_id):
    run_analysis.delay(str(job_id))