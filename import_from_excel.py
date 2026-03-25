import streamlit as st
import pandas as pd
from uuid import uuid4

def transform_excel_data_to_session_state(params_and_values_df, inconsistent_combinations_df):
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
            value_list.append({"value_id": value_id, "value_name": clean_value_name})
            value_name_to_id_by_param[param_id][clean_value_name] = value_id
        st.session_state.params.append({"param_id": param_id, "param_name": clean_param_name, "values": value_list})

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
        st.session_state.inconsistent_combinations.append({"combination_id": combination_id, "combination_values": combination_values, "comment": comment})

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
            transform_excel_data_to_session_state(params_and_values_df, inconsistent_combinations_df)
            st.rerun()
        except Exception as e:
            st.error(f"Feil ved import av Excel-fil: {e}")