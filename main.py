import streamlit as st
from params_and_values import params_and_values
from inconsistent_combinations import inconsistent_combinations
from possible_combinations import possible_combinations
from descriptions import descriptions
from classification import classification
from helpers import get_possible_combinations
from export_to_excel import export_to_excel
from import_from_excel import import_from_excel

st.set_page_config(
    page_title="Morfologi",
    page_icon=":material/metro:",
    initial_sidebar_state="collapsed",
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
if "possible_combinations" not in st.session_state:
    # possible_combinations: list of dicts: {param_id: value_id, ...}
    st.session_state.possible_combinations = []
if "classification_rules" not in st.session_state:
    # classification_rules: list of dicts: {classification_rule_id, classification_rule_name, combination_values: {param_id: [value_id, ...]}}
    st.session_state.classification_rules = []
if "combination_classes" not in st.session_state:
    # combination_classes: list of dicts: {combination_class_id, combination_class_name, classification_rule_ids: [classification_rule_id, ...], number_of_combinations}
    st.session_state.combination_classes = []

st.session_state.possible_combinations = get_possible_combinations(
    st.session_state.params,
    st.session_state.inconsistent_combinations,
)

current_n_combinations = len(st.session_state.possible_combinations)
if current_n_combinations != st.session_state.n_combinations[0]:
    st.session_state.n_combinations[1] = st.session_state.n_combinations[0]
    st.session_state.n_combinations[0] = current_n_combinations

title_row = st.container(horizontal=True)
title_row.title("Morfologi")
title_row.metric(
    "Mulige kombinasjoner",
    st.session_state.n_combinations[0],
    delta=st.session_state.n_combinations[0] - st.session_state.n_combinations[1],
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Parametere og verdier",
    "Beskrivelser",
    "Inkonsistente kombinasjoner",
    "Mulige kombinasjoner",
    "Klassifisering"
])

with tab1:
    params_and_values()

with tab2:
    descriptions()

with tab3:
    inconsistent_combinations_df = inconsistent_combinations()

with tab4:
    possible_combinations_df = possible_combinations()

with tab5:
    classification_rules_df = classification()

with st.sidebar:
    export_to_excel(inconsistent_combinations_df, possible_combinations_df, classification_rules_df)
    st.divider()
    import_from_excel()
