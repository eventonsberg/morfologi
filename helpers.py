def get_param_name_by_id(params):
    return {param["param_id"]: param["param_name"] for param in params}

def get_value_name_by_id(params):
    return {
        value["value_id"]: value["value_name"]
        for param in params
        for value in param["values"]
    }

def compute_possible_combinations(params):
    if len(params) == 0:
        return 0
    n_combinations = 1
    for param in params:
        n_values = len(param["values"])
        if n_values == 0:
            return 0
        n_combinations *= n_values
    return n_combinations