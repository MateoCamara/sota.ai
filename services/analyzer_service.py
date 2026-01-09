
import os
import yaml
import json
from openai import OpenAI
from config import Config

class AnalyzerService:
    def __init__(self):
        Config.validate_keys()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", "prompts.yaml"), "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            return {}

    def analyze_text(self, text: str, prompt_key: str = "default_analysis", custom_fields: list = None, model: str = "gpt-4o-mini") -> dict:
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
