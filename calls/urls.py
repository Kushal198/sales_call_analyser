from django.urls import path
from .views import CallListCreateView, AnalyseTriggerView, JobStatusView

urlpatterns = [
    path('calls/', CallListCreateView.as_view(), name='call-list-create'),
    path('calls/<uuid:call_id>/analyse/', AnalyseTriggerView.as_view(), name='analyse-trigger'),
    path('jobs/<uuid:job_id>/', JobStatusView.as_view(), name='job-status'),
]