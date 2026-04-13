import streamlit as st
from itertools import combinations
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
    get_classification_by_rule_id,
    get_combination_values_by_classification_rule_id
)
from uuid import uuid4
import pandas as pd

def get_combination_class_id_and_name(classification_rule_ids):
    combination_classes = st.session_state.combination_classes
    for combination_class in combination_classes:
        if set(combination_class["classification_rule_ids"]) == set(classification_rule_ids):
            return combination_class["combination_class_id"], combination_class["combination_class_name"]
    new_class_id = str(uuid4())
    classification_by_rule_id = get_classification_by_rule_id(st.session_state.classification_rules)
    generic_class_name = " + ".join(
        classification_by_rule_id[rule_id]
        for rule_id in classification_rule_ids
    )
    return new_class_id, generic_class_name

def update_combination_class_name(combination_class_id):
    input_key = f"combination_class_name_input_{combination_class_id}"
    for combination_class in st.session_state.combination_classes:
        if combination_class["combination_class_id"] == combination_class_id:
            combination_class["combination_class_name"] = st.session_state[input_key]
            break

def update_combination_classes():
    classification_rules = st.session_state.classification_rules
    combination_classes = []
    for n_rules in range(1, len(classification_rules) + 1):
        for classification_rule_combination in combinations(classification_rules, n_rules):
            classification_rule_ids = [rule["classification_rule_id"] for rule in classification_rule_combination]
            combination_class_id, combination_class_name = get_combination_class_id_and_name(classification_rule_ids)
            combination_classes.append({
                "combination_class_id": combination_class_id,
                "combination_class_name": combination_class_name,
                "classification_rule_ids": classification_rule_ids,
            })
    return combination_classes

def display_combination_classes():
    combination_classes = update_combination_classes()
    st.session_state.combination_classes = combination_classes
    possible_combinations = st.session_state.possible_combinations
    unclassified_combinations = possible_combinations.copy()
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    param_columns = [param["param_name"] for param in st.session_state.params]
    combination_values_by_rule_id = get_combination_values_by_classification_rule_id(st.session_state.classification_rules)

    for class_idx, combination_class in enumerate(combination_classes):
        classification_rule_ids = combination_class["classification_rule_ids"]
        possible_combinations_in_class = []
        for possible_combination in possible_combinations:
            matches_all_rules = True
            for rule_id in classification_rule_ids:
                combination_values = combination_values_by_rule_id[rule_id]
                for param, values in combination_values.items():
                    if possible_combination[param] not in values:
                        matches_all_rules = False
                        break
                if not matches_all_rules:
                    break
            if matches_all_rules:
                possible_combinations_in_class.append({
                    param_name_by_id[param_id]: value_name_by_id[value_id]
                    for param_id, value_id in possible_combination.items()
                })
                if possible_combination in unclassified_combinations:
                    unclassified_combinations.remove(possible_combination)
        combination_class_df = pd.DataFrame(possible_combinations_in_class, columns=param_columns)
        number_of_combinations = len(possible_combinations_in_class)
        
        if number_of_combinations > 0:
            st.subheader(f"Klasse {class_idx + 1}")
            col1, col2 = st.columns([5, 1], vertical_alignment="center")
            input_key = f"combination_class_name_input_{combination_class['combination_class_id']}"
            if input_key not in st.session_state:
                st.session_state[input_key] = combination_class["combination_class_name"]
            col1.text_input(
                "Kombinasjonsklasse",
                label_visibility="collapsed",
                key=input_key,
                on_change=update_combination_class_name,
                args=(combination_class["combination_class_id"],),
            )
            col2.markdown(f":blue[**{number_of_combinations} kombinasjon{'er' if number_of_combinations != 1 else ''}**]")
            
            st.dataframe(combination_class_df)
            st.caption(
                "Basert på følgende klassifiseringsregler: " +
                " + ".join(
                    get_classification_by_rule_id(st.session_state.classification_rules)[rule_id]
                    for rule_id in classification_rule_ids
                )
            )
    if unclassified_combinations:
        st.subheader("Uklassifiserte kombinasjoner")
        unclassified_combinations_data = [
            {
                param_name_by_id[param_id]: value_name_by_id[value_id]
                for param_id, value_id in possible_combination.items()
            }
            for possible_combination in unclassified_combinations
        ]
        unclassified_combinations_df = pd.DataFrame(unclassified_combinations_data, columns=param_columns)
        number_of_unclassified = len(unclassified_combinations)
        st.markdown(f":blue[**{number_of_unclassified} kombinasjon{'er' if number_of_unclassified != 1 else ''}**] er ikke klassifisert av noen regel.")
        st.dataframe(unclassified_combinations_df)

        