import streamlit as st
import pandas as pd
from urllib.parse import quote
from classification_calculation import (
    compute_formal_concepts,
    sync_concept_register,
    compute_edges,
    compute_attribute_frequencies,
    weighted_abstraction_loss,
    compute_persistence,
    rescale_persistence_0_1,
    generate_concept_score_df,
    transform_nodes_to_graphviz,
    transform_edges_to_graphviz,
    transform_ranks_to_graphviz,
    generate_graphviz_legend,
)
from classification_optimization import compute_optimal_selection, build_score_history_chart
from helpers import (
    get_param_name_by_id,
    get_value_name_by_id,
    update_possible_combinations_with_combination_class_names,
)

def classification():
    pending_classification_toast = st.session_state.pop("pending_classification_toast", False)
    if pending_classification_toast:
        st.toast(
            "Ingen konsepter oppfyller klassekriteriene. Juster klassifiseringsparametrene.",
            icon=":material/warning:",
            duration="long"
        )

    if st.session_state.n_combinations[0] == 0:
        st.info("Ingen mulige kombinasjoner.")
        return
    elif st.session_state.n_combinations[0] <= 2:
        st.info("Flere kombinasjoner kreves for å kunne klassifisere.")
        return
    
    possible_combinations = st.session_state.possible_combinations

    classification_params = st.session_state.classification_params

    with st.form("classification_params_form"):
        st.markdown(
            "**Parametervekter**",
            help="Juster parametervektene hvis du ønsker å prioritere visse egenskaper under klassifiseringen."
        )
        param_weights = {}
        for param in st.session_state.params:
            param_id = param["param_id"]
            param_name = param["param_name"]
            param_weights[param_id] = st.slider(
                param_name,
                min_value=0.00,
                max_value=1.00,
                value=float(classification_params.get(param_id, 0.50)),
                step=0.01
            )
        st.markdown(
            "**Innstillinger for klassifisering**",
        )
        param_weights["optimization_strategy"] = st.segmented_control(
            "Optimeringsstrategi",
            options=["Høyest gjennomsnittsscore", "Høyest totalscore"],
            default=classification_params.get("optimization_strategy", "Høyest gjennomsnittsscore"),
            required=True,
        )
        param_weights["max_classes"] = st.number_input(
            "Maksimalt antall klasser",
            min_value=2,
            value=int(classification_params.get("max_classes", 10)),
            step=1
        )
        update_classification = st.form_submit_button("Oppdater klassifisering", type="primary")

    if update_classification:
        score_plot_placeholder = st.empty()
        score_history = []
        st.session_state.classification_params = {
            f"{param_id}": weight
            for param_id, weight in param_weights.items()
            if param_id != "optimization_strategy" and param_id != "max_classes"
        }
        st.session_state.classification_params["optimization_strategy"] = param_weights["optimization_strategy"]
        st.session_state.classification_params["max_classes"] = param_weights["max_classes"]
        configurations = {}
        for combination in possible_combinations:
            config = {f"{param_id}": value_id
                    for param_id, value_id in combination["combination_values"].items()}
            configurations[frozenset(combination["combination_values"].items())] = config
        concepts = compute_formal_concepts(configurations)
        st.session_state.listed_concepts = {
            intent_tuple: list_state
            for intent_tuple, list_state in st.session_state.get("listed_concepts", {}).items()
            if intent_tuple in concepts and list_state in ("red", "green")
        }
        st.session_state.n_concepts = len(concepts)
        edges = compute_edges(concepts)
        attribute_frequencies = compute_attribute_frequencies(concepts)
        raw_persistence = compute_persistence(concepts, attribute_frequencies)
        raw_edge_losses = {
            (child, parent): weighted_abstraction_loss(
                concepts[child],
                concepts[parent],
                attribute_frequencies,
                st.session_state.classification_params,
            )
            for child, parent in edges
        }

        shared_values = [
            value
            for value in list(raw_persistence.values()) + list(raw_edge_losses.values())
            if value is not None
        ]
        shared_min = min(shared_values) if shared_values else None
        shared_max = max(shared_values) if shared_values else None

        persistence = rescale_persistence_0_1(raw_persistence, min_value=shared_min, max_value=shared_max)
        edge_losses = rescale_persistence_0_1(raw_edge_losses, min_value=shared_min, max_value=shared_max)
        best_solution = compute_optimal_selection(
            concepts,
            persistence,
            optimization_strategy=st.session_state.classification_params["optimization_strategy"],
            max_classes=st.session_state.classification_params["max_classes"],
            listed_concepts=st.session_state.listed_concepts,
            score_plot_placeholder=score_plot_placeholder,
            score_history_output=score_history,
        )
        st.session_state.optimal_score_history = score_history
        selected_concepts = best_solution["selection"] if best_solution else []
        if len(selected_concepts) == 0:
            st.session_state.pending_classification_toast = True
        st.session_state.selected_concept_intents = set(
            tuple(sorted(concepts[concept_name]["intent"]))
            for concept_name in selected_concepts
        )
        sync_concept_register(concepts, persistence)
        concept_labels = {}
        concept_number = 0
        for intent_tuple in concepts.keys():
            if intent_tuple in st.session_state.concepts:
                concept_labels[intent_tuple] = st.session_state.concepts[intent_tuple]["name"]
            else:
                concept_number += 1
                concept_labels[intent_tuple] = f"_konsept_{concept_number}"
        st.session_state.concept_score_df = generate_concept_score_df(concepts, persistence, concept_labels)
        graphviz_nodes = transform_nodes_to_graphviz(
            concepts,
            selected_concepts=selected_concepts,
            concept_scores=persistence,
            concept_labels=concept_labels,
            listed_concepts=st.session_state.listed_concepts,
        )
        graphviz_ranks = transform_ranks_to_graphviz(concepts)
        graphviz_edges = transform_edges_to_graphviz(edges, edge_losses)
        st.session_state.concepts_graph = f"""
            digraph G {{
                rankdir=LR;
                ranksep=1.5;
                node [fontsize=10];
                {graphviz_nodes}
                {graphviz_ranks}
                {graphviz_edges}
            }}
        """

        update_possible_combinations_with_combination_class_names(
            st.session_state.possible_combinations,
            st.session_state.concepts,
            st.session_state.selected_concept_intents,
        )
        st.rerun()

    stored_score_history = st.session_state.get("optimal_score_history", [])
    if stored_score_history:
        history_chart = build_score_history_chart(stored_score_history)
        if history_chart is not None:
            st.altair_chart(history_chart)
    
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    col1.header("Kombinasjonsklasser")
    col2.metric(
        "Klasser",
        len(st.session_state.selected_concept_intents),
    )
    col3.metric(
        "Konsepter",
        int(st.session_state.get("n_concepts", 0)),
    )
    not_classified_count = sum(
        1
        for combination in st.session_state.possible_combinations
        if not combination.get("combination_class_names", [])
    )
    col4.metric(
        "Uklassifisert",
        not_classified_count,
    )

    if st.session_state.get("n_concepts", 0) == 0:
        st.info("Klikk på 'Oppdater klassifisering' for å beregne kombinasjonsklasser.")
        return
    elif len(st.session_state.selected_concept_intents) == 0:
        st.info("Ingen klasser.")
    param_columns = [param["param_name"] for param in st.session_state.params]
    param_name_by_id = get_param_name_by_id(st.session_state.params)
    value_name_by_id = get_value_name_by_id(st.session_state.params)
    concept_name_changed = False
    concept_name_updates = {}
    for concept_intent_tuple, concept_info in st.session_state.concepts.items():
        if concept_intent_tuple in st.session_state.selected_concept_intents:
            concept_widget_key = "concept_name_" + ("|".join(concept_intent_tuple) if concept_intent_tuple else "__no_intent__")
            current_name = concept_info["name"]
            concept_name_input = st.text_input(
                "Klassenavn",
                value=current_name,
                key=concept_widget_key,
                label_visibility="collapsed",
            )
            if concept_name_input != current_name:
                concept_name_changed = True
                st.session_state.concepts[concept_intent_tuple]["name"] = concept_name_input
                concept_name_updates[concept_intent_tuple] = concept_name_input
            combination_frozensets = concept_info["extent"]

            caption = ":small[:gray[Kombinasjoner: ]]"
            n_combinations = len(combination_frozensets)
            caption += f" :blue-badge[{n_combinations}]"
            if concept_info["value"] is not None:
                caption += " :small[:gray[Konseptverdi: ]]"
                caption += f" :blue-badge[{concept_info['value']:.2f}]"
            caption += " :small[:gray[Egenskaper: ]]"
            for intent in concept_intent_tuple:
                param_id, value_id = intent.split(" = ")
                param_name = param_name_by_id.get(param_id, f"Param {param_id}")
                value_name = value_name_by_id.get(value_id, f"Verdi {value_id}")
                caption += f" :blue-badge[{param_name} = {value_name}] "
            st.markdown(caption)

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
            st.dataframe(combination_df, height="content")
            st.divider()

    if st.session_state.concepts_graph:
        st.header("Konseptvisualisering")
        graphviz_url = "https://dreampuf.github.io/GraphvizOnline/#" + quote(
            st.session_state.concepts_graph,
            safe=""
        )
        st.link_button(
            "Åpne konseptvisualisering i Graphviz Online",
            graphviz_url,
            icon=":material/open_in_new:"
        )
        st.download_button(
            "Last ned konseptvisualisering (.dot)",
            data=st.session_state.concepts_graph,
            icon=":material/download:",
            file_name="concepts_graph.dot",
            mime="text/vnd.graphviz",
            help="Dette filformatet kan åpnes i *Graphviz Online*"
        )
        if st.button(
            "Generer konseptvisualisering",
            icon=":material/visibility:",
            help="Genereringen vil være tidkrevende ved mange konsepter",
        ):
            st.graphviz_chart(st.session_state.concepts_graph)
            st.graphviz_chart(generate_graphviz_legend())
    
    concept_score_df = st.session_state.get("concept_score_df", None)
    concept_list_changed = False
    if concept_score_df is not None:
        sorted_concept_score_df = concept_score_df.sort_values(by="Konseptverdi", ascending=False)
        st.divider()
        st.header("Konsepter")
        edited_concepts = st.data_editor(
            sorted_concept_score_df,
            hide_index=True,
            column_config={
                "Konsept": st.column_config.TextColumn(disabled=True),
                "Kombinasjoner": st.column_config.NumberColumn(disabled=True),
                "Konseptverdi": st.column_config.NumberColumn(disabled=True),
                "Egenskaper": st.column_config.ListColumn(disabled=True),
                "Liste": st.column_config.SelectboxColumn(
                    options=[
                        "🟥 RØD",
                        "🟩 GRØNN",
                    ],
                ),
                "_intent_tuple": None,
            }
        )
        st.caption(
            "Konsepter som er :red-badge[RØD]-listet kan ikke være en del av klasseutvalget. " \
            "Konsepter som er :green-badge[GRØNN]-listet må være en del av klasseutvalget." 
        )
        for idx, row in edited_concepts.iterrows():
            intent_tuple = row["_intent_tuple"]
            list_value = row["Liste"]
            if list_value == "🟥 RØD":
                new_list_state = "red"
            elif list_value == "🟩 GRØNN":
                new_list_state = "green"
            else:
                new_list_state = None

            current_list_state = st.session_state.listed_concepts.get(intent_tuple)

            if current_list_state != new_list_state:
                if new_list_state is None:
                    st.session_state.listed_concepts.pop(intent_tuple, None)
                else:
                    st.session_state.listed_concepts[intent_tuple] = new_list_state
                concept_list_changed = True

    if concept_name_changed or concept_list_changed:
        concept_score_df = st.session_state.get("concept_score_df")
        if concept_score_df is not None and not concept_score_df.empty:
            updated_concept_score_df = concept_score_df.copy()

            if concept_name_changed and "_intent_tuple" in updated_concept_score_df.columns:
                for concept_intent_tuple, concept_name in concept_name_updates.items():
                    concept_mask = updated_concept_score_df["_intent_tuple"] == concept_intent_tuple
                    updated_concept_score_df.loc[concept_mask, "Konsept"] = concept_name

            if concept_list_changed and "_intent_tuple" in updated_concept_score_df.columns:
                for concept_intent_tuple in updated_concept_score_df["_intent_tuple"]:
                    concept_mask = updated_concept_score_df["_intent_tuple"] == concept_intent_tuple
                    concept_list_value = st.session_state.listed_concepts.get(concept_intent_tuple)
                    updated_concept_score_df.loc[concept_mask, "Liste"] = (
                        "🟥 RØD" if concept_list_value == "red"
                        else "🟩 GRØNN" if concept_list_value == "green"
                        else None
                    )

            st.session_state.concept_score_df = updated_concept_score_df
        st.rerun()
