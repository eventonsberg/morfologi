import streamlit as st
import pandas as pd
from uuid import uuid4
from helpers import get_param_name_by_id, get_value_name_by_id
from itertools import product


def value_axis_metadata(params):
    entries = []
    label_by_value_id = {}

    for param in params:
        param_id = param["param_id"]
        param_name = param["param_name"]
        for value in param["values"]:
            value_id = value["value_id"]
            value_name = value["value_name"]
            label = (param_name, value_name)
            entries.append(
                {
                    "param_id": param_id,
                    "value_id": value_id,
                    "label": label,
                }
            )
            label_by_value_id[value_id] = label

    return entries, label_by_value_id

def all_value_names(params):
    value_names = []
    value_to_param = {}

    for param in params:
        for value in param["values"]:
            name = value["value_name"]
            value_names.append(name)
            value_to_param[name] = param["param_id"]

    return value_names, value_to_param


def empty_triangular_cc_matrix(params):
    entries, _ = value_axis_metadata(params)
    labels = [entry["label"] for entry in entries]

    df = pd.DataFrame(
        False,
        index=labels,
        columns=labels,
        dtype="boolean",
    )

    for i, row_entry in enumerate(entries):
        for j, col_entry in enumerate(entries):

            # Øvre-høyre greier
            #if j > i:
            #    df.iloc[i, j] = pd.NA

            # Like parametre
            if row_entry["param_id"] == col_entry["param_id"]:
                df.iloc[i, j] = pd.NA
    
    df = df.dropna(axis=0, how="all") 
    df = df.dropna(axis=1, how="all")

    df.index = pd.MultiIndex.from_tuples(
        df.index,
        names=["Parameter", "Verdi"],
    )
    df.columns = pd.MultiIndex.from_tuples(
        df.columns,
        names=["Parameter (kol)", "Verdi (kol)"],
    )

    return df

def empty_value_cc_matrix(params):
    values, value_to_param = all_value_names(params)

    df = pd.DataFrame(False, index=values, columns=values)

    for v1 in values:
        for v2 in values:
            if value_to_param[v1] == value_to_param[v2]:
                df.loc[v1, v2] = pd.NA

    return df


def fill_value_inconsistencies(df, inconsistent_combinations, params):
    _, label_by_value_id = value_axis_metadata(params)

    for combo in inconsistent_combinations:
        combo_vals = combo["combination_values"]

        # Kun par av parametre, ikke tripler etc
        if len(combo_vals) != 2:
            continue

        (_, v1_ids), (_, v2_ids) = combo_vals.items()

        for v1_id, v2_id in product(v1_ids, v2_ids):
            label_v1 = label_by_value_id.get(v1_id)
            label_v2 = label_by_value_id.get(v2_id)
            if label_v1 is None or label_v2 is None:
                continue

            df.loc[label_v2, label_v1] = True
            df.loc[label_v1, label_v2] = True

    return df


