import random
from datasets import load_dataset
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
                max_tokens=1024,
                system=f"You are a helpful assistant that can answer questions. Today's date is 2024-{month:02d}-15.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
            if attempt == max_retries - 1:
                raise e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except Exception as e:
            raise e

def evaluate_claude(problem, month):
    question = problem["question"]
    correct_answer = problem["answer"].split("###")[-1]

    correct_answer = "".join(c for c in correct_answer.strip() if c.isdigit() or c == ".")
    
    prompt = f"Please solve this problem step by step and put the answer on the last line:\n\n{question}\n\nRemember to only output the answer and nothing else on the last line."
    traces = []
        
    response = get_response(prompt, month)
    traces.append({"prompt": prompt, "response": response})
    
    final_answer = "".join(c for c in response.split("\n")[-1].strip() if c.isdigit() or c == ".")
    
    is_correct = final_answer == correct_answer
    
    result = {
        "is_correct": is_correct,
        "traces": traces,
    }
    
    return result


def main():
    dataset = load_dataset("openai/gsm8k", "main")
    train_data = dataset["train"]

    # Select 1000 random problems from the training set
    num_problems = 1000
    random_indices_file = f"selected_problems_gsm8k.json"
    if os.path.exists(random_indices_file):
        with open(random_indices_file, "r") as f:
            selected_indices = json.load(f)
    else:
        selected_indices = random.sample(range(len(train_data)), num_problems)
        with open(random_indices_file, "w") as f:
            json.dump(selected_indices, f)

    selected_problems = [train_data[i] for i in selected_indices]

    results = {}
    traces_folder = f"traces"
    os.makedirs(traces_folder, exist_ok=True)

    def process_month(month):
        monthly_traces_file = f"{traces_folder}/month_{month:02d}_traces.json"
        if os.path.exists(monthly_traces_file):
            with open(monthly_traces_file, "r") as f:
                monthly_traces = json.load(f)
            correct_count = sum(1 for result in monthly_traces if result["is_correct"])
            start_index = len(monthly_traces)
            print(f"Month {month:02d} | Resuming from existing traces | Problems solved: {start_index} | Correct: {correct_count}")
        else:
            monthly_traces = []
            correct_count = 0
            start_index = 0

        progress_bar = tqdm(selected_problems[start_index:], initial=start_index, total=len(selected_problems), desc=f"Month {month:02d}", leave=False)
        for i, problem in enumerate(progress_bar, start=start_index):
            result = evaluate_claude(problem, month)
            if result["is_correct"]:
                correct_count += 1
            monthly_traces.append(result)
            accuracy_so_far = correct_count / (i + 1)
            with open(monthly_traces_file, "w") as f:
                json.dump(monthly_traces, f, indent=2)
            progress_bar.set_description(f"Month {month:02d} | Progress: {i+1}/{len(selected_problems)} | Correct: {correct_count} | Accuracy: {accuracy_so_far:.2%}")
        return correct_count

    # Use concurrent.futures to process all months simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_to_month = {executor.submit(process_month, month): month for month in range(1, 13)}
        for future in concurrent.futures.as_completed(future_to_month):
            month = future_to_month[future]
            try:
                correct_count = future.result()
                results[f"month_{month:02d}"] = correct_count
            except Exception as exc:
                print(f'Month {month:02d} generated an exception: {exc}')

    # Save overall results
    with open(f"{traces_folder}/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()