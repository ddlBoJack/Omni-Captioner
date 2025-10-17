import os
import json
from tqdm import tqdm
import argparse

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import threading
write_lock = threading.Lock()

from agent_lib import OmniDetectiveAgent

class API():
    def __init__(self):
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_key = "YOUR_API_KEY"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }
        self.MAX_API_RETRY = 1000
        self.LLM_MIT_RETRY_SLEEP = 0.1

tools = [
    {
        "tool_name": "LALM",
        "description": "get the answer from an audio clip and a question",
    },
    # Add more tools here, for example, whisper for asr, qwen3-omni-captioner for detailed captionng, ocr, music analysis, etc.
]

def omni_detective_agent(line, fout):
    try:
        item = json.loads(line.strip())
        public_url = item.get("url", None)
        agent = OmniDetectiveAgent(
            api=API(),
            agent_model="gpt-4.1-2025-04-14",
            observer_tools=tools,
            max_calls=10,
            url=public_url
        )
        result = agent.run()
        item["omni_detective_trajectory"] = result
        output_line = json.dumps(item, ensure_ascii=False) + '\n'
        with write_lock:
            fout.write(output_line)
            fout.flush()
    except Exception as e:
        print(f"Error processing item: {e}")

def run_parallel(num_workers=10, function=None, input_path=None, output_path=None):
    key = "id"

    if os.path.exists(output_path):
        with open(output_path, 'r') as fin:
            id_list = [json.loads(line)[key] for line in fin]
    else:
        id_list = []

    with open(input_path, 'r') as fin, open(output_path, 'a') as fout:
        lines = fin.readlines()
        if key in json.loads(lines[0]):
            lines = [line for i, line in enumerate(lines) if json.loads(line)[key] not in id_list]
        else:
            lines = [line for i, line in enumerate(lines)]
        if num_workers > 1:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(function, line, fout) for line in lines]
                for _ in tqdm(as_completed(futures), total=len(futures)):
                    pass
        elif num_workers == 1:
            for line in tqdm(lines):
                function(line, fout)
        else:
            raise ValueError('num_workers must be greater than 0')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Run omni detective agent in parallel")
    parser.add_argument("--input_path", type=str, required=True, help="Path to input file (.jsonl)")
    parser.add_argument("--output_path", type=str, required=True, help="Path to output file (.jsonl)")
    parser.add_argument("--num_workers", type=int, default=10, help="Number of parallel workers")

    args = parser.parse_args()

    run_parallel(
        num_workers=args.num_workers,
        function=omni_detective_agent,
        input_path=args.input_path,
        output_path=args.output_path
    )