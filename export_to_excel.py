import streamlit as st
import pandas as pd
from io import BytesIO
from helpers import get_classification_rule_name_by_rule_id

def export_to_excel(inconsistent_combinations_df, possible_combinations_df, classification_rules_df):
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

    clean_classification_rules_df = classification_rules_df.copy()
    if not clean_classification_rules_df.empty:
        clean_classification_rules_df.drop(columns=["_rule_id"], inplace=True)
        param_columns = [col for col in clean_classification_rules_df.columns if col != "Klassifiseringsregel"]
        for col in param_columns:
            clean_classification_rules_df[col] = clean_classification_rules_df[col].apply(
                lambda value: "; ".join(value) if isinstance(value, list) else value
            )

    combination_classes_data = []
    classification_rule_name_by_rule_id = get_classification_rule_name_by_rule_id(st.session_state.classification_rules)
    for combination_class in st.session_state.combination_classes:
        number_of_combinations = combination_class.get("number_of_combinations", 0)
        if number_of_combinations > 0:
            class_name = combination_class["combination_class_name"].strip()
            classification_rule_ids = combination_class["classification_rule_ids"]
            classification_rule_names = [
                classification_rule_name_by_rule_id[rule_id].strip()
                for rule_id in classification_rule_ids
            ]
            combination_classes_data.append({
                "Kombinasjonsklasse": class_name,
                "Klassifiseringsregler": "; ".join(classification_rule_names),
                "Antall kombinasjoner": number_of_combinations
            })
    combination_classes_df = pd.DataFrame(combination_classes_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        params_and_values_df.to_excel(writer, index=False, sheet_name='Parametere og verdier')
        descriptions_df.to_excel(writer, index=False, sheet_name='Beskrivelser')
        clean_inconsistent_combinations_df.to_excel(writer, index=False, sheet_name='Inkonsistente kombinasjoner')
        possible_combinations_df.to_excel(writer, index=False, sheet_name='Mulige kombinasjoner')
        clean_classification_rules_df.to_excel(writer, index=False, sheet_name='Klassifiseringsregler')
        combination_classes_df.to_excel(writer, index=False, sheet_name='Kombinasjonsklasser')
    excel_data = output.getvalue()
    
    st.header("Lagre analyse")
    st.download_button(
        label="Eksporter til Excel",
        icon=":material/download:",
        data=excel_data,
        file_name="Morfologi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )