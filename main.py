import streamlit as st
import pandas as pd
from params_and_values import params_and_values
from inconsistent_combinations import inconsistent_combinations
from possible_combinations import possible_combinations
from descriptions import descriptions
from classification import classification
from helpers import (
    get_possible_combinations,
    update_possible_combinations_with_combination_class_names,
)
from export_to_excel import export_to_excel
from import_from_excel import import_from_excel

st.set_page_config(
    page_title="Morfologi",
    page_icon=":material/metro:",
    layout="wide",
    menu_items={
        "Report a bug": "mailto:evton@ffi.no; torgeir.aambo@ffi.no",
        "About": """
            Dette morfologi-verktøyet er utviklet av Even K. Tønsberg og Torgeir Aambø ved Forsvarets forskningsinstitutt (FFI).  
              
            Verktøyet er under stadig utvikling.
            Finner du en feil eller har forslag til forbedringer, vennligst ta kontakt via :blue-badge[Report a bug] i menyen oppe til høyre.
        """
    }
)

if "params" not in st.session_state:
    # params: list of dicts: {param_id, param_name, param_description, values: [{value_id, value_name, value_description}, ...]}
    st.session_state.params = []
if "n_combinations" not in st.session_state:
    # n_combinations: [possible_combinations, prev_possible_combinations]
    st.session_state.n_combinations = [0, 0]
if "inconsistent_combinations" not in st.session_state:
    # inconsistent_combinations: list of dicts: {combination_id, combination_values: {param_id: [value_id, ...]}, comment}
    st.session_state.inconsistent_combinations = []
if "inconsistent_combinations_df" not in st.session_state:
    st.session_state.inconsistent_combinations_df = pd.DataFrame()
if "possible_combinations" not in st.session_state:
    # possible_combinations: list of dicts: {combination_number, combination_values: {param_id: value_id, ...}, combination_class_names: [combination_class_name, ...]}
    st.session_state.possible_combinations = []
if "possible_combinations_df" not in st.session_state:
    st.session_state.possible_combinations_df = pd.DataFrame()
if "concepts" not in st.session_state:
    # concepts = {
    #   concept_intent_tuple: {
    #     "name": concept_name,
    #     "extent": {
    #       frozenset({(param_id: value_id), ...}),
    #       ...
    #     },
    #     "value": concept_value
    #   },
    #   ...
    # }
    st.session_state.concepts = {}
if "selected_concept_intents" not in st.session_state:
    # selected_concept_intents: set of concept_intent_tuple
    st.session_state.selected_concept_intents = set()
if "concepts_graph" not in st.session_state:
    # concepts_graph: graphviz graph object
    st.session_state.concepts_graph = ""
if "classification_params" not in st.session_state:
    # classification_params: dict of {param_name: param_value}
    st.session_state.classification_params = {}

st.session_state.possible_combinations = get_possible_combinations(
    st.session_state.params,
    st.session_state.inconsistent_combinations,
)
update_possible_combinations_with_combination_class_names(
    st.session_state.possible_combinations,
    st.session_state.concepts,
    st.session_state.selected_concept_intents,
)

current_n_combinations = len(st.session_state.possible_combinations)
if current_n_combinations != st.session_state.n_combinations[0]:
    st.session_state.n_combinations[1] = st.session_state.n_combinations[0]
    st.session_state.n_combinations[0] = current_n_combinations

pg = st.navigation([
    st.Page(params_and_values, title="Parametere og verdier", icon=":material/tune:"),
    st.Page(descriptions, title="Beskrivelser", icon=":material/description:"),
    st.Page(inconsistent_combinations, title="Inkonsistente kombinasjoner", icon=":material/block:"),
    st.Page(possible_combinations, title="Mulige kombinasjoner", icon=":material/table:"),
    st.Page(classification, title="Klassifisering", icon=":material/category:"),
], position="top")

with st.sidebar:
    st.metric(
        "Mulige kombinasjoner",
        st.session_state.n_combinations[0],
        delta=st.session_state.n_combinations[0] - st.session_state.n_combinations[1],
    )
    st.divider()
    export_to_excel()
    st.divider()
    import_from_excel()

pg.run()
