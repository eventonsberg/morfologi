import streamlit as st
from params_and_values import params_and_values
from inconsistent_combinations import inconsistent_combinations
from possible_combinations import possible_combinations
from helpers import get_possible_combinations

st.set_page_config(
    page_title="Morfologi",
    page_icon=":material/metro:",
    initial_sidebar_state="collapsed",
    layout="wide",
    menu_items={
        "Report a bug": "mailto:Even-Kristian.Tonsberg@ffi.no; Torgeir.Aambo@ffi.no",
        "About": """
            Dette morfologi-verktøyet er utviklet av Even K. Tønsberg og Torgeir Aambø ved Forsvarets forskningsinstitutt (FFI).  
              
            Verktøyet er under stadig utvikling.
            Finner du en feil eller har forslag til forbedringer, vennligst ta kontakt via :blue-badge[Report a bug] i menyen oppe til høyre.
        """
    }
)

if "params" not in st.session_state:
    # params: list of dicts: {param_id, param_name, values: [{value_id, value_name}, ...]}
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

tab1, tab2, tab3 = st.tabs(["Parametere og verdier", "Inkonsistente kombinasjoner", "Mulige kombinasjoner"])

with tab1:
    params_and_values()

with tab2:
    inconsistent_combinations()

with tab3:
    possible_combinations()






with st.sidebar:
    st.markdown(
        """
        TODO:
        - Fjerne tilhørende inkonsistente kombinasjoner ved sletting av parametere og verdier
        - Gjøre det umulig å legge til inkonsistente kombinasjoner som er dekket av allerede registrerte inkonsistente kombinasjoner
        - Funksjonalitet for å importere og eksportere data
        - Funksjonalitet for å definere klasser av kombinasjoner
        - Funksjonalitet for å legge til beskrivelser av parametere og verdier
        """
    )