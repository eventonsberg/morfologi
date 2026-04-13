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
                "combination_values": combination_values,
                "combination_class_ids": [],
            })
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

def remove_param_from_classification_rules(classification_rules, param_id):
    cleaned_rules = []
    for rule in classification_rules:
        combination_values = {
            existing_param_id: list(value_ids)
            for existing_param_id, value_ids in rule["combination_values"].items()
            if existing_param_id != param_id
        }

        if len(combination_values) >= 1:
            cleaned_rules.append({
                "classification_rule_id": rule["classification_rule_id"],
                "combination_values": combination_values,
                "classification_rule_name": rule.get("classification_rule_name", ""),
            })
    return cleaned_rules

def remove_value_from_classification_rules(classification_rules, param_id, value_id):
    cleaned_rules = []
    for rule in classification_rules:
        combination_values = {
            existing_param_id: list(value_ids)
            for existing_param_id, value_ids in rule["combination_values"].items()
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
        # Keep only meaningful classification rules
        if len(combination_values) >= 1:
            cleaned_rules.append({
                "classification_rule_id": rule["classification_rule_id"],
                "combination_values": combination_values,
                "classification_rule_name": rule.get("classification_rule_name", ""),
            })
    return cleaned_rules

def get_classification_rule_name_by_rule_id(classification_rules):
    return {rule["classification_rule_id"]: rule["classification_rule_name"] for rule in classification_rules}

def get_combination_values_by_classification_rule_id(classification_rules):
    return {rule["classification_rule_id"]: rule["combination_values"] for rule in classification_rules}

def get_combination_class_name_by_combination_class_id(combination_classes):
    return {combination_class["combination_class_id"]: combination_class["combination_class_name"] for combination_class in combination_classes}