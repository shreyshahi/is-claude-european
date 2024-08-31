import json
import csv
from datetime import datetime
import concurrent.futures
import os

def process_month(month):
    system_date = datetime(2024, month, 15).strftime("%Y-%m-%d")
    correct_count = 0
    response_lengths = []

    file_path = f"traces/month_{month:02d}_traces.json"
    if not os.path.exists(file_path):
        return None, None

    with open(file_path, 'r') as f:
        data = json.load(f)
        for i, d in enumerate(data):
            correct_count += d['is_correct']
            response_lengths.append((system_date, i+1, len(d['traces'][0]['response'])))

    return (system_date, correct_count), response_lengths

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_to_month = {executor.submit(process_month, month): month for month in range(1, 13)}
        
        correct_counts = []
        all_response_lengths = []
        
        for future in concurrent.futures.as_completed(future_to_month):
            result = future.result()
            if result[0] is not None:
                correct_counts.append(result[0])
                all_response_lengths.extend(result[1])

    # Write correct counts to CSV
    with open('correct_counts.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['system_date', 'num_correct'])
        writer.writerows(correct_counts)

    # Write response lengths to CSV
    with open('response_lengths.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['system_date', 'problem_number', 'num_characters'])
        writer.writerows(all_response_lengths)

if __name__ == "__main__":
    main()