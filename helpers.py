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
    combination_number = 1
    for combination in product(*values_by_param):
        combination_values = {
            param["param_id"]: value["value_id"]
            for param, value in zip(params, combination)
        }
        if not any(
            all(
                combination_values.get(param_id) in value_ids
                for param_id, value_ids in inconsistent_combination["combination_values"].items()
            )
            for inconsistent_combination in inconsistent_combinations
        ):
            possible_combinations.append({
                "combination_number": combination_number,
                "combination_values": combination_values,
                "combination_class_names": [],
            })
            combination_number += 1
    return possible_combinations

def remove_param_from_inconsistent_combinations(inconsistent_combinations, param_id):
    cleaned_combinations = []
    for combination in inconsistent_combinations:
        combination_values = {
            existing_param_id: list(value_ids)
            for existing_param_id, value_ids in combination["combination_values"].items()
            if existing_param_id != param_id
        }
        if len(combination_values) >= 2:
            cleaned_combinations.append({
                "combination_id": combination["combination_id"],
                "combination_values": combination_values,
                "comment": combination.get("comment", ""),
            })
    return cleaned_combinations

def remove_value_from_inconsistent_combinations(inconsistent_combinations, param_id, value_id):
    cleaned_combinations = []
    for combination in inconsistent_combinations:
        combination_values = {
            existing_param_id: list(value_ids)
            for existing_param_id, value_ids in combination["combination_values"].items()
        }
        if param_id in combination_values:
            remaining_value_ids = [
                existing_value_id
                for existing_value_id in combination_values[param_id]
                if existing_value_id != value_id
            ]
            if remaining_value_ids:
                combination_values[param_id] = remaining_value_ids
            else:
                combination_values.pop(param_id)
        # Keep only meaningful inconsistent combinations
        if len(combination_values) >= 2:
            cleaned_combinations.append({
                "combination_id": combination["combination_id"],
                "combination_values": combination_values,
                "comment": combination.get("comment", ""),
            })
    return cleaned_combinations

def update_possible_combinations_with_combination_class_names(possible_combinations, concepts, selected_concept_intents):
    selected_concepts = [
        concepts[concept_intent_tuple]
        for concept_intent_tuple in selected_concept_intents
        if concept_intent_tuple in concepts
    ]

    for combination in possible_combinations:
        combination_key = frozenset(combination["combination_values"].items())
        combination["combination_class_names"] = [
            concept_info["name"]
            for concept_info in selected_concepts
            if combination_key in concept_info.get("extent", set())
        ]