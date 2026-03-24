from itertools import product

def get_param_name_by_id(params):
    return {param["param_id"]: param["param_name"] for param in params}

def get_value_name_by_id(params):
    return {
        value["value_id"]: value["value_name"]
        for param in params
        for value in param["values"]
    }

def get_possible_combinations(params, inconsistent_combinations=None):
    if len(params) < 2:
        return []
    values_by_param = [param["values"] for param in params]
    if any(len(values) == 0 for values in values_by_param):
        return []
    inconsistent_combinations = inconsistent_combinations or []
    possible_combinations = []
    for combination in product(*values_by_param):
        combination_dict = {
            param["param_id"]: value["value_id"]
            for param, value in zip(params, combination)
        }
        if not any(
            all(
                combination_dict.get(param_id) in value_ids
                for param_id, value_ids in inconsistent_combination["combination_values"].items()
            )
            for inconsistent_combination in inconsistent_combinations
        ):
            possible_combinations.append(combination_dict)
    return possible_combinations
