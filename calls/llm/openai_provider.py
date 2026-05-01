
from openai import OpenAI
from .base import LLMProvider
from calls.prompts import SYSTEM_PROMPT
import json


class OpenAIProvider(LLMProvider):
    def __init__(self, config) -> None:
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model

        self.tool_schema = {
        "type": "function",
        "function": {
            "name": "save_analysis",
            "description": "Save the structured sales call analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "2-3 sentence overview of the call"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                        "description": "Overall prospect tone"
                    },
                    "key_topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Main topics discussed"
                    },
                    "score": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Overall call quality score"
                    },
                    "score_rationale": {
                        "type": "string",
                        "description": "1-2 sentences explaining the score"
                    },
                    "skill_gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific sales skills the rep struggled with. Examples: discovery questioning, objection handling, closing, rapport building. Only include where there is clear evidence in the transcript."
                    },

                    # --- rep-facing ---
                    "action_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Concrete commitments the rep made on this call"
                    },
                    "objections_raised": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Objections or concerns raised by the prospect"
                    },
                    "missed_opportunities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific moments where the rep could have done better — must be call-specific, not generic"
                    },
                    "coaching_tips": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 3,
                        "description": "Forward-looking, actionable tips for the rep's next call"
                    },

                    # --- manager-facing ---
                    "deal_stage_assessment": {
                        "type": "string",
                        "description": "One sentence on where the deal stands and whether it is progressing"
                    },
                    "recommended_manager_action": {
                        "type": "string",
                        "enum": ["no_action", "review_with_rep", "flag_for_pipeline_review"],
                        "description": "What the manager should do after reviewing this analysis"
                    },
                },
                "required": [
                    "summary", "sentiment", "key_topics", "talk_ratio",
                    "score", "score_rationale", "action_items", "objections_raised",
                    "missed_opportunities", "coaching_tips",
                    "deal_stage_assessment", "recommended_manager_action"
                ]
            }
        }
    }

    def analyse(self, formatted_transcript: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Analyse this sales call transcript:\n\n{formatted_transcript}"
                }
            ],
            tools=[self.tool_schema],
            tool_choice={"type": "function", "function": {"name": "save_analysis"}},
            timeout=60,
        )

        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)  # parse string → dict
