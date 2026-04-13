import streamlit as st
import pandas as pd
from uuid import uuid4

def transform_excel_data_to_session_state(
    params_and_values_df,
    inconsistent_combinations_df,
    descriptions_df,
    classification_rules_df,
    combination_classes_df
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

    st.session_state.classification_rules = []
    classification_rule_name_to_id = {}
    for _, row in classification_rules_df.iterrows():
        rule_id = str(uuid4())
        combination_values = {}
        for col in classification_rules_df.columns:
            if col != "Klassifiseringsregel":
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
        classification_rule_name = row.get("Klassifiseringsregel", "")
        if pd.isna(classification_rule_name):
            classification_rule_name = ""
        st.session_state.classification_rules.append({
            "classification_rule_id": rule_id,
            "classification_rule_name": classification_rule_name,
            "combination_values": combination_values,
        })
        classification_rule_name_to_id[classification_rule_name] = rule_id

    st.session_state.combination_classes = []
    for _, row in combination_classes_df.iterrows():
        class_id = str(uuid4())
        class_name = row.get("Kombinasjonsklasse", "")
        if pd.isna(class_name):
            class_name = ""
        classification_rule_names_cell = row.get("Klassifiseringsregler", "")
        classification_rule_ids = []
        if pd.notna(classification_rule_names_cell):
            for rule_name in str(classification_rule_names_cell).split(";"):
                clean_rule_name = rule_name.strip()
                rule_id = classification_rule_name_to_id.get(clean_rule_name)
                if rule_id:
                    classification_rule_ids.append(rule_id)
        number_of_combinations = row.get("Antall kombinasjoner", 0)
        if pd.isna(number_of_combinations):
            number_of_combinations = 0
        st.session_state.combination_classes.append({
            "combination_class_id": class_id,
            "combination_class_name": class_name,
            "classification_rule_ids": classification_rule_ids,
            "number_of_combinations": number_of_combinations,
        })

def import_from_excel():
    st.header("Last opp tidligere analyse")
    uploaded_file = st.file_uploader(
        "Last opp Excel-fil",
        type=["xlsx"],
        label_visibility="collapsed",
        key="excel_uploader",
    )
    import_clicked = st.button(
        label="Importer fra Excel",
        icon=":material/upload:",
        disabled=uploaded_file is None,
    )
    st.caption(":red[:material/warning:] Ved import vil alle nåværende data i appen bli overskrevet.")
    if import_clicked:
        try:
            xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
            params_and_values_df = pd.read_excel(xls, sheet_name='Parametere og verdier', engine="openpyxl")
            inconsistent_combinations_df = pd.read_excel(xls, sheet_name='Inkonsistente kombinasjoner', engine="openpyxl")
            descriptions_df = pd.read_excel(xls, sheet_name='Beskrivelser', engine="openpyxl")
            classification_rules_df = pd.read_excel(xls, sheet_name='Klassifiseringsregler', engine="openpyxl")
            combination_classes_df = pd.read_excel(xls, sheet_name='Kombinasjonsklasser', engine="openpyxl")
            transform_excel_data_to_session_state(
                params_and_values_df,
                inconsistent_combinations_df,
                descriptions_df,
                classification_rules_df,
                combination_classes_df
            )
            st.rerun()
        except Exception as e:
            st.error(f"Feil ved import av Excel-fil: {e}")