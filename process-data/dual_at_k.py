import pandas as pd
import chardet
import os
os.makedirs('dual_at_k', exist_ok=True)

# Calculate the coefficient matrix  
coef_time = []
for i in range(3):
    row_list = []
    for j in range(3):
        if j == 0:
            row_list.append(1.2 ** i)
        else:
            row_list.append(0)
    coef_time.append(row_list)

coef_space = []
for i in range(3):
    row_list = []
    for j in range(3):
        if i == 0:
            row_list.append(1.2 ** j)
        else:
            row_list.append(0)
    coef_space.append(row_list)

coef_comb = []
for i in range(3):
    row_list = []
    for j in range(3):
        row_list.append((1.2 ** i) * (1.2 ** j))
    coef_comb.append(row_list)

# Read `std.csv` to get the number of submatrices passed by std  
if not os.path.exists('dual_at_k/std.csv'):
    raise FileNotFoundError('dual_at_k/std.csv not exists, please export std.csv')
std_csv = pd.read_csv('dual_at_k/std.csv')
std_csv = std_csv.fillna('')
std_csv = std_csv.to_dict(orient='records')
std_pass = {}
problem_difficulty = {}
if not os.path.exists('../data/data.csv'):
    raise FileNotFoundError('data/data.csv not exists')
data_csv = pd.read_csv('../data/data.csv')
data_csv = data_csv.fillna('')
data_csv = data_csv.to_dict(orient='records')
for row in data_csv:
    problem_id = str(row['id'])
    problem_difficulty[problem_id] = row['difficulty']

for row in std_csv:
    problem_id = str(row['id'])
    if std_pass.get(problem_id) is None:
        std_pass[problem_id] = 0
    for i in range(1, 4):
        for j in range(1, 4):
            key = f'(time{i},space{j})'
            if row[key] == 1:
                std_pass[problem_id] |= 1 << ((i - 1) * 3 + j - 1)

def process_row(row: dict):
    problem_id = str(row['id'])
    problem_pass1 = row['(time1,space1)']
    problem_pass10 = 1 - (1 - problem_pass1) ** 10

    # Generate sub-task pass1 matrix  
    pass1 = []
    for i in range(1, 4): 
        row_list = []
        for j in range(1, 4): 
            key = f'(time{i},space{j})'
            row_list.append(row[key])
        pass1.append(row_list)

    # Generate sub-task pass10 matrix  
    pass10 = []
    for i in range(1, 4): 
        row_list = []
        for j in range(1, 4): 
            key = f'(time{i},space{j})'
            row_list.append(1 - (1 - row[key]) ** 10)
        pass10.append(row_list)

    dual1_time, dual10_time = 0, 0
    dual1_space, dual10_space = 0, 0
    dual1_comb, dual10_comb = 0, 0
    std_pass_count_time, std_pass_count_space, std_pass_count_comb = 0, 0, 0

    for i in range(3):
        for j in range(3):
            dual1_time += pass1[i][j] * coef_time[i][j]
            dual10_time += pass10[i][j] * coef_time[i][j]
            dual1_space += pass1[i][j] * coef_space[i][j]
            dual10_space += pass10[i][j] * coef_space[i][j]
            dual1_comb += pass1[i][j] * coef_comb[i][j]
            dual10_comb += pass10[i][j] * coef_comb[i][j]
            if std_pass[problem_id] & (1 << (i * 3 + j)):
                std_pass_count_time += coef_time[i][j]
                std_pass_count_space += coef_space[i][j]
                std_pass_count_comb += coef_comb[i][j]

    dual1_time = dual1_time / std_pass_count_time
    dual10_time = dual10_time / std_pass_count_time
    dual1_space = dual1_space / std_pass_count_space
    dual10_space = dual10_space / std_pass_count_space
    dual1_comb = dual1_comb / std_pass_count_comb
    dual10_comb = dual10_comb / std_pass_count_comb

    row['problem_pass10'] = problem_pass10
    row['dual1_time'] = dual1_time
    row['dual10_time'] = dual10_time
    row['dual1_space'] = dual1_space
    row['dual10_space'] = dual10_space
    row['dual1_comb'] = dual1_comb
    row['dual10_comb'] = dual10_comb

    return row

    

def process_csv(model: str):
    """
    Process the specified problem CSV file  
    """
    path = f'dual_at_k/{model}.csv'
    if not os.path.exists(path):
        raise FileNotFoundError(f'{model}.csv not exists')
    data = pd.read_csv(path)
    data = data.fillna('')
    data = data.to_dict(orient='records')

    processed_data = []
    for row in data:
        res = process_row(row)
        processed_data.append(res)

    processed_df = pd.DataFrame(processed_data)

    output_path = path.replace('.csv', '_processed.csv')
    processed_df.to_csv(output_path, index=False)

