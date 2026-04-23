import streamlit as st
import pandas as pd
from io import BytesIO
from helpers import get_param_name_by_id, get_value_name_by_id

def export_to_excel(inconsistent_combinations_df, possible_combinations_df):
    params_and_values_data = {}
    for param in st.session_state.params:
        param_name = param["param_name"].strip()
        values = [value["value_name"] for value in param["values"]]
        params_and_values_data[param_name] = pd.Series(values)
    params_and_values_df = pd.DataFrame(params_and_values_data)
    
    descriptions_data = []
    for param in st.session_state.params:
        param_name = param["param_name"].strip()
        param_desc = param["param_description"].strip()
        descriptions_data.append({
            "Parameter": param_name,
            "Verdi": "",
            "Beskrivelse": param_desc
        })
        for value in param["values"]:
            value_name = value["value_name"].strip()
            value_desc = value["value_description"].strip()
            descriptions_data.append({
                "Parameter": "",
                "Verdi": value_name,
                "Beskrivelse": value_desc
            })
    descriptions_df = pd.DataFrame(descriptions_data)

    clean_inconsistent_combinations_df = inconsistent_combinations_df.copy()
    if not clean_inconsistent_combinations_df.empty:
        clean_inconsistent_combinations_df.drop(columns=["_combination_id"], inplace=True)
        param_columns = [col for col in clean_inconsistent_combinations_df.columns if col != "Kommentar"]
        for col in param_columns:
            clean_inconsistent_combinations_df[col] = clean_inconsistent_combinations_df[col].apply(
                lambda value: "; ".join(value) if isinstance(value, list) else value
            )

    clean_possible_combinations_df = possible_combinations_df.copy()
    if not clean_possible_combinations_df.empty:
        clean_possible_combinations_df["Klassifisering"] = clean_possible_combinations_df["Klassifisering"].apply(
            lambda classes: "; ".join(classes) if isinstance(classes, list) else classes
        )

    concepts_data = []
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    for concept_intent_tuple, concept_info in st.session_state.concepts.items():
        concept_name = concept_info["name"]
        concept_extent = concept_info["extent"]
        intent_descriptions = []
        for intent in concept_intent_tuple:
            param_id, value_id = intent.split(" = ")
            param_name = param_name_by_id.get(param_id, f"Param {param_id}")
            value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
            intent_descriptions.append(f"{param_name} = {value_name}")
        concepts_data.append({
            "Konseptnavn": concept_name,
            "Egenskaper": "; ".join(intent_descriptions),
            "Antall kombinasjoner": len(concept_extent)
        })
    concepts_df = pd.DataFrame(concepts_data)

    classification_params_data = []
    for param_name, param_value in st.session_state.classification_params.items():
        classification_params_data.append({
            "Parameter": param_name,
            "Verdi": str(param_value)
        })
    classification_params_df = pd.DataFrame(classification_params_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        params_and_values_df.to_excel(writer, index=False, sheet_name='Parametere og verdier')
        descriptions_df.to_excel(writer, index=False, sheet_name='Beskrivelser')
        clean_inconsistent_combinations_df.to_excel(writer, index=False, sheet_name='Inkonsistente kombinasjoner')
        clean_possible_combinations_df.to_excel(writer, index=False, sheet_name='Mulige kombinasjoner')
        concepts_df.to_excel(writer, index=False, sheet_name='Klasser')
        classification_params_df.to_excel(writer, index=False, sheet_name='Klassifiseringsparametre')
    excel_data = output.getvalue()
    
    st.header("Lagre analyse")
    st.download_button(
        label="Eksporter til Excel",
        icon=":material/download:",
        data=excel_data,
        file_name="Morfologi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )