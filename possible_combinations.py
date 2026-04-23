import streamlit as st
import pandas as pd
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
)

def possible_combinations():
    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner.")
        return pd.DataFrame()
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    param_columns = [param["param_name"] for param in st.session_state.params]
    table_rows = []
    for combination in st.session_state.possible_combinations:
        combination_values = combination["combination_values"]
        row = {
            param_name_by_id[param_id]: value_name_by_id[value_id]
            for param_id, value_id in combination_values.items()
        }
        row["Kombinasjon nr."] = combination["combination_number"]
        combination_class_names = combination["combination_class_names"]
        row["Klassifisering"] = combination_class_names
        table_rows.append(row)
    table_df = pd.DataFrame(
        table_rows,
        columns=["Kombinasjon nr."] + param_columns + ["Klassifisering"],
    )
    table_df = table_df.set_index("Kombinasjon nr.")
    st.dataframe(table_df, hide_index=False)
    return table_df