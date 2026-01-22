import os
import json
from openai import OpenAI
import ollama
from config import Config

class AnalyzerService:
    def __init__(self):
        self.openai_client = None
        self.ollama_host = Config.OLLAMA_BASE_URL
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

    def _get_openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self.openai_client is None:
            Config.validate_keys("openai")
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        return self.openai_client

    def _build_messages(self, text: str, prompt_key: str, custom_fields: list, for_ollama: bool = False):
        """Build system and user messages for the LLM."""
        json_instruction = ""
        if for_ollama:
            json_instruction = "\n\nIMPORTANT: You MUST respond with ONLY valid JSON. No explanations, no markdown, just the JSON object."

        if custom_fields:
            system_msg = "You are an expert academic researcher. Extract specific information from the paper."
            fields_str = "\n".join([f"- {field}" for field in custom_fields])
            user_msg = f"""Please analyze the following scientific paper content and extract the information for the specific fields listed below.

FIELDS TO EXTRACT:
{fields_str}

PAPER CONTENT:
{text}

INSTRUCTIONS:
Provide a valid JSON response where the keys are the field names listed above, and the values are the extracted information.
If information is missing, set the value to "N/A".{json_instruction}"""
        else:
            prompt_config = self.prompts.get(prompt_key, {})
            if not prompt_config:
                return None, None, f"Prompt key '{prompt_key}' not found"
            system_msg = prompt_config.get("system", "You are a helpful assistant.")
            user_template = prompt_config.get("user", "{text}")
            user_msg = user_template.replace("{text}", text) + json_instruction

        return system_msg, user_msg, None

    def analyze_text(self, text: str, prompt_key: str = "default_analysis", custom_fields: list = None,
                     model: str = "gpt-4o-mini", provider: str = "openai") -> dict:
        """
        Analyze text using OpenAI or Ollama.

        Args:
            text: The paper text to analyze
            prompt_key: Key for static prompts (default_analysis, summarization)
            custom_fields: List of custom fields to extract (overrides prompt_key)
            model: Model name (e.g., 'gpt-4o-mini' for OpenAI, 'llama3' for Ollama)
            provider: 'openai' or 'ollama'
        """
        if not text:
            return {"error": "No text provided"}

        # Truncate text if too long
        max_chars = 100000
        if len(text) > max_chars:
            print(f"Truncating text from {len(text)} to {max_chars} chars")
            text = text[:max_chars] + "...[TRUNCATED]"

        system_msg, user_msg, error = self._build_messages(
            text, prompt_key, custom_fields, for_ollama=(provider == "ollama")
        )
        if error:
            return {"error": error}

        if provider == "ollama":
            return self._analyze_with_ollama(system_msg, user_msg, model)
        else:
            return self._analyze_with_openai(system_msg, user_msg, model)

    def _analyze_with_openai(self, system_msg: str, user_msg: str, model: str) -> dict:
        """Call OpenAI API."""
        try:
            client = self._get_openai_client()
            response = client.chat.completions.create(
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

    def _analyze_with_ollama(self, system_msg: str, user_msg: str, model: str) -> dict:
        """Call Ollama API."""
        try:
            client = ollama.Client(host=self.ollama_host)
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                format="json"
            )
            content = response['message']['content']
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Ollama returned invalid JSON: {e}")
            return {"error": f"Invalid JSON response from Ollama: {str(e)}"}
        except Exception as e:
            print(f"Ollama API Error: {e}")
            return {"error": str(e)}
