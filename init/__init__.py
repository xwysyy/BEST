import os

current_file_path = os.path.abspath(os.path.dirname(__file__))
parent_path = os.path.abspath(os.path.dirname(current_file_path))

model_path = current_file_path + '/models.yaml'

problem_path = parent_path + '/data/problems'

data_path = parent_path + '/data'

template_path = current_file_path + '/template'

generate_k = 10