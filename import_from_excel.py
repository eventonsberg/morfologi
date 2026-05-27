import streamlit as st
import pandas as pd
from uuid import uuid4
from collections import defaultdict


def normalize_intent_tuple(intent_tuple):
    return tuple(sorted(intent_tuple))


def parse_attributes_to_intent(attributes_str, param_name_to_id, value_name_to_id_by_param):
    if pd.isna(attributes_str):
        attributes_str = ""
    intent_tuple = tuple()
    for attr in str(attributes_str).split(";"):
        parts = attr.split(" = ")
        if len(parts) != 2:
            continue
        param_name, value_name = parts
        param_id = param_name_to_id.get(param_name.strip())
        if not param_id:
            continue
        value_id = value_name_to_id_by_param[param_id].get(value_name.strip())
        if not value_id:
            continue
        intent_tuple += (f"{param_id} = {value_id}",)
    return normalize_intent_tuple(intent_tuple)


def parse_class_names(classification_cell_value):
    if pd.isna(classification_cell_value):
        return []
    return [
        class_name.strip()
        for class_name in str(classification_cell_value).split(";")
        if class_name.strip()
    ]

def transform_excel_data_to_session_state(
    params_and_values_df,
    descriptions_df,
    inconsistent_combinations_df,
    concepts_df,
    classification_params_df,
    classification_settings_df,
    listed_concepts_df,
    possible_combinations_df,
):
    param_descriptions = {}
    value_descriptions_by_param = {}
    current_param = None
    for _, row in descriptions_df.iterrows():
        raw_param = row.get("Parameter", "")
        raw_value = row.get("Verdi", "")
        raw_description = row.get("Beskrivelse", "")

        param_name = "" if pd.isna(raw_param) else str(raw_param).strip()
        value_name = "" if pd.isna(raw_value) else str(raw_value).strip()
        description = "" if pd.isna(raw_description) else str(raw_description).strip()

        if param_name:
            current_param = param_name
            value_descriptions_by_param.setdefault(current_param, {})
            param_descriptions[current_param] = description

        if value_name and current_param:
            value_descriptions_by_param.setdefault(current_param, {})[value_name] = description

    st.session_state.params = []
    param_name_to_id = {}
    value_name_to_id_by_param = {}

    for param_name, values in params_and_values_df.items():
        param_id = str(uuid4())
        value_list = []
        clean_param_name = str(param_name).strip()
        param_name_to_id[clean_param_name] = param_id
        value_name_to_id_by_param[param_id] = {}

        for value_name in values.dropna():
            value_id = str(uuid4())
            clean_value_name = str(value_name).strip()
            value_list.append({
                "value_id": value_id,
                "value_name": clean_value_name,
                "value_description": value_descriptions_by_param.get(clean_param_name, {}).get(clean_value_name, ""),
            })
            value_name_to_id_by_param[param_id][clean_value_name] = value_id
        st.session_state.params.append({
            "param_id": param_id,
            "param_name": clean_param_name,
            "param_description": param_descriptions.get(clean_param_name, ""),
            "values": value_list,
        })

    st.session_state.inconsistent_combinations = []
    for _, row in inconsistent_combinations_df.iterrows():
        combination_id = str(uuid4())
        combination_values = {}
        for col in inconsistent_combinations_df.columns:
            if col != "Kommentar":
                param_id = param_name_to_id.get(str(col).strip())
                if not param_id:
                    continue
                cell_value = row[col]
                if pd.notna(cell_value):
                    value_ids = []
                    for value_name in str(cell_value).split(";"):
                        clean_value_name = value_name.strip()
                        if not clean_value_name:
                            continue
                        value_id = value_name_to_id_by_param[param_id].get(clean_value_name)
                        if value_id:
                            value_ids.append(value_id)
                    if value_ids:
                        combination_values[param_id] = value_ids
        comment = row.get("Kommentar", "")
        if pd.isna(comment):
            comment = ""
        st.session_state.inconsistent_combinations.append({
            "combination_id": combination_id,
            "combination_values": combination_values,
            "comment": comment,
        })

    st.session_state.concepts = {}
    concept_name_to_intents = defaultdict(list)
    for _, row in concepts_df.iterrows():
        concept_name = row.get("Navn", "")
        if pd.isna(concept_name):
            continue
        concept_name = str(concept_name).strip()
        intent_tuple = parse_attributes_to_intent(
            row.get("Egenskaper", ""),
            param_name_to_id,
            value_name_to_id_by_param,
        )
        st.session_state.concepts[intent_tuple] = {
            "name": concept_name,
            "extent": set(),
            "value": None,
        }
        concept_name_to_intents[concept_name].append(intent_tuple)

    all_combination_keys = set()
    class_extents_by_name = defaultdict(set)
    if not possible_combinations_df.empty:
        for _, row in possible_combinations_df.iterrows():
            combination_values = {}
            for col in possible_combinations_df.columns:
                if col in ["Kombinasjon nr.", "Klassifisering"]:
                    continue
                param_id = param_name_to_id.get(str(col).strip())
                if not param_id:
                    continue
                cell_value = row.get(col)
                if pd.isna(cell_value):
                    continue
                value_id = value_name_to_id_by_param[param_id].get(str(cell_value).strip())
                if value_id:
                    combination_values[param_id] = value_id

            if not combination_values:
                continue

            combination_key = frozenset(combination_values.items())
            all_combination_keys.add(combination_key)

            for class_name in parse_class_names(row.get("Klassifisering", "")):
                class_extents_by_name[class_name].add(combination_key)

    matched_selected_intents = set()
    for class_name, class_extent in class_extents_by_name.items():
        matching_intents = concept_name_to_intents.get(class_name, [])
        if not matching_intents:
            continue
        for intent_tuple in matching_intents:
            st.session_state.concepts[intent_tuple]["extent"] = set(class_extent)
            matched_selected_intents.add(intent_tuple)

    if all_combination_keys:
        for intent_tuple, concept_info in st.session_state.concepts.items():
            if concept_info["extent"]:
                continue
            concept_extent = set()
            required_pairs = {
                tuple(intent_part.split(" = ", 1))
                for intent_part in intent_tuple
                if " = " in intent_part
            }
            for combination_key in all_combination_keys:
                if required_pairs.issubset(combination_key):
                    concept_extent.add(combination_key)
            concept_info["extent"] = concept_extent

    st.session_state.selected_concept_intents = matched_selected_intents
    st.session_state.concepts_graph = ""
    st.session_state.n_concepts = len(st.session_state.concepts)
    st.session_state.classification_params = {}
    for _, row in classification_params_df.iterrows():
        param_name = row.get("Parameter", "")
        param_id = param_name_to_id.get(str(param_name).strip())
        if not param_id:
            continue
        weight = row.get("Vekt", "")
        if pd.isna(param_name) or pd.isna(weight):
            continue
        st.session_state.classification_params[param_id] = float(weight)

    for _, row in classification_settings_df.iterrows():
        setting_key = row.get("Innstilling", "")
        setting_value = row.get("Verdi", "")
        if pd.isna(setting_key) or pd.isna(setting_value):
            continue
        setting_key = str(setting_key).strip()
        if setting_key == "Optimeringsstrategi":
            st.session_state.classification_params["optimization_strategy"] = str(setting_value)
        elif setting_key == "Maksimalt antall klasser":
            st.session_state.classification_params["max_classes"] = int(float(setting_value))

    st.session_state.listed_concepts = {}
    for _, row in listed_concepts_df.iterrows():
        intent_tuple = parse_attributes_to_intent(
            row.get("Egenskaper", ""),
            param_name_to_id,
            value_name_to_id_by_param,
        )
        list_value = row.get("Liste", "")
        if pd.isna(list_value):
            list_value = ""
        list_value = str(list_value).strip().lower()
        if list_value not in ["rød", "grønn"]:
            continue
        st.session_state.listed_concepts[intent_tuple] = "red" if list_value == "rød" else "green"

