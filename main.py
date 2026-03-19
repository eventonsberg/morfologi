import streamlit as st
import pandas as pd
from itertools import product

st.set_page_config(
    page_title="Morfologi"
)

st.title("Morfologi")

parameters_df = pd.DataFrame({
    "Parameter": ["Parameter 1", "Parameter 2", "Parameter 3"]
})

st.markdown("**Angi parametere**")
parameters_edited = st.data_editor(
    parameters_df,
    num_rows="dynamic",
    column_config={
        "Parameter": st.column_config.TextColumn(required=True)
    }
)

parameter_names = [
    str(parameter)
    for parameter in parameters_edited["Parameter"]
    if pd.notna(parameter) and str(parameter).strip() != ""
]

values = []
for i in range(1, 4):
    row_values = {}
    for parameter_index, parameter in enumerate(parameter_names, start=1):
        row_values[parameter] = f"Verdi {parameter_index}-{i}"
    values.append(row_values)

values_df = pd.DataFrame(values)

st.markdown("**Angi parameterverdier**")
values_edited = st.data_editor(
    values_df,
    num_rows="dynamic",
    column_config={
        parameter: st.column_config.TextColumn() for parameter in parameter_names
    }
)

st.subheader("Mulige kombinasjoner")

parameter_values = []
for parameter in parameter_names:
    unique_values = [
        value for value in values_edited[parameter].dropna().tolist()
        if str(value).strip() != ""
    ]
    if unique_values:
        parameter_values.append(unique_values)

if parameter_names and len(parameter_values) == len(parameter_names):
    combinations_df = pd.DataFrame(product(*parameter_values), columns=parameter_names)
    st.dataframe(combinations_df)
else:
    st.info("Legg inn minst én verdi for hver parameter for å se mulige kombinasjoner.")