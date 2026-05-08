import streamlit as st
import pandas as pd
from uuid import uuid4
from helpers import get_param_name_by_id, get_value_name_by_id
from itertools import product


def value_axis_metadata(params):
    entries = []
    label_by_value_id = {}
    value_name_counts = {}

    for param in params:
        param_id = param["param_id"]
        param_name = param["param_name"]
        for value in param["values"]:
            value_id = value["value_id"]
            value_name = value["value_name"]
            value_name_counts[value_name] = value_name_counts.get(value_name, 0) + 1
            display_value_name = value_name
            if value_name_counts[value_name] > 1:
                display_value_name = f"{value_name} #{value_name_counts[value_name]}"

            label = (param_name, display_value_name)
            entries.append(
                {
                    "param_id": param_id,
                    "value_id": value_id,
                    "label": label,
                    "display_value_name": display_value_name,
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


def remove_pair_from_inconsistent_combinations(
    inconsistent_combinations,
    param_1_id,
    value_1_id,
    param_2_id,
    value_2_id,
):
    """Remove one pairwise relation from 2-parameter cartesian-product combinations.

    If a combination represents many pairs (A x B), removing one pair may require
    splitting that record into up to two records while keeping the same data format.
    """
    updated_combinations = []
    changed = False

    for combo in inconsistent_combinations:
        combo_vals = combo.get("combination_values", {})

        if (
            len(combo_vals) != 2
            or param_1_id not in combo_vals
            or param_2_id not in combo_vals
        ):
            updated_combinations.append(combo)
            continue

        values_1 = set(combo_vals[param_1_id])
        values_2 = set(combo_vals[param_2_id])

        if value_1_id not in values_1 or value_2_id not in values_2:
            updated_combinations.append(combo)
            continue

        changed = True

        values_1_without = values_1 - {value_1_id}
        values_2_without = values_2 - {value_2_id}

        # Branch 1: all pairs where param_1 uses any other value.
        if values_1_without:
            updated_combinations.append(
                {
                    "combination_id": combo["combination_id"],
                    "combination_values": {
                        param_1_id: sorted(values_1_without),
                        param_2_id: sorted(values_2),
                    },
                    "comment": combo.get("comment", ""),
                }
            )

        # Branch 2: pairs where param_1 keeps value_1 but param_2 drops value_2.
        if values_2_without:
            updated_combinations.append(
                {
                    "combination_id": str(uuid4()),
                    "combination_values": {
                        param_1_id: [value_1_id],
                        param_2_id: sorted(values_2_without),
                    },
                    "comment": combo.get("comment", ""),
                }
            )

    return updated_combinations, changed


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
        selection = st.dataframe(
            filled_cc_matrix,
            height="content",
            selection_mode="multi-cell",
            on_select="rerun",
        )
        entries, _ = value_axis_metadata(st.session_state.params)
        row_label_to_ids = {
            entry["label"]: (entry["param_id"], entry["value_id"])
            for entry in entries
        }
        display_value_name_to_ids = {
            entry["display_value_name"]: (entry["param_id"], entry["value_id"], entry["label"])
            for entry in entries
        }
        cells = selection["selection"]["cells"]
        selected_combinations = []
        if len(cells) > 0:
            for cell in cells:
                row_idx = cell[0]
                # Identify param_id and value_id based on row index
                row_label = filled_cc_matrix.index[row_idx]
                param_1_id, value_1_id = row_label_to_ids.get(row_label, (None, None))
                param_1_name = param_name_by_id.get(param_1_id, f"Ukjent parameter ({param_1_id})")
                value_1_name = value_name_by_id.get(value_1_id, f"Ukjent verdi ({value_1_id})")

                display_value_2_name = cell[1]
                # Identify param_id and value_id based on display value name
                param_2_id, value_2_id, col_label = display_value_name_to_ids.get(display_value_2_name, (None, None, None))
                param_2_name = param_name_by_id.get(param_2_id, f"Ukjent parameter ({param_2_id})")
                value_2_name = value_name_by_id.get(value_2_id, f"Ukjent verdi ({value_2_id})")

                # Get inconsistency value
                value = filled_cc_matrix.loc[row_label, col_label]

                if param_1_id != param_2_id:
                    selected_combinations.append({
                        "param_1": {"id": param_1_id, "name": param_1_name},
                        "value_1": {"id": value_1_id, "name": value_1_name},
                        "param_2": {"id": param_2_id, "name": param_2_name},
                        "value_2": {"id": value_2_id, "name": value_2_name},
                        "inconsistent": value,
                    })
        selected_inconsistencies = [
            combo for combo in selected_combinations if combo["inconsistent"]
        ]
        selected_consistencies = [
            combo for combo in selected_combinations if not combo["inconsistent"]
        ]

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True, height=300):
                st.markdown("**Valgte konsistente kombinasjoner:**")
                if len(selected_consistencies) > 0:
                    for combo in selected_consistencies:
                        st.markdown(
                            f":blue-badge[{combo['param_1']['name']} = {combo['value_1']['name']}]"
                            " <-> "
                            f":blue-badge[{combo['param_2']['name']} = {combo['value_2']['name']}]"
                        )
                    comment = st.text_input(
                        "Kommentar",
                        placeholder="Skriv inn kommentar",
                        label_visibility="collapsed",
                        key="pairwise_inconsistency_comment",
                    )
                    register_button = st.button(
                        "Registrer inkonsistens",
                        key="register_pairwise_inconsistency",
                    )
                    if register_button:
                        for combo in selected_consistencies:
                            combination_values = {
                                combo["param_1"]["id"]: [combo["value_1"]["id"]],
                                combo["param_2"]["id"]: [combo["value_2"]["id"]],
                            }
                            st.session_state.inconsistent_combinations.append(
                                {
                                    "combination_id": str(uuid4()),
                                    "combination_values": combination_values,
                                    "comment": comment.strip(),
                                }
                            )
                        st.rerun()
                else:
                    st.caption("Ingen valgte.")

        with col2:
            with st.container(border=True, height=300):
                st.markdown("**Valgte inkonsistente kombinasjoner:**")
                if len(selected_inconsistencies) > 0:
                    for combo in selected_inconsistencies:
                        st.markdown(
                            f":blue-badge[{combo['param_1']['name']} = {combo['value_1']['name']}]"
                            " <-> "
                            f":blue-badge[{combo['param_2']['name']} = {combo['value_2']['name']}]"
                        )
                    remove_button = st.button(
                        "Fjern inkonsistens",
                        key="remove_pairwise_inconsistency",
                    )
                    if remove_button:
                        has_changes = False
                        updated = st.session_state.inconsistent_combinations
                        for combo in selected_inconsistencies:
                            updated, changed = remove_pair_from_inconsistent_combinations(
                                updated,
                                combo["param_1"]["id"],
                                combo["value_1"]["id"],
                                combo["param_2"]["id"],
                                combo["value_2"]["id"],
                            )
                            has_changes = has_changes or changed

                        if has_changes:
                            st.session_state.inconsistent_combinations = updated
                            st.rerun()
                else:
                    st.caption("Ingen valgte.")
        

        st.session_state.inconsistent_combinations_df = table_df
