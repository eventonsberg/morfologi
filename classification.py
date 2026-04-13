import streamlit as st
from helpers import get_param_name_by_id, get_value_name_by_id
from uuid import uuid4
import pandas as pd
from classification_calculation import display_combination_classes

def classification():
    st.header("Klassifiseringsregler")
    with st.expander("Definer regler for klassifisering av kombinasjoner"):
        if st.session_state.n_combinations[0] == 0:
            st.info("Ingen mulige kombinasjoner.")
        else:
            with st.form("classification_rules_form", clear_on_submit=True, border=False):
                classification_rule_name = st.text_input(
                    "**Klassifiseringsregel**",
                    placeholder="Angi navn på klassifiseringsregel",
                    key="classification_input",
                )
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
                        key=f"rules_value_selector_{param['param_id']}",
                    )
                    value_selectors[param["param_id"]] = value_selector
                submit_classification_rule = st.form_submit_button("Registrer klassifiseringsregel")
                if submit_classification_rule:
                    combination_values = {
                        param_id: selected_value_ids
                        for param_id, selected_value_ids in value_selectors.items()
                        if selected_value_ids
                    }
                    if len(combination_values) < 1:
                        st.warning("Minst én verdi må velges.")
                    elif not classification_rule_name.strip():
                        st.warning("Klassifiseringsregelen må navngis.")
                    elif any(
                        rule["classification_rule_name"].strip() == classification_rule_name.strip()
                        for rule in st.session_state.classification_rules
                    ):
                        st.warning("Klassifiseringsregelen må ha et unikt navn.")
                    else:
                        st.session_state.classification_rules.append(
                            {
                                "classification_rule_id": str(uuid4()),
                                "classification_rule_name": classification_rule_name.strip(),
                                "combination_values": combination_values,
                            }
                        )
                        st.rerun()
        
    if not st.session_state.classification_rules:
        st.info("Ingen klassifiseringsregler registrert.")
        return_table = pd.DataFrame()
    else:
        param_name_by_id = get_param_name_by_id(st.session_state.params)
        value_name_by_id = get_value_name_by_id(st.session_state.params)
        param_columns = [param["param_name"] for param in st.session_state.params]

        table_rows = []
        for classification_rule in st.session_state.classification_rules:
            row = {
                "_rule_id": classification_rule["classification_rule_id"],
                **{param_name: [] for param_name in param_columns},
            }
            for param_id, value_ids in classification_rule["combination_values"].items():
                param_name = param_name_by_id.get(param_id)
                if not param_name:
                    continue

                row[param_name] = [
                    value_name_by_id.get(value_id, f"Ukjent verdi ({value_id})")
                    for value_id in value_ids
                ]

            row["Klassifiseringsregel"] = classification_rule.get("classification_rule_name", "")
            table_rows.append(row)
        editor_columns = ["_rule_id", "Klassifiseringsregel", *param_columns]
        table_df = pd.DataFrame(table_rows, columns=editor_columns)
        edited_table_df = st.data_editor(
            table_df,
            hide_index=True,
            num_rows="delete",
            column_config={"_rule_id": None},
            disabled=["Klassifiseringsregel"] + param_columns,
            key="classification_rules_editor",
        )
        st.caption("For å slette en klassifiseringsregel, marker raden i venstre kolonne og trykk *Delete*.")
        remaining_ids = set(edited_table_df["_rule_id"].dropna().tolist())
        current_ids = {
            rule["classification_rule_id"]
            for rule in st.session_state.classification_rules
        }
        if remaining_ids != current_ids:
            st.session_state.classification_rules = [
                rule
                for rule in st.session_state.classification_rules
                if rule["classification_rule_id"] in remaining_ids
            ]
            st.rerun()
        return_table = table_df
        
    st.divider()
    st.header("Kombinasjonsklasser")
    display_combination_classes()

    return return_table