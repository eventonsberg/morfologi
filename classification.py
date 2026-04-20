import streamlit as st
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

# ----- MAIN FUNCTION -----

def classification():
    possible_combinations = st.session_state.possible_combinations

    configurations = {}
    for idx, combination in enumerate(possible_combinations):
        config = {f"{param_id}": value_id
                  for param_id, value_id in combination["combination_values"].items()}
        configurations[f"combination_{idx}"] = config
    concepts = compute_formal_concepts(configurations)
    edges = compute_edges(concepts)
    
    attribute_frequencies = compute_attribute_frequencies(concepts)
    persistence = compute_persistence(concepts, edges, attribute_frequencies)
    params = {
        "persistence_threshold": 0,
        "overlap_epsilon": 0,
    }
    selected_concepts = select_portfolio(concepts, persistence, params)

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


