
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
                            "description": "Main topics discussed in the call"
                        },
                        "action_items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific things the rep must do after this call"
                        },
                        "objections_raised": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Objections or concerns raised by the prospect"
                        },
                        "next_steps": {
                            "type": "string",
                            "description": "What was agreed as the next step to move the deal forward"
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
                    },
                    "required": [
                        "summary",
                        "sentiment",
                        "key_topics",
                        "action_items",
                        "objections_raised",
                        "next_steps",
                        "score",
                        "score_rationale",
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
