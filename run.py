import subprocess
import concurrent.futures
import os
import json
import re
import threading
import shutil
from init import problem_path
from ask import models_list

lock = threading.Lock()

def run(id: str, model: str, level:str, k:str):
    """
    Evaluate the specified large model's code for a given problem.  
    `id` is the problem ID, `model` is the model to be tested, `level` is the space constraint level,  
    and `k` is the k-th time the large model's generated code is queried.  
    """
    path = f'{problem_path}/{id}'
    with open(f'{path}/problem.json', 'r') as f:
        tem_problem_json = json.load(f)
        time_limit = (int)(tem_problem_json['time_limit'])
        memory_limit = tem_problem_json['memory_limit']
        if len(memory_limit) == 1:
            tem_limit = memory_limit[0][int(level)]
            memory_limit = [max(64, tem_limit // 8 ** _) for _ in range(2, -1, -1)]
        else:
            memory_limit = [item[(int)(level)] for item in memory_limit]
    test_case_num = 9

    code = f'{model}_{k}' if f'{model}_{k}.h' != 'std_0.h' else 'std'
    path_code = f'{path}/codes/{model}/level{level}'
    path_exec = f'{path}/exec'
    shutil.copyfile(f'{path_exec}/test.cpp',f'{path_code}/test_{code}.cpp')
    with open(f'{path_code}/test_{code}.cpp', 'r+') as f:
        test_cpp = f.read()
        test_cpp = test_cpp.replace('#include "std.h"', f'#include "{code}.h"\n#include "../../../exec/execute.h"')
        index = test_cpp.find('Solution solution;')
        test_cpp = test_cpp[:index] + f'\nget_usage("{path_code}/test_{code}");\n' + test_cpp[index:]
        index = test_cpp.find('solution.solve')
        index = test_cpp[index:].find(');\n') + index + 3
        test_cpp = test_cpp[:index] + f'\nget_usage("{path_code}/test_{code}");\n' + test_cpp[index:]
        f.seek(0)
        f.truncate()
        f.write(test_cpp)
        
    sign = os.system(f'g++ {path_code}/test_{code}.cpp -o {path_code}/test_{code}')
    res_data = []
    if sign != 0:
        sign = os.system(f'g++ {path_code}/test_{code}.cpp -o {path_code}/test_{code}')
        if sign != 0:
            for i in range(1, test_case_num + 1):
                res_data.append({
                    'case': f'{i}',
                    'result': 'Compile Error',
                    'time_used': 0,
                    'memory_used': 0
                })
    if sign == 0:
        for i in range(1, test_case_num + 1):
            shell = f'{path_code}/test_{code} {i} < {path}/cases/{i}.in > {path_code}/test_{code}{i}.out'
            shell_res = subprocess.run(shell, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stderr = shell_res.stderr
            if "CPU time limit exceeded" in stderr:
                res_data.append({
                    'case': f'{i}',
                    'result': 'Time Limit Exceeded',
                    'time_used': 2000,
                    'memory_used': 0
                })
                continue
            shell = f'diff {path_code}/test_{code}{i}.out {path}/cases/{i}.out > /dev/null 2>&1'
            sign = os.system(shell)
            if sign != 0:
                res_data.append({
                    'case': f'{i}',
                    'result': 'Wrong Answer',
                    'time_used': 0,
                    'memory_used': 0
                })
                os.system(f'rm -f {path_code}/test_{code}_result.txt')
            else:
                with lock:
                    with open(f'{path_code}/test_{code}_result.txt', 'r+') as f:
                        time_before = f.readline()
                        memory_before = f.readline()
                        time_after = f.readline()
                        memory_after = f.readline()
                        if time_before == '' or memory_before == '' or time_after == '' or memory_after == '':
                            time_before = 0
                            memory_before = 0
                            time_after = 0
                            memory_after = memory_limit[(i - 1) // 3] + 1
                        else:
                            time_before = int(time_before)
                            time_after = int(time_after)
                            memory_before = float(memory_before)
                            memory_after = float(memory_after)
                        time_used = time_after - time_before
                        memory_used = memory_after - memory_before
                        f.seek(0)
                        f.truncate()

                tem_result = 'Accepted'
                if time_used > time_limit:
                    tem_result = 'Time Limit Exceeded'
                if memory_used > memory_limit[(i - 1) // 3]:
                    if tem_result == 'Accepted':
                        tem_result = 'Memory Limit Exceeded'
                    else:
                        tem_result = 'Time Limit Exceeded / Memory Limit Exceeded'
                res_data.append({
                    'case': f'{i}',
                    'result': tem_result,
                    'time_used': time_used,
                    'memory_used': memory_used
                })
    os.system(f'rm -f {path_code}/test_{code}*')

    with lock:
        result_file = f'{path_code}/result.json'
        try:
            with open(result_file, 'r') as f:
                file_data = json.load(f)
        except:
            file_data = {}

        file_data[code] = res_data

        with open(result_file, 'w') as f:
            json.dump(file_data, f, indent=4)

def run_model(id: str, model: str, level: str = None, op: bool = True, max_workers: int = 3):
    """
    Evaluate the specified large model's code for a given problem.  
    `id` is the problem name, `model` is the model to be tested, `level` is the space constraint level.  
    If `level` is None, all levels will be tested.  
    `op`: Whether to use multithreading.  
    """
    def process_files(files, level):
        if op:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                batch_size = max_workers
                for i in range(0, len(files), batch_size):
                    batch = files[i:i + batch_size]
                    futures = []
                    for file in batch:
                        if file == 'std.h':
                            print(f'Running {id} std level{level}')
                            futures.append(executor.submit(run, id, model, level, '0'))
                            continue
                        match = re.search(r'.+_(\d+)\.h', file)
                        if match:
                            k = match.group(1)
                            print(f'Running {id} {model} level{level} {k}')
                            futures.append(executor.submit(run, id, model, level, k))
                    for future in concurrent.futures.as_completed(futures):
                        future.result() 
        else:
            for file in files:
                if file == 'std.h':
                    print(f'Running {id} std level{level}')
                    run(id, model, level, '0')
                    continue
                match = re.search(r'.+_(\d+)\.h', file)
                if match:
                    k = match.group(1)
                    print(f'Running {id} {model} level{level} {k}')
                    run(id, model, level, k)

    if level is None:
        for i in range(0, 3):
            path = f'{problem_path}/{id}/codes/{model}/level{i}'
            if not os.path.exists(path):
                print(f'{id} {model} level{i} not exist')
                continue
            files = os.listdir(path)
            process_files(files, i)
    else:
        path = f'{problem_path}/{id}/codes/{model}/level{level}'
        if not os.path.exists(path):
            return
        files = os.listdir(path)
        process_files(files, level)

def run_all(id: str, models: list=None, is_run_std: bool=True, op: bool=False):
    """
    Evaluate all large models' code for a given problem.  
    `id` is the problem name, `models` are the models to be tested,  
    `is_run_std` determines whether to test the standard model (default is True).  
    `op`: Whether to use multithreading.  
    """
    if models is None:
        models = models_list.copy() 
    if is_run_std:
        if 'std' not in models:
            models.insert(0, 'std')
    if op:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for model in models:
                print(f'Running {id} {model}')
                futures.append(executor.submit(run_model, id, model, None, op))
            concurrent.futures.wait(futures)
    else:
        for model in models:
            print(f'Running {id} {model}')
            run_model(id, model, None, op)


if __name__ == '__main__':
    pass