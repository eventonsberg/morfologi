import streamlit as st
import pandas as pd
from uuid import uuid4
from helpers import get_param_name_by_id, get_value_name_by_id

def inconsistent_combinations():
    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner. Definer parametere og verdier først.")
        return
    with st.form("inconsistent_combinations_form", clear_on_submit=True):
        st.caption("Velg verdier som ikke kan kombineres med hverandre")
        value_selectors = {}
        for param in st.session_state.params:
            values = param["values"]
            value_ids = [value["value_id"] for value in values]
            value_names_by_id = get_value_name_by_id([param])
            value_selector = st.pills(
                f"**{param['param_name']}**",
                value_ids,
                selection_mode="multi",
                format_func=lambda value_id, names=value_names_by_id: names[value_id],
                key=f"value_selector_{param['param_id']}",
            )
            value_selectors[param["param_id"]] = value_selector
        comment = st.text_input(
            "**Kommentar**",
            placeholder="Skriv inn kommentar",
            key="inconsistent_combination_comment",
        )
        submit_inconsistent_combination = st.form_submit_button("Registrer inkonsistens")
        if submit_inconsistent_combination:
            combination_values = {
                param_id: selected_value_ids
                for param_id, selected_value_ids in value_selectors.items()
                if selected_value_ids
            }
            if len(combination_values) < 2:
                st.warning("Minst én verdi fra to ulike parametere må velges.")
            else:
                st.session_state.inconsistent_combinations.append(
                    {
                        "combination_id": str(uuid4()),
                        "combination_values": combination_values,
                        "comment": comment.strip(),
                    }
                )
                st.rerun()
    
    st.subheader("Registrerte inkonsistente kombinasjoner")
    if not st.session_state.inconsistent_combinations:
        st.info("Ingen inkonsistente kombinasjoner registrert.")
    else:
        param_name_by_id = get_param_name_by_id(st.session_state.params)
        value_name_by_id = get_value_name_by_id(st.session_state.params)
        param_columns = [param["param_name"] for param in st.session_state.params]

        table_rows = []
        for combination in st.session_state.inconsistent_combinations:
            row = {
                "_combination_id": combination["combination_id"],
                **{param_name: [] for param_name in param_columns},
            }

            for param_id, value_ids in combination["combination_values"].items():
                param_name = param_name_by_id.get(param_id)
                if not param_name:
                    continue

                row[param_name] = [
                    value_name_by_id.get(value_id, f"Ukjent verdi ({value_id})")
                    for value_id in value_ids
                ]

            row["Kommentar"] = combination.get("comment", "")
            table_rows.append(row)
        editor_columns = ["_combination_id", *param_columns, "Kommentar"]
        table_df = pd.DataFrame(table_rows, columns=editor_columns)
        edited_table_df = st.data_editor(
            table_df,
            hide_index=True,
            num_rows="delete",
            column_config={"_combination_id": None},
            disabled=param_columns + ["Kommentar"],
            key="inconsistent_combinations_editor",
        )
        st.caption("For å slette en tidligere registrert kombinasjon, marker raden i venstre kolonne og trykk *Delete*.")
        remaining_ids = set(edited_table_df["_combination_id"].dropna().tolist())
        current_ids = {
            combination["combination_id"]
            for combination in st.session_state.inconsistent_combinations
        }
        if remaining_ids != current_ids:
            st.session_state.inconsistent_combinations = [
                combination
                for combination in st.session_state.inconsistent_combinations
                if combination["combination_id"] in remaining_ids
            ]
            st.rerun()