def result_csv(model: str, target: str='dual_at_k_result.csv'):
    """
    Summarize the results  
    """
    if not os.path.exists(f'dual_at_k/{model}_processed.csv'):
        raise FileNotFoundError('The processed file does not exist.')

    data = pd.read_csv(f'dual_at_k/{model}_processed.csv')
    data = data.fillna('')
    data = data.to_dict(orient='records')

    # Calculate the average values of pass1 and pass10 for this model  
    dual1_time, dual10_time = 0, 0
    dual1_space, dual10_space = 0, 0
    dual1_comb, dual10_comb = 0, 0
    dual1_comb_easy, dual10_comb_easy = 0, 0
    dual1_comb_medium, dual10_comb_medium = 0, 0
    dual1_comb_hard, dual10_comb_hard = 0, 0
    easy_count, medium_count, hard_count = 0, 0, 0
    pass10 = 0
    for row in data:
        pass10 += row['problem_pass10']
        dual1_time += row['dual1_time']
        dual10_time += row['dual10_time']
        dual1_space += row['dual1_space']
        dual10_space += row['dual10_space']
        dual1_comb += row['dual1_comb']
        dual10_comb += row['dual10_comb']
        if problem_difficulty[str(row['id'])] == 'easy':
            dual1_comb_easy += row['dual1_comb']
            dual10_comb_easy += row['dual10_comb']
            easy_count += 1
        elif problem_difficulty[str(row['id'])] == 'medium':
            dual1_comb_medium += row['dual1_comb']
            dual10_comb_medium += row['dual10_comb']
            medium_count += 1
        elif problem_difficulty[str(row['id'])] == 'hard':
            dual1_comb_hard += row['dual1_comb']
            dual10_comb_hard += row['dual10_comb']
            hard_count += 1


    dual1_time = dual1_time / len(data)
    dual10_time = dual10_time / len(data)
    dual1_space = dual1_space / len(data)
    dual10_space = dual10_space / len(data)
    dual1_comb = dual1_comb / len(data)
    dual10_comb = dual10_comb / len(data)
    if easy_count != 0:
        dual1_comb_easy = dual1_comb_easy / easy_count
        dual10_comb_easy = dual10_comb_easy / easy_count
    if medium_count != 0:
        dual1_comb_medium = dual1_comb_medium / medium_count
        dual10_comb_medium = dual10_comb_medium / medium_count
    if hard_count != 0:
        dual1_comb_hard = dual1_comb_hard / hard_count
        dual10_comb_hard = dual10_comb_hard / hard_count
    pass10 = pass10 / len(data)


    dual1_time = f"{dual1_time:.3f}"
    dual10_time = f"{dual10_time:.3f}"
    dual1_space = f"{dual1_space:.3f}"
    dual10_space = f"{dual10_space:.3f}"
    dual1_comb = f"{dual1_comb:.3f}"
    dual10_comb = f"{dual10_comb:.3f}"
    dual1_comb_easy = f"{dual1_comb_easy:.3f}"
    dual10_comb_easy = f"{dual10_comb_easy:.3f}"
    dual1_comb_medium = f"{dual1_comb_medium:.3f}"
    dual10_comb_medium = f"{dual10_comb_medium:.3f}"
    dual1_comb_hard = f"{dual1_comb_hard:.3f}"
    dual10_comb_hard = f"{dual10_comb_hard:.3f}"
    pass10 = f"{pass10:.3f}"

    if not os.path.exists(target):
        with open(target, 'w') as f:
            f.write('model,dual1_time,dual10_time,dual1_space,dual10_space,dual1_comb_easy,dual10_comb_easy,dual1_comb_medium,dual10_comb_medium,dual1_comb_hard,dual10_comb_hard,dual1_comb,dual10_comb,pass10\n')
    with open(target, 'r+') as f:
        lines = f.readlines()
        found = False 
        for i, line in enumerate(lines):
            if line.startswith(model):
                lines[i] = f'{model},{dual1_time},{dual10_time},{dual1_space},{dual10_space},{dual1_comb_easy},{dual10_comb_easy},{dual1_comb_medium},{dual10_comb_medium},{dual1_comb_hard},{dual10_comb_hard},{dual1_comb},{dual10_comb},{pass10}\n'
                found = True
                break
        if not found:
            lines.append(f'{model},{dual1_time},{dual10_time},{dual1_space},{dual10_space},{dual1_comb_easy},{dual10_comb_easy},{dual1_comb_medium},{dual10_comb_medium},{dual1_comb_hard},{dual10_comb_hard},{dual1_comb},{dual10_comb},{pass10}\n')
        f.seek(0)  
        f.writelines(lines) 
        f.truncate()
        res = f'{model}&{dual1_time}&{dual10_time}&{dual1_space}&{dual10_space}&{dual1_comb_easy}&{dual10_comb_easy}&{dual1_comb_medium}&{dual10_comb_medium}&{dual1_comb_hard}&{dual10_comb_hard}&{dual1_comb}&{dual10_comb}&{pass10}\\\\'
        print(res)

def work():
    models = os.listdir('dual_at_k')
    for model in models:
        if 'process' in model:
            continue
        if not model.endswith('.csv'):
            continue
        model = model.replace('.csv', '')
        process_csv(model)
        result_csv(model)



if __name__ == '__main__':
    work()