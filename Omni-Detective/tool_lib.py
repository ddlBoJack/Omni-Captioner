import json
import requests
import time
from prompt_lib import OmniDetectiveToolPrompt
def LALM(api, url, prompt, model_name="qwen3-omni-flash"):
    if model_name == "qwen3-omni-flash":
        messages = [
                {"role": "user", "content": [
                    {"type": "input_audio", "input_audio": {"data": url, "format": "wav"}},
                    {"type": "text", "text": OmniDetectiveToolPrompt.LALM.user_prompt(prompt)},
                ]},
            ]
        payload = {
            "model": model_name,
            "messages": messages,
            "modalities": ["text"],
        }
    
    elif model_name == "gemini-2.5-pro":
        messages = [
                {"role": "system", "content": OmniDetectiveToolPrompt.LALM.system_prompt()},
                {"role": "user", "content": [
                    {"type": "audio_url", "audio_url": {"url": url}},
                    {"type": "text", "text": OmniDetectiveToolPrompt.LALM.user_prompt(prompt)},
                ]},
            ]
        payload = {
            "model": model_name,
            "messages": messages,
            "dashscope_extend_params": {"provider": "google"},
        }

    else:
        raise ValueError("Invalid model name")


    retry_count = 0
    for _ in range(api.MAX_API_RETRY):
        try:
            response = requests.post(api.url, headers=api.headers, json=payload)
            response.raise_for_status()
            response = response.json()
            # print(response)
            content = response['choices'][0]['message']['content'].strip()
            return content
        except Exception as e:
            retry_count += 1
            print(f"Error processing item: {e}, retry {retry_count} times")
            time.sleep(api.LLM_MIT_RETRY_SLEEP)
    return None

# Add more tools here, for example, whisper for asr, qwen3-omni-captioner for detailed captionng, ocr, music analysis, etc.
def ASR(url_clip, prompt):
    return "This is the ASR result."

def OCR(url_pic, prompt):
    return "This is the OCR result."