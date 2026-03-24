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