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

with st.expander("**Registrer inkonsistente kombinasjoner**"):
    st.markdown("Velg parameterverdier som ikke kan kombineres med hverandre")

    value_selectors = {}
    for parameter in parameter_names:
        value_selectors[parameter] = st.pills(
            label=parameter,
            options=values_edited[parameter].dropna().tolist(),
            selection_mode="multi",
            key=f"selector_{parameter}"
        )
    combination_comment = st.text_input("Kommentar til inkonsistent kombinasjon")

    selected_values = {param: value_selectors[param] for param in parameter_names}
    selected_parameters_count = sum(1 for values in selected_values.values() if values)
    remove_combination = st.button(
        "Fjern kombinasjon",
        type="primary",
        disabled=selected_parameters_count < 2,
        key="remove_combination")

    if "inconsistent_combinations" not in st.session_state:
        st.session_state.inconsistent_combinations = []

    if remove_combination:
        st.session_state.inconsistent_combinations.append({
            "values": selected_values,
            "comment": combination_comment
        })

    st.markdown("**Registrerte inkonsistente kombinasjoner**")
    if st.session_state.inconsistent_combinations and len(st.session_state.inconsistent_combinations) > 0:
        rows = []
        for combo in st.session_state.inconsistent_combinations:
            row = {param: vals if vals else [] for param, vals in combo["values"].items()}
            row["Kommentar"] = combo["comment"]
            rows.append(row)
        inconsistent_combinations_df = pd.DataFrame(
            rows,
            columns=parameter_names + ["Kommentar"]
        )
        edited_inconsistent_combinations_df = st.data_editor(
            inconsistent_combinations_df,
            num_rows="delete",
            hide_index=True,
            disabled=[param for param in parameter_names] + ["Kommentar"],
            key="inconsistent_combinations_editor"
        )
        updated_combinations = []
        for _, edited_row in edited_inconsistent_combinations_df.iterrows():
            combo_values = {}
            for param in parameter_names:
                cell_value = edited_row.get(param, [])
                if isinstance(cell_value, list):
                    combo_values[param] = [
                        value for value in cell_value
                        if pd.notna(value) and str(value).strip() != ""
                    ]
                elif pd.isna(cell_value):
                    combo_values[param] = []
                else:
                    combo_values[param] = [str(cell_value)]

            comment_value = edited_row.get("Kommentar", "")
            updated_combinations.append({
                "values": combo_values,
                "comment": "" if pd.isna(comment_value) else str(comment_value)
            })
        st.session_state.inconsistent_combinations = updated_combinations
    else:
        st.info("Ingen inkonsistente kombinasjoner registrert.")

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

    inconsistent_combinations = st.session_state.get("inconsistent_combinations", [])
    if inconsistent_combinations:
        excluded_mask = pd.Series(False, index=combinations_df.index)

        for combo in inconsistent_combinations:
            combo_mask = pd.Series(True, index=combinations_df.index)
            has_selected_values = False

            for param, selected_vals in combo["values"].items():
                cleaned_values = [
                    value for value in selected_vals
                    if pd.notna(value) and str(value).strip() != ""
                ]
                if cleaned_values:
                    has_selected_values = True
                    combo_mask &= combinations_df[param].isin(cleaned_values)

            if has_selected_values:
                excluded_mask |= combo_mask

        combinations_df = combinations_df.loc[~excluded_mask].reset_index(drop=True)

    number_of_combinations = len(combinations_df)
    st.subheader(f"Mulige kombinasjoner ({number_of_combinations})")
    st.dataframe(combinations_df)
else:
    st.subheader("Mulige kombinasjoner")
    st.info("Legg inn minst én verdi for hver parameter for å se mulige kombinasjoner.")

st.warning("""
    TODO:
    - Sørge for at man kan endre parametere uten at det overskriver allerede definerte verdier
    - Gi et varsel hvis brukeren prøver å legge til en inkonsistent kombinasjon som allerede er dekket av en tidligere registrert kombinasjon
""")