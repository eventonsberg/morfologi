import streamlit as st
import pandas as pd
from io import BytesIO
from helpers import get_param_name_by_id, get_value_name_by_id

def generate_excel_data():
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

    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    param_columns = [param["param_name"] for param in st.session_state.params]

    inconsistent_rows = []
    for combination in st.session_state.get("inconsistent_combinations", []):
        row = {
            "_combination_id": combination.get("combination_id", ""),
            **{param_name: [] for param_name in param_columns},
        }
        for param_id, value_ids in combination.get("combination_values", {}).items():
            param_name = param_name_by_id.get(param_id)
            if not param_name:
                continue
            row[param_name] = [
                value_name_by_id.get(value_id, f"Ukjent verdi ({value_id})")
                for value_id in value_ids
            ]
        row["Kommentar"] = combination.get("comment", "")
        inconsistent_rows.append(row)

    inconsistent_combinations_df = pd.DataFrame(
        inconsistent_rows,
        columns=["_combination_id", *param_columns, "Kommentar"],
    )
    clean_inconsistent_combinations_df = inconsistent_combinations_df.copy()
    if not clean_inconsistent_combinations_df.empty:
        clean_inconsistent_combinations_df.drop(columns=["_combination_id"], inplace=True)
        exported_param_columns = [col for col in clean_inconsistent_combinations_df.columns if col != "Kommentar"]
        for col in exported_param_columns:
            clean_inconsistent_combinations_df[col] = clean_inconsistent_combinations_df[col].apply(
                lambda value: "; ".join(value) if isinstance(value, list) else value
            )

    possible_rows = []
    for combination in st.session_state.get("possible_combinations", []):
        row = {
            "Kombinasjon nr.": combination.get("combination_number"),
            **{param_name: "" for param_name in param_columns},
            "Klassifisering": combination.get("combination_class_names", []),
        }
        for param_id, value_id in combination.get("combination_values", {}).items():
            param_name = param_name_by_id.get(param_id)
            if not param_name:
                continue
            row[param_name] = value_name_by_id.get(value_id, f"Ukjent verdi ({value_id})")
        possible_rows.append(row)

    possible_combinations_df = pd.DataFrame(
        possible_rows,
        columns=["Kombinasjon nr.", *param_columns, "Klassifisering"],
    )
    clean_possible_combinations_df = possible_combinations_df.copy()
    if not clean_possible_combinations_df.empty:
        clean_possible_combinations_df["Klassifisering"] = clean_possible_combinations_df["Klassifisering"].apply(
            lambda classes: "; ".join(classes) if isinstance(classes, list) else classes
        )

    concepts_data = []
    selected_concept_intents = st.session_state.get("selected_concept_intents", set())
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
            "Navn": concept_name,
            "Valgt som klasse": "JA" if concept_intent_tuple in selected_concept_intents else "NEI",
            "Egenskaper": "; ".join(intent_descriptions),
            "Antall kombinasjoner": len(concept_extent),
        })
    concepts_df = pd.DataFrame(concepts_data)

    classification_params_data = []
    for param_id, param_value in st.session_state.classification_params.items():
        classification_params_data.append({
            "Parameter": param_name_by_id.get(param_id, f"Param {param_id}"),
            "Vekt": str(param_value)
        })
    classification_params_df = pd.DataFrame(classification_params_data)

    listed_concepts_data = []
    for concept_intent_tuple, list_value in st.session_state.listed_concepts.items():
        intent_descriptions = []
        for intent in concept_intent_tuple:
            param_id, value_id = intent.split(" = ")
            param_name = param_name_by_id.get(param_id, f"Param {param_id}")
            value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
            intent_descriptions.append(f"{param_name} = {value_name}")
        listed_concepts_data.append({
            "Egenskaper": "; ".join(intent_descriptions),
            "Liste": "RØD" if list_value == "red" else ("GRØNN" if list_value == "green" else "")
        })
    listed_concepts_df = pd.DataFrame(listed_concepts_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        params_and_values_df.to_excel(writer, index=False, sheet_name='Parametere og verdier')
        descriptions_df.to_excel(writer, index=False, sheet_name='Beskrivelser')
        clean_inconsistent_combinations_df.to_excel(writer, index=False, sheet_name='Inkonsistente kombinasjoner')
        clean_possible_combinations_df.to_excel(writer, index=False, sheet_name='Mulige kombinasjoner')
        if not concepts_df.empty:
            concepts_df.to_excel(writer, index=False, sheet_name='Klasser')
        if not classification_params_df.empty:
            classification_params_df.to_excel(writer, index=False, sheet_name='Parametervekter')
        if not listed_concepts_df.empty:
            listed_concepts_df.to_excel(writer, index=False, sheet_name='Rød- og grønnlistede konsepter')
    return output.getvalue()


@st.dialog("Eksporter til Excel")
def export_dialog():
    st.markdown("Excel-filen er klar. Klikk på knappen under for å laste den ned.")
    st.download_button(
        label="Last ned Excel-fil",
        type="primary",
        icon=":material/download:",
        data=st.session_state.excel_data,
        file_name="Morfologi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def export_to_excel():
    st.header("Lagre analyse")

    if st.button("Eksporter til Excel", icon=":material/download:"):
        with st.spinner("Genererer Excel-fil..."):
            st.session_state.excel_data = generate_excel_data()
        export_dialog()