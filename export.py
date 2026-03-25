import streamlit as st
import pandas as pd
from io import BytesIO

def export_to_excel(inconsistent_combinations_df, possible_combinations_df):
    params_and_values_data = {}
    for param in st.session_state.params:
        param_name = param["param_name"].strip()
        values = [value["value_name"] for value in param["values"]]
        params_and_values_data[param_name] = pd.Series(values)
    params_and_values_df = pd.DataFrame(params_and_values_data)
    
    clean_inconsistent_combinations_df = inconsistent_combinations_df.copy()
    if not clean_inconsistent_combinations_df.empty:
        clean_inconsistent_combinations_df.drop(columns=["_combination_id"], inplace=True)
        param_columns = [col for col in clean_inconsistent_combinations_df.columns if col != "Kommentar"]
        for col in param_columns:
            clean_inconsistent_combinations_df[col] = clean_inconsistent_combinations_df[col].apply(
                lambda value: "; ".join(value) if isinstance(value, list) else value
            )

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        params_and_values_df.to_excel(writer, index=False, sheet_name='Parametere og verdier')
        clean_inconsistent_combinations_df.to_excel(writer, index=False, sheet_name='Inkonsistente kombinasjoner')
        possible_combinations_df.to_excel(writer, index=False, sheet_name='Mulige kombinasjoner')
    excel_data = output.getvalue()
    st.download_button(
        label="Eksporter til Excel",
        data=excel_data,
        file_name="Morfologi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )