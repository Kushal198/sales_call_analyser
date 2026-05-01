from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Call, AnalysisJob, CallAnalysis
from .worker import format_transcript, compute_talk_ratio


VALID_TRANSCRIPT = [
    {"speaker": "Rep", "text": "Hi John, thanks for jumping on the call today."},
    {"speaker": "Prospect", "text": "Sure, though I only have 20 minutes."},
    {"speaker": "Rep", "text": "What are your biggest challenges with your current CRM?"},
    {"speaker": "Prospect", "text": "The reporting is terrible and my team hates using it."},
]

MOCK_ANALYSIS = {
    "summary": "Rep discussed CRM reporting issues with prospect.",
    "sentiment": "neutral",
    "key_topics": ["CRM", "reporting"],
    "action_items": ["Send pricing breakdown"],
    "objections_raised": ["Budget is tight"],
    "next_steps": "Rep to follow up on Friday",
    "score": 7,
    "score_rationale": "Good discovery but weak closing.",
}


class CallCreateTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('call-list-create')

    def test_create_call_valid(self):
        payload = {"title": "Acme Demo", "transcript": VALID_TRANSCRIPT}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Call.objects.count(), 1)
        self.assertEqual(response.data['title'], 'Acme Demo')

    def test_create_call_empty_transcript(self):
        payload = {"title": "Empty Call", "transcript": []}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('transcript', response.data)

    def test_create_call_missing_speaker(self):
        payload = {
            "title": "Bad Transcript",
            "transcript": [{"text": "Hello there"}]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_call_missing_text(self):
        payload = {
            "title": "Bad Transcript",
            "transcript": [{"speaker": "Rep"}]
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_call_missing_title(self):
        payload = {"transcript": VALID_TRANSCRIPT}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_calls(self):
        Call.objects.create(title="Call 1", transcript=VALID_TRANSCRIPT)
        Call.objects.create(title="Call 2", transcript=VALID_TRANSCRIPT)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class AnalyseTriggerTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.call = Call.objects.create(
            title="Acme Demo",
            transcript=VALID_TRANSCRIPT
        )
        self.url = reverse('analyse-trigger', kwargs={'call_id': self.call.id})

    @patch('calls.views.dispatch_analysis')
    def test_trigger_analysis_valid(self, mock_dispatch):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('job_id', response.data)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(AnalysisJob.objects.count(), 1)
        mock_dispatch.assert_called_once()

    def test_trigger_analysis_call_not_found(self):
        url = reverse('analyse-trigger', kwargs={'call_id': '00000000-0000-0000-0000-000000000000'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    @patch('calls.views.dispatch_analysis')
    def test_trigger_analysis_already_running(self, mock_dispatch):
        AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.RUNNING)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)
        self.assertEqual(AnalysisJob.objects.count(), 1)
        mock_dispatch.assert_not_called()

    @patch('calls.views.dispatch_analysis')
    def test_trigger_analysis_already_pending(self, mock_dispatch):
        AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.PENDING)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AnalysisJob.objects.count(), 1)
        mock_dispatch.assert_not_called()

    @patch('calls.views.dispatch_analysis')
    def test_trigger_analysis_after_failure_creates_new_job(self, mock_dispatch):
        AnalysisJob.objects.create(
            call=self.call,
            status=AnalysisJob.Status.FAILED,
            error_message="OpenAI timeout"
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(AnalysisJob.objects.count(), 2)
        mock_dispatch.assert_called_once()

    @patch('calls.views.dispatch_analysis')
    def test_trigger_analysis_after_completion_creates_new_job(self, mock_dispatch):
        AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.COMPLETED)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(AnalysisJob.objects.count(), 2)
        mock_dispatch.assert_called_once()


class JobStatusTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.call = Call.objects.create(
            title="Acme Demo",
            transcript=VALID_TRANSCRIPT
        )

    def _get_url(self, job_id):
        return reverse('job-status', kwargs={'job_id': job_id})

    def test_poll_pending_job(self):
        job = AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.PENDING)
        response = self.client.get(self._get_url(job.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')
        self.assertIsNone(response.data['analysis'])

    def test_poll_running_job(self):
        job = AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.RUNNING)
        response = self.client.get(self._get_url(job.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'running')
        self.assertIsNone(response.data['analysis'])

    def test_poll_completed_job_has_analysis(self):
        job = AnalysisJob.objects.create(call=self.call, status=AnalysisJob.Status.COMPLETED)
        CallAnalysis.objects.create(
            job=job,
            summary="Good call.",
            sentiment="positive",
            key_topics=["pricing"],
            action_items=["Send doc"],
            objections_raised=["Too expensive"],
            next_steps="Follow up Friday",
            talk_ratio={"Rep": 0.6, "Prospect": 0.4},
            score=8,
            score_rationale="Strong discovery."
        )
        response = self.client.get(self._get_url(job.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertIsNotNone(response.data['analysis'])
        self.assertEqual(response.data['analysis']['score'], 8)
        self.assertEqual(response.data['analysis']['sentiment'], 'positive')

    def test_poll_failed_job_surfaces_error(self):
        job = AnalysisJob.objects.create(
            call=self.call,
            status=AnalysisJob.Status.FAILED,
            error_message="OpenAI API timeout"
        )
        response = self.client.get(self._get_url(job.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'failed')
        self.assertEqual(response.data['error_message'], 'OpenAI API timeout')
        self.assertIsNone(response.data['analysis'])

    def test_poll_non_existent_job(self):
        url = self._get_url('00000000-0000-0000-0000-000000000000')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)


class WorkerUtilTests(TestCase):

    def test_format_transcript(self):
        result = format_transcript(VALID_TRANSCRIPT)
        self.assertIn("Rep: Hi John", result)
        self.assertIn("Prospect: Sure", result)
        self.assertEqual(len(result.split('\n')), 4)

    def test_compute_talk_ratio(self):
        result = compute_talk_ratio(VALID_TRANSCRIPT)
        self.assertIn('Rep', result)
        self.assertIn('Prospect', result)
        total = sum(result.values())
        self.assertAlmostEqual(total, 1.0, places=1)

    def test_compute_talk_ratio_empty(self):
        result = compute_talk_ratio([])
        self.assertEqual(result, {})


class WorkerIntegrationTests(TestCase):

    def setUp(self):
        self.call = Call.objects.create(
            title="Acme Demo",
            transcript=VALID_TRANSCRIPT
        )

    @patch('calls.worker.get_llm_provider')
    def test_run_analysis_success(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.analyse.return_value = MOCK_ANALYSIS
        mock_get_provider.return_value = mock_provider

        job = AnalysisJob.objects.create(call=self.call)

        from calls.worker import run_analysis
        run_analysis(str(job.id))

        job.refresh_from_db()
        self.assertEqual(job.status, AnalysisJob.Status.COMPLETED)
        self.assertTrue(hasattr(job, 'analysis'))
        self.assertEqual(job.analysis.score, 7)
        self.assertEqual(job.analysis.sentiment, 'neutral')

    @patch('calls.worker.get_llm_provider')
    def test_run_analysis_llm_failure_marks_job_failed(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.analyse.side_effect = Exception("OpenAI is down")
        mock_get_provider.return_value = mock_provider

        job = AnalysisJob.objects.create(call=self.call)

        from calls.worker import run_analysis
        try:
            run_analysis(str(job.id))
        except Exception:
            pass

        job.refresh_from_db()
        self.assertEqual(job.status, AnalysisJob.Status.FAILED)
        self.assertIn("OpenAI is down", job.error_message)

    def test_run_analysis_job_not_found(self):
        from calls.worker import run_analysis
        # should not raise, just log
        try:
            run_analysis('00000000-0000-0000-0000-000000000000')
        except Exception as e:
            self.fail(f"run_analysis raised unexpectedly: {e}")