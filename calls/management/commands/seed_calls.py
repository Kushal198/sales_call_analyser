# management/commands/seed_calls.py
from django.core.management.base import BaseCommand
from calls.models import Call

SAMPLE_CALLS = [
    {
        "title": "Strong discovery call — Acme Corp",
        "transcript": [
            {"speaker": "Rep", "text": "Hi Sarah, before I jump into anything, I'd love to understand what's driving the urgency to look at solutions now."},
            {"speaker": "Prospect", "text": "We've had three reps quit in the last quarter and our onboarding time is killing us."},
            {"speaker": "Rep", "text": "That's significant. When you say onboarding time, are you measuring from hire date to first closed deal?"},
            {"speaker": "Prospect", "text": "Exactly. It's taking us four months when competitors are at six weeks."},
            {"speaker": "Rep", "text": "And what's the cost of that gap to you in real terms — lost pipeline, manager time?"},
            {"speaker": "Prospect", "text": "Conservatively about $200k per rep. We have six new hires starting next month."},
            {"speaker": "Rep", "text": "So the cost of doing nothing is over a million dollars. That's the number we need to solve against."},
            {"speaker": "Prospect", "text": "When you put it that way, yes."},
            {"speaker": "Rep", "text": "Let me show you exactly how we cut that onboarding window. Can we schedule a technical deep dive with your enablement lead this week?"},
            {"speaker": "Prospect", "text": "Yes, Thursday works. Send me a calendar invite."}
        ]
    },
    {
        "title": "Average call — budget objection mishandled — TechFlow Inc",
        "transcript": [
            {"speaker": "Rep", "text": "Hi John, thanks for jumping on the call today."},
            {"speaker": "Prospect", "text": "Sure, though I only have 20 minutes."},
            {"speaker": "Rep", "text": "What are your biggest challenges with your current CRM?"},
            {"speaker": "Prospect", "text": "Honestly the reporting is terrible and my team hates using it."},
            {"speaker": "Rep", "text": "That is exactly what we solve. Our reporting suite is drag and drop, takes 2 minutes to build a dashboard."},
            {"speaker": "Prospect", "text": "Sounds good but what does it cost? Our budget is pretty tight right now."},
            {"speaker": "Rep", "text": "We start at $200 per month for your team size. I can send over a full breakdown after this call."},
            {"speaker": "Prospect", "text": "Ok, send it over and we can revisit next week."},
            {"speaker": "Rep", "text": "Perfect, I will send the pricing doc today and follow up Friday. Does that work?"},
            {"speaker": "Prospect", "text": "Friday works."}
        ]
    },
    {
        "title": "Poor call — no discovery — GlobalSales Ltd",
        "transcript": [
            {"speaker": "Rep", "text": "Hi Mike, let me tell you about our platform. We have AI-powered analytics, automated reporting, pipeline forecasting..."},
            {"speaker": "Prospect", "text": "Ok..."},
            {"speaker": "Rep", "text": "We also integrate with Salesforce, HubSpot, and over 50 other tools. Our customers see 30% productivity gains."},
            {"speaker": "Prospect", "text": "That sounds interesting but I'm not sure it's relevant to us."},
            {"speaker": "Rep", "text": "Oh it's definitely relevant. Everyone in your industry uses us. We have case studies I can send over."},
            {"speaker": "Prospect", "text": "Sure, send them over."},
            {"speaker": "Rep", "text": "Great. I'll send everything across. Talk soon."},
            {"speaker": "Prospect", "text": "Ok bye."}
        ]
    },
]

class Command(BaseCommand):
    help = 'Seed the database with sample sales calls'

    def handle(self, *args, **kwargs):
        for data in SAMPLE_CALLS:
            call = Call.objects.create(**data)
            self.stdout.write(f"Created call: {call.id} — {call.title}")
        self.stdout.write(self.style.SUCCESS(f'\nSeeded {len(SAMPLE_CALLS)} calls. Use any id above to trigger analysis.'))