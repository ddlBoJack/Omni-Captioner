import json
import requests
import time

from prompt_lib import OmniDetectiveAgentPrompt
from tool_lib import *

class OmniDetectiveAgent:
    def __init__(self, api, agent_model="chatgpt-4o-latest", observer_tools=None, max_calls=10, url=None):
        self.agent_model = agent_model
        self.observer_tools = observer_tools
        self.api = api
        self.max_calls = max_calls
        self.calls_left = max_calls
        self.url = url
        self.history = []

        self.agent_sys_prompt = OmniDetectiveAgentPrompt.agent_sys_prompt
        self.agent_first_prompt = OmniDetectiveAgentPrompt.agent_first_prompt
        self.agent_prompt = OmniDetectiveAgentPrompt.agent_prompt
        self.agent_final_prompt = OmniDetectiveAgentPrompt.agent_final_prompt

        self.history.append({"role": "system", "content": self.agent_sys_prompt(max_calls=self.max_calls, tool_list=json.dumps(self.observer_tools, indent=None, ensure_ascii=False))})

    def check_agent_response_format(self, data):
        if not isinstance(data, dict):
            print("Agent format error: output is not a dict")
            return False

        if "tool_name" not in data or "question" not in data:
            print("Agent format error: missing 'tool_name' or 'question'")
            return False

        valid_tools = {tool["tool_name"] for tool in self.observer_tools}
        if data["tool_name"] not in valid_tools:
            print(f"Agent format error: invalid tool_name '{data['tool_name']}'")
            return False

        if not isinstance(data["question"], str) or not data["question"].strip():
            print("Agent format error: 'question' must be a non-empty string")
            return False

        return True
    def call_agent(self, prompt, check=True):
        messages = self.history + [{"role": "user", "content": prompt}]
        payload = {
            "model": self.agent_model,
            "messages": messages,
        }
        
        retry_count = 0
        for _ in range(self.api.MAX_API_RETRY):
            try:
                response = requests.post(self.api.url, headers=self.api.headers, json=payload)
                response.raise_for_status()
                response = response.json()
                # print(response)
                content = response['choices'][0]['message']['content'].strip()

                if check:
                    content = content.replace('```json', '').replace('```', '').strip()
                    parsed = json.loads(content)
                    if parsed and self.check_agent_response_format(parsed):
                        return parsed
                    else:
                        retry_count += 1
                        print(f"[Attempt {retry_count}] Agent format check failed, retrying...")
                        continue
                else:
                    return content
            except Exception as e:
                retry_count += 1
                print(f"Error processing item: {e}, retry {retry_count} times")
                time.sleep(self.api.LLM_MIT_RETRY_SLEEP)
        return None
    
    def call_observer(self, tool_name, prompt):
        if tool_name == "LALM":
            return LALM(self.api, self.url, prompt)
        # Add more tools here, for example, whisper for asr, qwen3-omni-captioner for detailed captionng, ocr, music analysis, etc.

    def run(self):
        agent_response = ""
        observer_response = ""
        while self.calls_left > 0:
            print("Calling left: ", self.calls_left)
            if self.calls_left == self.max_calls:
                agent_prompt = self.agent_first_prompt(calls_left=self.calls_left)
            else:
                agent_prompt = self.agent_prompt(observation=observer_response, calls_left=self.calls_left)
            agent_response = self.call_agent(agent_prompt, check=True)
            observer_response = self.call_observer(agent_response["tool_name"], agent_response["question"])

            self.calls_left -= 1
            self.history.append({"role": "user", "content": agent_prompt})
            self.history.append({"role": "assistant", "content": json.dumps(agent_response, indent=None, ensure_ascii=False)})

        if self.calls_left == 0:
            print("Calling left: ", self.calls_left)
            agent_prompt = self.agent_final_prompt(observation=observer_response)
            agent_response = self.call_agent(agent_prompt, check=False)
            self.history.append({"role": "user", "content": agent_prompt})
            self.history.append({"role": "assistant", "content": json.dumps(agent_response, indent=None, ensure_ascii=False)})
            return self.history