def inconsistent_combinations():
    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner.")
    else:
        with st.container(border=True):
            st.caption("Velg verdier som ikke kan kombineres med hverandre")
            form_reset_id = st.session_state.get("inconsistent_form_reset_id", 0)

            selected_by_param: dict[str, set[str]] = {}
            for param in st.session_state.params:
                param_id = param["param_id"]
                selection_key = f"value_selector_{param_id}_{form_reset_id}"
                selected_by_param[param_id] = set(st.session_state.get(selection_key) or [])

            # Build a pairwise inconsistency lookup from already-registered combinations
            inconsistency_map: dict[str, set[str]] = {}
            multi_param_combos: list[dict[str, set[str]]] = []
            for combo in st.session_state.inconsistent_combinations:
                combo_vals = combo["combination_values"]
                normalized_combo_vals = {
                    param_id: set(value_ids)
                    for param_id, value_ids in combo_vals.items()
                    if value_ids
                }
                if len(normalized_combo_vals) < 2:
                    continue

                if len(normalized_combo_vals) == 2:
                    (_, v1_ids), (_, v2_ids) = normalized_combo_vals.items()
                    for v1 in v1_ids:
                        for v2 in v2_ids:
                            inconsistency_map.setdefault(v1, set()).add(v2)
                            inconsistency_map.setdefault(v2, set()).add(v1)
                    continue

                multi_param_combos.append(normalized_combo_vals)

            value_selectors = {}
            for param in st.session_state.params:
                values = param["values"]
                value_ids = [value["value_id"] for value in values]
                value_names_by_id = get_value_name_by_id([param])
                key = f"value_selector_{param['param_id']}_{form_reset_id}"

                # Collect values currently selected in all OTHER parameters
                selected_from_others: set[str] = set()
                for other_param in st.session_state.params:
                    if other_param["param_id"] == param["param_id"]:
                        continue
                    other_key = f"value_selector_{other_param['param_id']}_{form_reset_id}"
                    selected_from_others.update(st.session_state.get(other_key) or [])

                # Values that are inconsistent with any already-selected value.
                excluded: set[str] = set()
                for selected_val in selected_from_others:
                    excluded.update(inconsistency_map.get(selected_val, set()))
                current_selection = st.session_state.get(key) or []

                for value_id in value_ids:
                    if value_id in excluded:
                        continue

                    candidate_selection = set(current_selection)
                    candidate_selection.add(value_id)

                    for combo_vals in multi_param_combos:
                        if param["param_id"] not in combo_vals:
                            continue
                        if not candidate_selection.intersection(combo_vals[param["param_id"]]):
                            continue

                        combo_is_matched = True
                        for combo_param_id, combo_value_ids in combo_vals.items():
                            if combo_param_id == param["param_id"]:
                                selected_for_combo_param = candidate_selection
                            else:
                                selected_for_combo_param = selected_by_param.get(combo_param_id, set())

                            if not selected_for_combo_param.intersection(combo_value_ids):
                                combo_is_matched = False
                                break

                        if combo_is_matched:
                            excluded.add(value_id)
                            break

                available_value_ids = [vid for vid in value_ids if vid not in excluded]

                # Remove stale selections (values that are no longer available).
                cleaned_selection = [v for v in current_selection if v in available_value_ids]
                if cleaned_selection != current_selection:
                    st.session_state[key] = cleaned_selection
                selected_by_param[param["param_id"]] = set(cleaned_selection)

                value_selector = st.pills(
                    f"**{param['param_name']}**",
                    available_value_ids,
                    selection_mode="multi",
                    format_func=lambda value_id, names=value_names_by_id: names[value_id],
                    key=key,
                )
                value_selectors[param["param_id"]] = value_selector

            st.caption("Verdier skjules hvis de er inkonsistente med en allerede valgt verdi eller en kombinasjon av valgte verdier")

            comment_key = f"inconsistent_combination_comment_{form_reset_id}"
            comment = st.text_input(
                "**Kommentar**",
                placeholder="Skriv inn kommentar",
                key=comment_key,
            )
            if st.button("Registrer inkonsistens"):
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
                    # Force fresh widget keys on next run to fully reset pills and comment.
                    st.session_state["inconsistent_form_reset_id"] = form_reset_id + 1
                    st.rerun()
    
    st.subheader("Inkonsistente kombinasjoner")
    if not st.session_state.inconsistent_combinations:
        st.info("Ingen inkonsistente kombinasjoner registrert.")
        st.session_state.inconsistent_combinations_df = pd.DataFrame()
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
            height="content"
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

        st.divider()
        st.subheader("Parvis inkonsistens")

        blank_cc_matrix = empty_triangular_cc_matrix(st.session_state.params)
        filled_cc_matrix = fill_value_inconsistencies(
            blank_cc_matrix,
            st.session_state.inconsistent_combinations,
            st.session_state.params,
        )
        st.dataframe(filled_cc_matrix, height="content")

        st.session_state.inconsistent_combinations_df = table_df
