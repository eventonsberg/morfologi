import streamlit as st
import pandas as pd
from classification_calculation import (
    compute_formal_concepts,
    compute_edges,
    compute_attribute_frequencies,
    compute_persistence,
    rescale_persistence_0_1,
    abstraction_loss,
    select_portfolio,
    transform_nodes_to_graphviz,
    transform_edges_to_graphviz,
    generate_graphviz_legend
)
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
    update_possible_combinations_with_combination_class_names,
)

def classification():
    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner.")
        return
    
    possible_combinations = st.session_state.possible_combinations

    classification_params = st.session_state.classification_params

    with st.form("classification_params_form"):
        tau = st.slider(
            "Minste tillatte konseptverdi",
            min_value=0.00,
            max_value=1.00,
            value=float(classification_params.get("persistence_threshold", 0.00)),
            step=0.01
        )
        epsilon = st.slider(
            "Maksimalt tillatt overlapp mellom klasser",
            min_value=0.00,
            max_value=1.00,
            value=float(classification_params.get("overlap_epsilon", 0.00)),
            step=0.01
        )
        alpha = st.slider(
            "Minste tillatte antall kombinasjoner i en klasse",
            min_value=1,
            max_value=len(possible_combinations),
            value=min(int(classification_params.get("min_class_size", 2)), len(possible_combinations)),
            step=1
        )
        patch_uncovered = st.checkbox(
            "Legg til klasser for enkeltkombinasjoner som ikke er dekket",
            value=classification_params.get("patch_uncovered", True)
        )
        generate_concepts_graph = st.checkbox(
            "Generer konseptvisualisering :gray[- Ikke anbefalt hvis] :gray-badge[Mulige kombinasjoner > 100]",
            value=False
        )
        update_classification = st.form_submit_button("Oppdater klassifisering", type="primary")

    if update_classification:
        st.session_state.classification_params = {
            "persistence_threshold": tau,
            "overlap_epsilon": epsilon,
            "min_class_size": alpha,
            "patch_uncovered": patch_uncovered,
        }
        configurations = {}
        for combination in possible_combinations:
            config = {f"{param_id}": value_id
                    for param_id, value_id in combination["combination_values"].items()}
            configurations[frozenset(combination["combination_values"].items())] = config
        concepts = compute_formal_concepts(configurations)
        edges = compute_edges(concepts)
        
        attribute_frequencies = compute_attribute_frequencies(concepts)
        persistence = compute_persistence(concepts, edges, attribute_frequencies)
        persistence = rescale_persistence_0_1(persistence)
        params = {
            "persistence_threshold": tau,
            "overlap_epsilon": epsilon,
            "min_class_size": alpha,
            "patch_uncovered": patch_uncovered,
        }
        selected_concepts = select_portfolio(concepts, persistence, params)
        st.session_state.selected_concept_intents = set(
            tuple(sorted(concepts[concept_name]["intent"]))
            for concept_name in selected_concepts
        )

        if generate_concepts_graph:
            edge_losses = {
                (child, parent): abstraction_loss(
                    concepts[child],
                    concepts[parent],
                    attribute_frequencies
                )
                for child, parent in edges
            }
            edge_losses = rescale_persistence_0_1(edge_losses)
            graphviz_nodes = transform_nodes_to_graphviz(
                concepts,
                selected_concepts=selected_concepts,
                concept_scores=persistence,
            )
            graphviz_edges = transform_edges_to_graphviz(edges, edge_losses)
            st.session_state.concepts_graph = f"""
                digraph G {{
                    rankdir=LR;
                    ranksep=1.5;
                    node [fontsize=10];
                    {graphviz_nodes}
                    {graphviz_edges}
                }}
            """
        else:
            st.session_state.concepts_graph = ""

        update_possible_combinations_with_combination_class_names(
            st.session_state.possible_combinations,
            st.session_state.concepts,
            st.session_state.selected_concept_intents,
        )
        st.rerun()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.header("Kombinasjonsklasser")
    col2.metric(
        "Klasser",
        len(st.session_state.selected_concept_intents),
        delta=f"{len(st.session_state.concepts)} konsepter",
        delta_color="off",
        delta_arrow="off",
    )
    not_classified_count = sum(
        1
        for combination in st.session_state.possible_combinations
        if not combination.get("combination_class_names", [])
    )
    col3.metric(
        "Uklassifiserte kombinasjoner",
        not_classified_count,
    )

    if not st.session_state.concepts:
        st.info("Klikk på 'Oppdater klassifisering' for å beregne kombinasjonsklasser.")
        return
    param_columns = [param["param_name"] for param in st.session_state.params]
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    class_number = 1
    concept_name_changed = False
    for concept_intent_tuple, concept_name_and_extent in st.session_state.concepts.items():
        if concept_intent_tuple in st.session_state.selected_concept_intents:
            st.subheader(f"Klasse {class_number}")
            concept_widget_key = "concept_name_" + ("|".join(concept_intent_tuple) if concept_intent_tuple else "__no_intent__")
            current_name = concept_name_and_extent["name"]
            col1, col2 = st.columns([5, 1], vertical_alignment="center")
            concept_name_input = col1.text_input(
                "Klassenavn",
                value=current_name,
                key=concept_widget_key,
                label_visibility="collapsed",
            )
            if concept_name_input != current_name:
                concept_name_changed = True
                st.session_state.concepts[concept_intent_tuple]["name"] = concept_name_input
            combination_frozensets = concept_name_and_extent["extent"]
            n_combinations = len(combination_frozensets)
            col2.markdown(f":blue[**{n_combinations} kombinasjon" + ("" if n_combinations == 1 else "er") + "**]")

            # Display combinations in this concept
            combinations = []
            for combination in possible_combinations:
                if frozenset(combination["combination_values"].items()) in combination_frozensets:
                    combination_values = combination["combination_values"]
                    row = {
                        param_name_by_id[param_id]: value_name_by_id[value_id]
                        for param_id, value_id in combination_values.items()
                    }
                    row["Kombinasjon nr."] = combination["combination_number"]
                    combinations.append(row)
            combination_df = pd.DataFrame(
                combinations,
                columns=["Kombinasjon nr."] + param_columns,
            )
            combination_df = combination_df.set_index("Kombinasjon nr.")
            st.dataframe(combination_df)
            caption = ":small[:gray[Egenskaper: ]]"
            for intent in concept_intent_tuple:
                param_id, value_id = intent.split(" = ")
                param_name = param_name_by_id.get(param_id, f"Param {param_id}")
                value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
                caption += f":gray-badge[{param_name} = {value_name}] "
            st.markdown(caption)

            class_number += 1

    if concept_name_changed:
        st.rerun()

    if st.session_state.concepts_graph:
        st.divider()
        st.header("Konsepter (mulige kombinasjonsklasser)")
        st.graphviz_chart(st.session_state.concepts_graph)
        st.graphviz_chart(generate_graphviz_legend())
        st.download_button(
            "Last ned konseptvisualisering (.dot)",
            data=st.session_state.concepts_graph,
            icon=":material/download:",
            file_name="concepts_graph.dot",
            mime="text/vnd.graphviz",
            help="Dette filformatet kan åpnes med verktøy som Graphviz Online"
        )