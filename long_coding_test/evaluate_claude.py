import anthropic
import os
import json
from tqdm import tqdm
import time
import concurrent.futures

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_response(prompt, month):
    max_retries = 5
    base_delay = 1
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=8192,
                system=f"You are a helpful assistant that can answer questions. Today's date is 2024-{month:02d}-15.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text, response.usage.output_tokens
        except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
            if attempt == max_retries - 1:
                raise e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except Exception as e:
            raise e

def evaluate_claude(month):
    prompt = """
    Write a convolutional neural network to classify imagenet dataset.
    Implement the neural network in python without using any machine learning libraries and manually implement backpropagation from scratch.
    Explain your code as you go along. Be as detailed as possible and explain how one can speed up the code with bare metal CUDA code.
    """
    response, response_length = get_response(prompt, month)
    return {"prompt": prompt, "response": response, "response_length": response_length}

def process_month(month):
    monthly_traces_file = f"traces/month_{month:02d}_traces.json"
    if os.path.exists(monthly_traces_file):
        with open(monthly_traces_file, "r") as f:
            monthly_traces = json.load(f)
        start_index = len(monthly_traces)
        print(f"Month {month:02d} | Resuming from existing traces | Problems solved: {start_index}")
    else:
        monthly_traces = []
        start_index = 0

    total_response_length = sum(trace["response_length"] for trace in monthly_traces)
    progress_bar = tqdm(range(start_index, 500), initial=start_index, total=500, desc=f"Month {month:02d}", leave=False)
    for _ in progress_bar:
        result = evaluate_claude(month)
        monthly_traces.append(result)
        total_response_length += result["response_length"]
        avg_response_length = total_response_length / len(monthly_traces)
        with open(monthly_traces_file, "w") as f:
            json.dump(monthly_traces, f, indent=2)
        progress_bar.set_description(f"Month {month:02d} | Progress: {len(monthly_traces)}/500 | Avg Response Length: {avg_response_length:.2f}")
    return avg_response_length

def main():
    os.makedirs("traces", exist_ok=True)
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_to_month = {executor.submit(process_month, month): month for month in range(1, 13)}
        for future in concurrent.futures.as_completed(future_to_month):
            month = future_to_month[future]
            try:
                avg_response_length = future.result()
                results[f"month_{month:02d}"] = avg_response_length
            except Exception as exc:
                print(f'Month {month:02d} generated an exception: {exc}')

    with open("traces/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()