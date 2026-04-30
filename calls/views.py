from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Call, AnalysisJob
from .serializers import CallSerializer, AnalysisJobSerializer
from .worker import dispatch_analysis


class CallListCreateView(APIView):

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


class AnalyseTriggerView(APIView):

    def post(self, request, call_id):
        try:
            call = Call.objects.get(id=call_id)
        except Call.DoesNotExist:
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        job = AnalysisJob.objects.create(call=call)
        dispatch_analysis(job.id)

        return Response(
            {"job_id": job.id, "status": job.status},
            status=status.HTTP_202_ACCEPTED
        )


class JobStatusView(APIView):

    def get(self, request, job_id):
        try:
            job = AnalysisJob.objects.get(id=job_id)
        except AnalysisJob.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AnalysisJobSerializer(job)
        return Response(serializer.data)