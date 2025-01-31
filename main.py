from ask import ask, models_list
from run import run, run_all
from init import problem_path, template_path, data_path
import os
import shutil
import pandas as pd
import chardet
import json
import ast
from concurrent.futures import ThreadPoolExecutor

with open(data_path + '/data.csv', 'rb') as f:
    encoding = chardet.detect(f.read())['encoding']

def check_result_files(base_path: str, problem_id: str):
    """
    Check whether the `result.json` file exists in each subfolder of the path corresponding to `problem_id`.

    :param base_path: Root directory (e.g., "problems/")
    :param problem_id: Problem ID (e.g., "1234")
    :return: Returns True if any `result.json` file is missing, otherwise returns False.
    """
    no_result = False
    target_path = os.path.join(base_path, problem_id, "codes")
    
    if not os.path.exists(target_path):
        print(f"Path does not exist: {target_path}")
        return True  # Return True immediately if the path does not exist  

    for subfolder in os.listdir(target_path):
        subfolder_path = os.path.join(target_path, subfolder)
        if os.path.isdir(subfolder_path):  # Ensure it is a directory  
            for level in os.listdir(subfolder_path):
                level_path = os.path.join(subfolder_path, level)
                if os.path.isdir(level_path) and level.startswith("level"):
                    result_file = os.path.join(level_path, "result.json")
                    if not os.path.exists(result_file):
                        print(f"Missing file: {result_file}")
                        no_result = True
                        break
            if no_result:
                break
    return no_result

def process_row(row: dict):
    """
    Function to process a single row of data.  
    Check whether the problem configuration has been modified or newly created.  
    Responsible for creating and generating each problem.  
    `row` is a dictionary.  
    """
    os.makedirs(problem_path, exist_ok=True)
    
    id = str(row['id'])
    desc = row['desc']
    data = ast.literal_eval(row['data'])
    time_limit = int(row['time_limit'])
    memory_limit = ast.literal_eval(row['memory_limit'])
    std = row['std']
    test_cpp = row['test']
    cate = row['cate']
    difficulty = row['difficulty']
    if not all([desc]):
        raise Exception(f'Problem {id} not complete')
    if not all([desc, data, time_limit, memory_limit, std, test_cpp, cate, difficulty]):
        raise Exception(f'Problem {id} not complete')
    std = f'#ifndef STD_H\n#define STD_H\n#include <bits/stdc++.h>\nusing namespace std;\n\n{std}\n\n#endif'

    # Determine whether the problem configuration has been modified or newly created  
    flag = False
    # Check whether the test data has been modified  
    flag1 = False

    path = f'{problem_path}/{id}'
    if not os.path.exists(path):
        flag = True
        os.makedirs(f'{path}/exec', exist_ok=True)
        os.makedirs(f'{path}/desc', exist_ok=True)
        os.makedirs(f'{path}/codes', exist_ok=True)
        os.makedirs(f'{path}/cases', exist_ok=True)
        shutil.copyfile(f'{template_path}/execute.h', f'{path}/exec/execute.h')

    def operate_file(file_path: str, cur_content: str):
        full_path = f'{path}/{file_path}'
        nonlocal flag
        try:
            with open(full_path, 'r+', encoding='utf-8') as f:
                pre_content = f.read()
                if pre_content != cur_content:
                    f.seek(0)
                    f.write(cur_content)
                    f.truncate()
                    if file_path != 'desc/desc.md':
                        nonlocal flag1
                        flag1 = True
                    else:
                        flag = True
        except FileNotFoundError:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(cur_content)
            flag = True 

    os.makedirs(f'{path}/codes/std', exist_ok=True)
    for level in range(3):
        os.makedirs(f'{path}/codes/std/level{level}', exist_ok=True)
        if f'solve1' in std:
            std1 = std.replace('solve1', f'solve')
            std2 = std.replace('solve2', f'solve')
            operate_file(f'codes/std/level{level}/std_1.h', std1)
            operate_file(f'codes/std/level{level}/std_2.h', std2)
            if f'solve3' in std:
                std3 = std.replace('solve3', f'solve')
                operate_file(f'codes/std/level{level}/std_3.h', std3)
        else:
            operate_file(f'codes/std/level{level}/std.h', std)

    operate_file('exec/test.cpp', test_cpp)
    operate_file('desc/desc.md', desc)

    def operate_json(file_path: str, new_content: dict):
        full_path = f'{path}/{file_path}'
        nonlocal flag
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                pre_content = json.load(f)
            if pre_content != new_content:
                flag = True
                with open(full_path, 'w', encoding='utf-8') as f:
                    json.dump(new_content, f, ensure_ascii=False, indent=4)
        except:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(new_content, f, ensure_ascii=False, indent=4)
            flag = True

    problem_json_file = {}
    problem_json_file['time_limit'] = (time_limit)
    problem_json_file['memory_limit'] = memory_limit
    problem_json_file['data'] = data
    problem_json_file['cate'] = cate
    problem_json_file['difficulty'] = difficulty
    operate_json('problem.json', problem_json_file)

    test_case_path = f'{data_path}/test_cases/{id}'
    if not os.path.exists(test_case_path):
        raise Exception(f'Test cases for problem {id} not found')
    def compare_dir(dir1: str, dir2: str):
        nonlocal flag1
        if len(os.listdir(dir1)) != len(os.listdir(dir2)):
            flag1 = True
            return
        for file in os.listdir(dir1):
            file1 = f'{dir1}/{file}'
            file2 = f'{dir2}/{file}'
            try:
                with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                    if f1.read() != f2.read():
                        flag1 = True
                        return
            except FileNotFoundError:
                flag1 = True
                return
    compare_dir(test_case_path, f'{path}/cases')
    if flag is True:
        print(f'{id} changed')
        shutil.rmtree(f'{path}/cases')
        shutil.copytree(test_case_path, f'{path}/cases')
        ask(id)
        run_all(id)
    elif flag1 is True:
        print(f'{id} test changed')
        shutil.rmtree(f'{path}/cases')
        shutil.copytree(test_case_path, f'{path}/cases')
        run_all(id)
    else:
        tem_model_list = [model for model in models_list if not os.path.exists(f'{path}/codes/{model}')]
        tem_model_list = [x for x in tem_model_list if x != 'std']
        no_result = check_result_files('data/problems',id)             
        if tem_model_list or no_result:
            print(f'{id} models changed')
            if tem_model_list:
                ask(id, tem_model_list)
                run_all(id, tem_model_list)
            elif no_result:
                run_all(id, models_list)
        else:
            print(f'{id} not changed')


def create_problem(name: int = None, op: bool = False):
    """
    Read data and process each row with or without concurrency.  
    `name`: Whether a specific problem name is specified.  
    `op`: Whether to process concurrently.  
    """
    df = pd.read_csv(f'{data_path}/data.csv', encoding=encoding)

    if name:
        df = df[df['id'] == name]
        if df.empty:
            raise Exception(f'Problem {name} not found')
        process_row(df.to_dict(orient='records')[0])
        return

    if op is True:
        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(process_row, df.to_dict(orient='records'))
    else:
        for _, row in df.iterrows():
            process_row(row)

if __name__ == '__main__':
    print(f'Enabled models: {models_list}')
    create_problem()
