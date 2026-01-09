import os
import json
from openai import OpenAI
from config import Config

class AnalyzerService:
    def __init__(self):
        Config.validate_keys()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.prompts = {
            "default_analysis": {
                "system": "You are an expert academic researcher assisting with a systematic literature review.",
                "user": """Please analyze the following scientific paper content and extract the desired information.

PAPER CONTENT:
{text}

INSTRUCTIONS:
Provide a JSON response with the following fields:
- Summary: A concise summary of the paper (max 150 words).
- Methodology: validation method used (e.g., case study, experiment, survey).
- Key Findings: Bullet points of main results.
- Research Gap: What problem does this paper solve?
- Limitations: Any mentioned limitations.

If information is missing, use "N/A"."""
            },
            "summarization": {
                "system": "You are a helpful research assistant.",
                "user": """Summarize the following paper in less than 200 words, focusing on the contribution and results.

TEXT:
{text}"""
            }
        }

    def _load_prompts(self):
        # Deprecated
        return self.prompts

    def analyze_text(self, text: str, prompt_key: str = "default_analysis", custom_fields: list = None, model: str = "gpt-5-mini") -> dict:
        """
        Analyze text using OpenAI API.
        If custom_fields is provided, it dynamically constructs the prompt.
        """
        if not text:
            return {"error": "No text provided"}
            
        # Truncate text if too long (rough safety check, e.g. 100k chars ~ 25k tokens)
        max_chars = 100000 
        if len(text) > max_chars:
            print(f"Truncating text from {len(text)} to {max_chars} chars")
            text = text[:max_chars] + "...[TRUNCATED]"

        if custom_fields:
            # Dynamic Prompt Construction
            system_msg = "You are an expert academic researcher. Extract specific information from the paper."
            
            fields_str = "\n".join([f"- {field}" for field in custom_fields])
            
            user_msg = f"""
            Please analyze the following scientific paper content and extract the information for the specific fields listed below.
            
            FIELDS TO EXTRACT:
            {fields_str}
            
            PAPER CONTENT:
            {text}
            
            INSTRUCTIONS:
            Provide a valid JSON response where the keys are the field names listed above, and the values are the extracted information.
            If information is missing, set the value to "N/A".
            """
        else:
            # Static Prompt from YAML
            prompt_config = self.prompts.get(prompt_key, {})
            if not prompt_config:
                return {"error": f"Prompt key '{prompt_key}' not found"}

            system_msg = prompt_config.get("system", "You are a helpful assistant.")
            user_template = prompt_config.get("user", "{text}")
            user_msg = user_template.replace("{text}", text)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return {"error": str(e)}
