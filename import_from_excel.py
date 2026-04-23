import streamlit as st
import pandas as pd
import hashlib
from io import BytesIO
from uuid import uuid4

def transform_excel_data_to_session_state(
    params_and_values_df,
    descriptions_df,
    inconsistent_combinations_df,
    concepts_df,
    classification_params_df
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
    for _, row in concepts_df.iterrows():
        concept_name = row.get("Konseptnavn", "")
        if pd.isna(concept_name):
            continue
        concept_name = str(concept_name).strip()
        intent_tuple = tuple()
        attributes_str = row.get("Egenskaper", "")
        if pd.isna(attributes_str):
            attributes_str = ""
        for attr in attributes_str.split(";"):
            parts = attr.split(" = ")
            if len(parts) != 2:
                continue
            param_name, value_name = parts
            param_name = param_name.strip()
            value_name = value_name.strip()
            param_id = param_name_to_id.get(param_name)
            if not param_id:
                continue
            value_id = value_name_to_id_by_param[param_id].get(value_name)
            if not value_id:
                continue
            intent_tuple += (f"{param_id} = {value_id}",)
        st.session_state.concepts[intent_tuple] = {
            "name": concept_name,
            "extent": set(),
        }
    st.session_state.selected_concept_intents = set()
    st.session_state.concepts_graph = ""
    st.session_state.n_concepts = 0
    st.session_state.classification_params = {}
    for _, row in classification_params_df.iterrows():
        param_name = row.get("Parameter", "")
        value = row.get("Verdi", "")
        if pd.isna(param_name) or pd.isna(value):
            continue
        st.session_state.classification_params[str(param_name).strip()] = str(value).strip()

def import_from_excel():
    st.header("Last opp tidligere analyse")
    uploaded_file = st.file_uploader(
        "Last opp Excel-fil",
        type=["xlsx"],
        label_visibility="collapsed",
        key="excel_uploader",
    )
    st.caption(":red[:material/warning:] Ved opplasting vil alle nåværende data i appen bli overskrevet.")

    if uploaded_file is None:
        st.session_state.pop("last_imported_excel_hash", None)
        return

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    if st.session_state.get("last_imported_excel_hash") == file_hash:
        return

    try:
        xls = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
        params_and_values_df = pd.read_excel(xls, sheet_name='Parametere og verdier', engine="openpyxl")
        descriptions_df = pd.read_excel(xls, sheet_name='Beskrivelser', engine="openpyxl")
        inconsistent_combinations_df = pd.read_excel(xls, sheet_name='Inkonsistente kombinasjoner', engine="openpyxl")
        concepts_df = pd.read_excel(xls, sheet_name='Konsepter', engine="openpyxl")
        classification_params_df = pd.read_excel(xls, sheet_name='Klassifiseringsparametre', engine="openpyxl")
        transform_excel_data_to_session_state(
            params_and_values_df,
            descriptions_df,
            inconsistent_combinations_df,
            concepts_df,
            classification_params_df
        )
        st.session_state.last_imported_excel_hash = file_hash
        st.rerun()
    except Exception as e:
        st.error(f"Feil ved import av Excel-fil: {e}")