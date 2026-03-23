import streamlit as st
from uuid import uuid4

def params_and_values():
    hcol1, hcol2 = st.columns([1, 1])
    hcol1.subheader("Parametere")
    hcol2.subheader("Verdier")
    if not st.session_state.params:
        st.info("Ingen parametere lagt til.")
    else:
        for param_idx, param in enumerate(st.session_state.params):
            col1, col2 = st.columns([1, 1])
            param_name_key = f"param_name_{param['param_id']}"
            if param_name_key not in st.session_state:
                st.session_state[param_name_key] = param["param_name"]
            with col1:
                pcol1, pcol2 = st.columns([3, 1])
                new_param_name = pcol1.text_input(
                    "Parameternavn",
                    key=param_name_key,
                    label_visibility="collapsed",
                )
                st.session_state.params[param_idx]["param_name"] = new_param_name
                if pcol2.button("Slett", key=f"delete_param_{param['param_id']}"):
                    # Implement later: Remove constraints involving this parameter
                    st.session_state.params.pop(param_idx)
                    st.rerun()
            with col2:
                if len(param["values"]) == 0:
                    st.info("Ingen verdier lagt til for denne parameteren.")
                else:
                    for value_idx, value in enumerate(param["values"]):
                        vcol1, vcol2 = st.columns([3, 1])
                        value_name_key = f"value_name_{param['param_id']}_{value['value_id']}"
                        if value_name_key not in st.session_state:
                            st.session_state[value_name_key] = value["value_name"]
                        new_value_name = vcol1.text_input(
                            "Verdi",
                            key=value_name_key,
                            label_visibility="collapsed",
                        )
                        st.session_state.params[param_idx]["values"][value_idx]["value_name"] = new_value_name
                        if vcol2.button("Slett", key=f"delete_value_{param['param_id']}_{value['value_id']}"):
                            # Implement later: Remove constraints involving this value
                            st.session_state.params[param_idx]["values"].pop(value_idx)
                            st.rerun()
                with st.form(f"values_form_{param['param_id']}", clear_on_submit=True, border=False):
                    vform_col1, vform_col2 = st.columns([3, 1])
                    new_value_name = vform_col1.text_input(
                        "Ny verdi",
                        placeholder="Skriv inn verdi",
                        key=f"new_value_name_{param['param_id']}",
                        label_visibility="collapsed",
                    )
                    submit_value = vform_col2.form_submit_button("Legg til")
                    if submit_value:
                        value_name = new_value_name.strip()
                        if not value_name:
                            st.warning("Vennligst angi en verdi.")
                        else:
                            existing_value_names = {
                                v["value_name"].strip().lower() for v in param["values"]
                            }
                            if value_name.lower() in existing_value_names:
                                st.warning(f"Duplikate verdier er ikke tillatt. *{value_name}* finnes allerede for denne parameteren.")
                            else:
                                new_value = {
                                    "value_id": str(uuid4()),
                                    "value_name": value_name,
                                }
                                st.session_state.params[param_idx]["values"].append(new_value)
                                st.rerun()
            st.divider()
    col1, col2 = st.columns([1, 1])
    with col1.form("params_form", clear_on_submit=True, border=False):
        pform_col1, pform_col2 = st.columns([3, 1])
        new_param_name = pform_col1.text_input(
            "Ny parameter",
            placeholder="Skriv inn parameternavn",
            label_visibility="collapsed",
        )
        submit_param = pform_col2.form_submit_button("Legg til")
        if submit_param:
            param_name = new_param_name.strip()
            if not param_name:
                st.warning("Vennligst angi et parameternavn.")
            else:
                existing_param_names = {
                    p["param_name"].strip().lower() for p in st.session_state.params
                }
                if param_name.lower() in existing_param_names:
                    st.warning(f"Duplikate parameternavn er ikke tillatt. *{param_name}* finnes allerede.")
                else:
                    new_param = {
                        "param_id": str(uuid4()),
                        "param_name": param_name,
                        "values": [],
                    }
                    st.session_state.params.append(new_param)
                    st.rerun()