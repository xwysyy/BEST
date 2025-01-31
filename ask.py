import os
import yaml
import concurrent.futures
from openai import OpenAI
from dotenv import load_dotenv
from init import model_path, problem_path, data_path, generate_k
import re
import json

load_dotenv()
with open(model_path, 'r', encoding='utf-8') as file:
    models_config = yaml.load(file, Loader=yaml.FullLoader)
models_list = [
    model for model in list(models_config.keys()) 
    if models_config[model].get('enabled', False) 
]
with open(f'{data_path}/prompt.txt', 'r', encoding='utf-8') as f:
    prompt = f.read()

def find_last_odd_backtick_position(code):
    backtick_positions = []
    index = 0
    while True:
        index = code.find("```", index)
        if index == -1:
            break
        backtick_positions.append(index)
        index += 3  

    for k in range(len(backtick_positions) // 2):
        odd_index = len(backtick_positions) - (2 * k + 1)
        even_index = len(backtick_positions) - (2 * k + 2)

        if odd_index < 0 or even_index < 0:
            continue

        if "Solution" in code[backtick_positions[even_index]:backtick_positions[odd_index]]:
            return backtick_positions[odd_index]

    for k in range(len(backtick_positions) // 2):
        odd_index = len(backtick_positions) - (2 * k + 2)
        even_index = len(backtick_positions) - (2 * k + 3)

        # Ensure odd_index and even_index are within range
        if odd_index < 0 or even_index < 0:
            continue

        # Check if "Solution" is between two "```"
        if "Solution" in code[backtick_positions[even_index]:backtick_positions[odd_index]]:
            return backtick_positions[odd_index]


    return -1  # If no matching "```" is found  

def cut_code(code: str):
    pos = []
    endplace = find_last_odd_backtick_position(code)  # Find the position of the last "```"  
    if endplace == -1:
        return code

    # Find all positions of class and struct  
    index = 0
    while index < len(code):
        class_pos = code.find('class', index)
        struct_pos = code.find('struct', index)

        if class_pos == -1 and struct_pos == -1:
            break

        if class_pos != -1 and (struct_pos == -1 or class_pos < struct_pos):
            pos.append(class_pos)
            index = class_pos + 1
        else:
            pos.append(struct_pos)
            index = struct_pos + 1
    # Find the smallest k such that there is no "```" between pos[k] and endplace  
    k = -1
    for i in range(len(pos)):
        if pos[i] < endplace:
            if code[pos[i]:endplace].find('```') == -1:
                k = i
                break
    # print(len(pos))

    # Extract the characters between pos[k] and endplace  
    if k != -1:
        start_pos = pos[k]
        result = code[start_pos:endplace]

        # Use a regular expression to find "main(", allowing multiple spaces  
        pattern = r'main\s*\('
        main_match = re.search(pattern, code[start_pos:endplace])

        if main_match:
            main_pos = main_match.start() + start_pos  # Calculate the position in the original code  
           # Search for the first "}" before "main("  
            brace_pos = code.rfind('}', start_pos, main_pos)
            if brace_pos != -1:
                result = code[start_pos:brace_pos]
        
        return result
    else:
        return code

def get_code(question: str, model: str, api_key: str, base_url: str):
    """
    Call the specified large model API to generate code for the given question.  
    `question` is the problem description, and `model` is the name of the large model.  
    """
    api_key = os.getenv(api_key)
    if api_key is None:
        raise ValueError('API Key not found')
    client = OpenAI(api_key = api_key, base_url = base_url)
    chat_completion = client.chat.completions.create(
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user","content": question}
        ],
        max_tokens=4096,
        model = model,
    )
    
    code = chat_completion.choices[0].message.content
    code = '\n' + code
    code = cut_code(code)
    tem_name = re.sub(r'[^a-zA-Z0-9_]', '_', model).upper()
    code = f'#ifndef {tem_name}_H\n#define {tem_name}_H\n#include <bits/stdc++.h>\nusing namespace std;\n\n{code}\n\n#endif'
    return code

def ask(id: str, models: list = models_list, level: str = None):
    """
    Call all enabled large model APIs to generate code for the given question.  
    `id` is the question ID, and `models_list` is the list of large models.  
    By default, it uses the enabled models but can specify a model.  
    """
    os.makedirs(problem_path, exist_ok=True)
    path = f'{problem_path}/{id}'
    if not os.path.exists(path):
        raise ValueError('Problem not found')
    if not os.path.exists(f'{path}/desc/desc.md'):
        raise ValueError('Problem description not found')
    with open(f'{path}/desc/desc.md', 'r', encoding='utf-8') as f:
        problem = f.read()
    
    with open(f'{path}/problem.json', 'r', encoding='utf-8') as f:
        problem_json = json.load(f)
        data_ = problem_json['data'][-1]
        time_limit = problem_json['time_limit']
        memory_limit = problem_json['memory_limit'][-1]

    problem = problem.replace('@data', str(data_))
    problem = problem.replace('@time_limit', str(time_limit))

    path = f'{path}/codes'
    os.makedirs(path, exist_ok=True)

    def save_code_for_model_and_level(model: str, level_tem: int, desc:str):
        """
        Generate and save code for the specified model and level.  
        """
        os.makedirs(f'{path}/{model}', exist_ok=True)
        enabled = models_config[model]['enabled']
        if not enabled:
            return
        api_key = models_config[model]['api_key']
        if api_key is None:
            raise ValueError('API Key not found')
        base_url = models_config[model]['base_url']

        os.makedirs(f'{path}/{model}/level{level_tem}', exist_ok=True)

        def generate_and_save_code(i: int):
            """
            Generate and save the code.  
            """
            while True:
                cpp_code = get_code(desc, model, api_key, base_url)
                if len(cpp_code) >= 250:
                    break  
                
            with open(f'{path}/{model}/level{level_tem}/{model}_{i}.h', 'w', encoding='utf-8') as f:
                for chunk in [cpp_code[i:i + 1024] for i in range(0, len(cpp_code), 1024)]:
                    f.write(chunk)
            

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(generate_and_save_code, i) for i in range(1, generate_k + 1)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  
                except Exception as e:
                    print(f"An error occurred while generating code for model {model}, level {level_tem}: {e}")

    level_t = [0, 1, 2] if level is None else [int(level)]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for model in models:
            for level_tem in level_t:
                desc = problem.replace('@memory_limit', str(memory_limit[level_tem]))
                futures.append(executor.submit(save_code_for_model_and_level, model, level_tem, desc))
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == '__main__':
    print(f'Enabled models: {models_list}') 