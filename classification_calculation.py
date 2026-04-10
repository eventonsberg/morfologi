import streamlit as st
from itertools import combinations
from helpers import get_classification_by_rule_id
from uuid import uuid4

def get_existing_combination_class(classification_rule_ids):
    combination_classes = st.session_state.combination_classes
    for combination_class in combination_classes:
        if set(combination_class["classification_rule_ids"]) == set(classification_rule_ids):
            return combination_class
    return None

def get_combination_class_name(classification_rule_ids):
    existing_combination_class = get_existing_combination_class(classification_rule_ids)
    if existing_combination_class:
        return existing_combination_class["combination_class_name"]

    classification_by_rule_id = get_classification_by_rule_id(st.session_state.classification_rules)
    generic_combination_class_name = " + ".join(
        classification_by_rule_id[rule_id]
        for rule_id in classification_rule_ids
    )
    return generic_combination_class_name

def get_combination_class_id(classification_rule_ids):
    existing_combination_class = get_existing_combination_class(classification_rule_ids)
    if existing_combination_class:
        return existing_combination_class["combination_class_id"]
    return str(uuid4())

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
            combination_classes.append({
                "combination_class_id": get_combination_class_id(classification_rule_ids),
                "combination_class_name": get_combination_class_name(classification_rule_ids),
                "classification_rule_ids": classification_rule_ids,
            })
    return combination_classes

def display_combination_classifications():
    combination_classes = update_combination_classes()
    st.session_state.combination_classes = combination_classes

    for combination_class in combination_classes:
        input_key = f"combination_class_name_input_{combination_class['combination_class_id']}"
        st.session_state[input_key] = combination_class["combination_class_name"]
        st.text_input(
            "Kombinasjonsklasse",
            value=combination_class['combination_class_name'],
            label_visibility="collapsed",
            key=input_key,
            on_change=update_combination_class_name,
            args=(combination_class["combination_class_id"],),
        )
        st.caption(
            "Basert på følgende klassifiseringsregler: " +
            " + ".join(
                get_classification_by_rule_id(st.session_state.classification_rules)[rule_id]
                for rule_id in combination_class["classification_rule_ids"]
            )
        )
