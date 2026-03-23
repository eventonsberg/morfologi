import streamlit as st
from params_and_values import params_and_values
from inconsistent_combinations import inconsistent_combinations
from possible_combinations import possible_combinations

st.set_page_config(page_title="Morfologi")
st.title("Morfologi")

if "params" not in st.session_state:
    # params: list of dicts: {param_id, param_name, values: [{value_id, value_name}, ...]}
    st.session_state.params = []

tab1, tab2, tab3 = st.tabs(["Parametere og verdier", "Inkonsistente kombinasjoner", "Mulige kombinasjoner"])

with tab1:
    params_and_values()

with tab2:
    inconsistent_combinations()

with tab3:
    possible_combinations()

#st.write(st.session_state.params)