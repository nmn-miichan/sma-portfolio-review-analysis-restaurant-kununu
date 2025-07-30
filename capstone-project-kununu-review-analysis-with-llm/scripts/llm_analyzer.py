import google.generativeai as genai
import google.ai.generativelanguage as glm
import json
import os
import time
import glob
import re
from datetime import datetime

def configure_genai(api_key):
    genai.configure(api_key=api_key)

def extract_company_name_from_filename(filename):
    basename = os.path.basename(filename)
    name_without_ext = os.path.splitext(basename)[0]
    
    if name_without_ext.startswith("scraped_reviews_"):
        parts = name_without_ext.split("_")
        if len(parts) >= 4:
            company_parts = parts[2:-2] if len(parts) > 4 else [parts[2]]
            return "_".join(company_parts)
    
    return name_without_ext


def get_current_date():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def extract_json_from_response(response_text):
    json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
    if json_match:
        extracted = json_match.group(1).strip()
        return extracted
    return response_text

def process_individual_prompts(input_data, prompt_number, company_name, current_date, api_key, max_retries=5):
    
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-05-20",
    )
    
    prompt_file = f'./prompts/prompt_{prompt_number}.txt'
    
    if not os.path.exists(prompt_file):
        print(f"Error: Prompt file not found: {prompt_file}")
        return None
        
    with open(prompt_file, 'r', encoding='utf-8') as file:
        prompt = file.read()
            
    prompt = prompt + "\n\nHier sind die zu analysierenden Daten:\n" + json.dumps(input_data, ensure_ascii=False, indent=2)
            
    print(f"Processing prompt_{prompt_number}.txt...")
            
    retry_count = 0
    response_text = None
    
    while retry_count < max_retries:
        try:
            response = model.generate_content(prompt)
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = candidate.finish_reason
                    print(f"Finish reason: {finish_reason}")
                    
                    if finish_reason == 2:  # MAX_TOKENS
                        print(f"Response truncated due to max tokens. Retry {retry_count + 1}/{max_retries}")
                        retry_count += 1
                        time.sleep(30)
                        continue
                    elif finish_reason == 3:  # SAFETY
                        print("Response blocked due to safety filters")
                        retry_count += 1
                        time.sleep(30)
                        continue
            
            response_text = response.text
            
            if len(response_text) < 500:
                print(f"Response too short ({len(response_text)} chars). Retry {retry_count + 1}/{max_retries}")
                retry_count += 1
                time.sleep(30)
                continue
            
            print(f"Valid response received ({len(response_text)} characters)")
            break
            
        except ValueError as e:
            print(f"ValueError occurred: {e}")
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Max retries ({max_retries}) reached. Skipping prompt_{prompt_number}")
                return None
            print(f"Retrying... ({retry_count}/{max_retries})")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Max retries ({max_retries}) reached. Skipping prompt_{prompt_number}")
                return None
            time.sleep(5)
    
    if retry_count >= max_retries or response_text is None:
        print(f"Failed to get valid response after {max_retries} retries")
        return None

    clean_json_text = extract_json_from_response(response_text)
    
    try:
        parsed_json = json.loads(clean_json_text)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        parsed_json = {"raw_response": clean_json_text}
    
    response_data = {"response": parsed_json}

    responses_dir = f"./responses/response_{company_name}_{current_date}"
    os.makedirs(responses_dir, exist_ok=True)
    
    response_output_path = f"{responses_dir}/response_{company_name}_{current_date}_{prompt_number}.json"
    with open(response_output_path, "w", encoding="utf-8") as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
        
    return response_data

def combine_json_responses(company_name, current_date, selected_prompts, responses_dir="./responses"):
    json_files = []
    for prompt_num in selected_prompts:
        file_path = os.path.join(responses_dir, f"response_{company_name}_{current_date}",
                                 f"response_{company_name}_{current_date}_{prompt_num}.json")
        if os.path.exists(file_path):
            json_files.append(file_path)
    

    json_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
    
    all_responses = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                response_data = json.load(f)
                
                if isinstance(response_data, dict) and "response" in response_data:
                    all_responses.append(response_data["response"])
                else:
                    all_responses.append(response_data)
                
                print(f"Loaded {os.path.basename(json_file)}")
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    combined_data = {"categories": all_responses}
    
    results_dir = "./results"
    os.makedirs(results_dir, exist_ok=True)
    output_file = os.path.join(results_dir, f"result_{company_name}_{current_date}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    
    print(f"Combined results saved to: {output_file}")


def process_prompts_and_generate_responses(input_data, company_name, current_date, api_key, start_prompt=1, end_prompt=13):
    for i in range(start_prompt, end_prompt + 1):
        result = process_individual_prompts(input_data, i, company_name, current_date, api_key)
        if result is None:
            print(f"Skipping prompt {i} due to errors")
        time.sleep(30)

def main(input_file_path=None, api_key=None):
    if input_file_path is None:
        data_dir = "./data"
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        
        if not json_files:
            print("No JSON files found in ./data/ directory")
            return
        
        input_file_path = max(json_files, key=os.path.getmtime)
        print(f"Using input file: {input_file_path}")
    
    company_name = extract_company_name_from_filename(input_file_path)
    current_date = get_current_date()
    
    print(f"Company: {company_name}")
    print(f"Date: {current_date}")
    
    with open(input_file_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    
    if api_key:
        process_prompts_and_generate_responses(input_data, company_name, current_date, api_key, 1, 13)
    else:
        print("Error: API key is required")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        api_key = sys.argv[2]
        main(input_file, api_key)
    else:
        print("Usage: python llm_analyzer.py <input_file> <api_key>")
