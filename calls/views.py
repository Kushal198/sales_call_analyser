from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Call, AnalysisJob
from .serializers import AnalysisJobCreatedSerializer, CallSerializer, AnalysisJobSerializer
from .worker import dispatch_analysis
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    request=CallSerializer,
    examples=[
        OpenApiExample(
            'Sample Sales Call',
            value={
                "title": "Demo call with Customer",
                "transcript": [
                    {"speaker": "Rep", "text": "Hi John, thanks for jumping on the call today."},
                    {"speaker": "Prospect", "text": "Sure, though I only have 20 minutes."},
                ]
            },
            request_only=True
        )
    ]
)
class CallListCreateView(APIView):
    serializer_class = CallSerializer
    def get(self, request):
        calls = Call.objects.all().order_by('-created_at')
        serializer = CallSerializer(calls, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CallSerializer(data=request.data)
        if serializer.is_valid():
            call = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=None,  
    responses={
        202: AnalysisJobCreatedSerializer
    },
    examples=[
        OpenApiExample(
            'Trigger Analysis',
            value={
                "job_id": "79b39d11-a1a2-4a58-bcb2-cd9ff7f545e2",
                "status": "pending"
            },
            response_only=True
        )
    ]
)
class AnalyseTriggerView(APIView):
    def post(self, request, call_id):
        if not Call.objects.filter(id=call_id).exists():
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            active_job = (
                AnalysisJob.objects
                .select_for_update()
                .filter(
                    call_id=call_id,
                    status__in=[AnalysisJob.Status.PENDING, AnalysisJob.Status.RUNNING]
                ).first()
            )

            if active_job:
                return Response(
                    {"job_id": active_job.id, "status": active_job.status, "detail": "Analysis already in progress"},
                    status=status.HTTP_200_OK
                )

            job = AnalysisJob.objects.create(call_id=call_id)

        dispatch_analysis(job.id)
        return Response(
            {"job_id": job.id, "status": job.status},
            status=status.HTTP_202_ACCEPTED
        )

@extend_schema(
    responses={200: AnalysisJobSerializer}
)
class JobStatusView(APIView):

    def get(self, request, job_id):
        try:
            job = AnalysisJob.objects.select_related('analysis').get(id=job_id)
        except AnalysisJob.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AnalysisJobSerializer(job)
        return Response(serializer.data)


@extend_schema(
    responses={200: AnalysisJobSerializer(many=True)},
)
class CallJobsListView(APIView):
    def get(self, request, call_id):
        if not Call.objects.filter(id=call_id).exists():
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        jobs = AnalysisJob.objects.filter(call_id=call_id).select_related('analysis')
        serializer = AnalysisJobSerializer(jobs, many=True)
        return Response(serializer.data)