def import_from_excel():
    st.header("Last opp tidligere analyse")
    uploader_key = f"excel_uploader_{st.session_state.get('uploader_key', 0)}"
    uploaded_file = st.file_uploader(
        "Last opp Excel-fil",
        type=["xlsx"],
        label_visibility="collapsed",
        key=uploader_key,
    )
    st.caption(":red[:material/warning:] Ved opplasting vil alle nåværende data i appen bli overskrevet.")

    if uploaded_file is None:
        return

    try:
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
        params_and_values_df = pd.read_excel(xls, sheet_name='Parametere og verdier', engine="openpyxl")
        descriptions_df = pd.read_excel(xls, sheet_name='Beskrivelser', engine="openpyxl")
        inconsistent_combinations_df = pd.read_excel(xls, sheet_name='Inkonsistente kombinasjoner', engine="openpyxl")
        
        if 'Klasser' in xls.sheet_names:
            concepts_df = pd.read_excel(xls, sheet_name='Klasser', engine="openpyxl")
        else:
            concepts_df = pd.DataFrame()

        if 'Parametervekter' in xls.sheet_names:
            classification_params_df = pd.read_excel(xls, sheet_name='Parametervekter', engine="openpyxl")
        else:
            classification_params_df = pd.DataFrame()

        if 'Innstillinger' in xls.sheet_names:
            classification_settings_df = pd.read_excel(
                xls,
                sheet_name='Innstillinger',
                engine="openpyxl",
            )
        else:
            classification_settings_df = pd.DataFrame()

        if 'Rød- og grønnlistede konsepter' in xls.sheet_names:
            listed_concepts_df = pd.read_excel(xls, sheet_name='Rød- og grønnlistede konsepter', engine="openpyxl")
        else:
            listed_concepts_df = pd.DataFrame()

        if 'Mulige kombinasjoner' in xls.sheet_names:
            possible_combinations_df = pd.read_excel(xls, sheet_name='Mulige kombinasjoner', engine="openpyxl")
        else:
            possible_combinations_df = pd.DataFrame()

        transform_excel_data_to_session_state(
            params_and_values_df,
            descriptions_df,
            inconsistent_combinations_df,
            concepts_df,
            classification_params_df,
            classification_settings_df,
            listed_concepts_df,
            possible_combinations_df,
        )
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
        st.rerun()
    except Exception as e:
        st.error(f"Feil ved import av Excel-fil: {e}")