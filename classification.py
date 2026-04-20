import streamlit as st
import pandas as pd
from classification_calculation import (
    compute_formal_concepts,
    compute_edges,
    compute_attribute_frequencies,
    compute_persistence,
    abstraction_loss,
    select_portfolio,
    transform_nodes_to_graphviz,
    transform_edges_to_graphviz,
    generate_graphviz_legend
)
from helpers import get_param_name_by_id, get_value_name_by_id

def classification():
    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner.")
        return
    
    possible_combinations = st.session_state.possible_combinations

    if True: #st.button("Oppdater klassifisering"):
        configurations = {}
        for combination in possible_combinations:
            config = {f"{param_id}": value_id
                    for param_id, value_id in combination["combination_values"].items()}
            configurations[combination['combination_number']] = config
        concepts = compute_formal_concepts(configurations)
        edges = compute_edges(concepts)
        
        attribute_frequencies = compute_attribute_frequencies(concepts)
        persistence = compute_persistence(concepts, edges, attribute_frequencies)
        params = {
            "persistence_threshold": 0,
            "overlap_epsilon": 0,
        }
        selected_concepts = select_portfolio(concepts, persistence, params)
        st.session_state.selected_concept_intents = set(
            tuple(sorted(concepts[concept_name]["intent"]))
            for concept_name in selected_concepts
        )
        
        st.header("Kombinasjonsklasser")
        class_number = 1
        concept_name_changed = False
        for concept_name, concept in concepts.items():
            concept_intent_tuple = tuple(sorted(concept["intent"]))
            if concept_intent_tuple in st.session_state.selected_concept_intents:
                st.subheader(f"Klasse {class_number}")
                concept_widget_key = "concept_name_" + ("|".join(concept_intent_tuple) if concept_intent_tuple else "__no_intent__")
                current_name = st.session_state.concepts.get(concept_intent_tuple, {"name": concept_name})["name"]
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
                combination_numbers = concept.get("extent", [])
                n_combinations = len(combination_numbers)
                col2.markdown(f":blue[**{n_combinations} kombinasjon" + ("er" if n_combinations == 1 else "er") + "**]")

                # Display combinations in this concept
                param_columns = [param["param_name"] for param in st.session_state.params]
                param_name_by_id = get_param_name_by_id(st.session_state.params)
                value_name_by_id = get_value_name_by_id(st.session_state.params)
                combinations = []
                for combination in possible_combinations:
                    if combination["combination_number"] in combination_numbers:
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
                class_number += 1

        if concept_name_changed:
            st.rerun()

        st.divider()
        st.header("Konseptvisualisering")
        edge_losses = {
            (child, parent): abstraction_loss(
                concepts[child],
                concepts[parent],
                attribute_frequencies
            )
            for child, parent in edges
        }
        graphviz_nodes = transform_nodes_to_graphviz(concepts, selected_concepts)
        graphviz_edges = transform_edges_to_graphviz(edges, edge_losses)
        st.graphviz_chart(f"""
            digraph G {{
                rankdir=LR;
                ranksep=1.5;
                node [fontsize=10];
                {graphviz_nodes}
                {graphviz_edges}
            }}
        """)
        st.graphviz_chart(generate_graphviz_legend())


