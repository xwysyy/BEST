import os
import json
import csv
import pandas as pd

levels = 3
passk = 10
testcase = 3
model_results = {}
fieldnames = ['id', 'label', 'difficulty', 'k']
stdnames = ['id', 'label', 'difficulty', 'k', 'solution_id']


def create_zero_matrix(lim):
    return [[0.0 for _ in range(0, lim)] for _ in range(0, lim)]

def create_one_matrices(lim):
    return [[[1.0 for _ in range(lim)] for _ in range(lim)] for _ in range(passk + 1)]

def create_problem_dir(model, problem, cate, difficulty, std_sum = 0):
    global model_results
    if model not in model_results:
        model_results[model] = {}
    if problem not in model_results[model]:
        model_results[model][problem] = {}
    else:
        return 

    if model != "std":
        model_results[model][problem] = {
            "cate": cate,
            "difficulty": difficulty,
            "data": create_one_matrices(levels + 1),
            "ans": create_zero_matrix(levels)
        }
    else:
        if std_sum == 0:
            model_results[model][problem] = {
                "cate": cate,
                "difficulty": difficulty,
                "std": create_zero_matrix(levels)
            }
        else:
            model_results[model][problem] = {
                "cate": cate,
                "difficulty": difficulty,
            }
            for i in range(1, std_sum + 1):
                model_results[model][problem][f'std_{i}'] = create_zero_matrix(levels)

def csv_init():
    global fieldnames
    for i in range(1, levels + 1):
        for j in range(1, levels + 1):
            fieldnames.append(f"(time{i},space{j})")
    global stdnames
    for i in range(1, levels + 1):
        for j in range(1, levels + 1):
            stdnames.append(f"(time{i},space{j})")

def get_model_results(selected_models: str = None):

    global model_results

    data_dir = "data"
    root_dir = os.path.join(data_dir, "problems")
    result_dir = "process-data/dual_at_k"

    os.makedirs(result_dir, exist_ok=True)
    for problem_id in os.listdir(root_dir):
        problem_dir = os.path.join(root_dir, problem_id)
        code_dir = os.path.join(problem_dir, 'codes')
        problem_json = os.path.join(problem_dir, 'problem.json')
        with open(problem_json, 'r', encoding='utf-8') as p:
            problem_json_data = json.load(p)
        cate = problem_json_data['cate']
        difficulty = problem_json_data['difficulty']
        
        for model in os.listdir(code_dir):
            if selected_models and model != selected_models:
                continue
            
            model_dir = os.path.join(code_dir, model)
            for level_id in range(1,levels+1):
                level_dir = os.path.join(model_dir, f'level{level_id - 1}')
                result_pat = os.path.join(level_dir, 'result.json')
                
                try:
                    with open(result_pat, 'r', encoding='utf-8') as p:
                        result_json = json.load(p)
                except FileNotFoundError:
                    continue

                if model == 'std':
                    std_k_count = sum(1 for key in result_json.keys() if key.startswith('std_'))
                    create_problem_dir(model, problem_id, cate, difficulty, std_k_count)

                    for std_id in result_json:
                        ac_tot = [1]*(levels + 1)
                        now_std = result_json[std_id]
                        for case in now_std:
                            tim_level = int((int(case['case']) - 1) / 3 )
                            if case['result'] != "Accepted":
                                ac_tot[tim_level + 1] = 0
                        for i in range(1,levels + 1):
                            model_results[model][problem_id][std_id][i-1][level_id-1] += ac_tot[i]
                    continue
                
                create_problem_dir(model, problem_id, cate, difficulty)

                for pass_id in range(1,passk+1):
                    try:
                        now_res = result_json[f'{model}_{pass_id}']
                    except KeyError:
                        print(f"KeyError: {model}_{pass_id}{problem_id}")
                        continue
                    ac_tot = [1]*(levels + 1)
                    case_id = 0
                    for case in now_res:
                        case_id += 1
                        tim_level = int((case_id - 1) / 3 )
                        if case['result'] != "Accepted":
                            ac_tot[tim_level + 1] = 0
                    for i in range(1,levels + 1):
                        model_results[model][problem_id]['data'][pass_id][i][level_id] = ac_tot[i]

    for model in model_results:
        if model == 'std':
            continue
        for problem in model_results[model]:
            for k in range(1,passk + 1):
                for i in range(1,levels + 1):
                    for j in range(1,levels + 1):
                        if i != 1:
                            model_results[model][problem]['data'][k][i][j] = min(
                                model_results[model][problem]['data'][k][i][j],
                                model_results[model][problem]['data'][k][i - 1][j]
                            )
                        if j != 1:
                            model_results[model][problem]['data'][k][i][j] = min(
                                model_results[model][problem]['data'][k][i][j],
                                model_results[model][problem]['data'][k][i][j - 1]
                            )
                        model_results[model][problem]['ans'][i - 1][j - 1] +=\
                            model_results[model][problem]['data'][k][i][j]

    for model in model_results:
        for problem in model_results[model]:
            for i in range(1,levels + 1):
                for j in range(1,levels + 1):
                    if model != "std":
                        model_results[model][problem]['ans'][i - 1][j - 1] /= 1.0 * passk
                        
def insert_data(rows, problem, cate, difficulty, data):
    row = {}
    row['id'] = problem
    row['label'] = cate
    row['difficulty'] = difficulty
    row['k'] = passk
    for i in range(len(data)):
        row[fieldnames[i + 4]] = data[i]
    rows.append(row)

def insert_std_data(rows, problem, cate, difficulty, data ,solution_id):
    row = {}
    row['id'] = problem
    row['label'] = cate
    row['difficulty'] = difficulty
    row['k'] = passk
    row['solution_id'] = solution_id

    for i in range(len(data)):
        row[stdnames[i + 5]] = data[i]
    rows.append(row)

def flatten(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list


def csv_output():
    global model_results
    result_dir = "process-data/dual_at_k"
    for model in model_results:
        rows = []
        for problem in model_results[model]:
            cate = model_results[model][problem]['cate']
            difficulty = model_results[model][problem]['difficulty']
            if model == 'std':
                data =  model_results[model][problem]
                for sol_id in data:
                    if not sol_id.startswith("std"):
                        continue
                    mat = data[sol_id]
                    insert_std_data(rows, problem, cate, difficulty, flatten(mat),sol_id)
            else:
                data = model_results[model][problem]['ans']
                insert_data(rows, problem, cate, difficulty, flatten(data))
        csv_pat = os.path.join(result_dir, f'{model}.csv')
        cloumn = fieldnames
        if model == 'std':
            cloumn = stdnames
        with open(csv_pat, 'w', newline='', encoding='utf-8-sig') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=cloumn)
            writer.writeheader()
            writer.writerows(rows)

def evaluate_models(selected_models: str = None):

    csv_init()
    get_model_results(selected_models)
    csv_output()

if __name__ == "__main__":

    model_list = "std"
    evaluate_models(model_list)