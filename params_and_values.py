import streamlit as st
from uuid import uuid4

def params_and_values():
    n_params = len(st.session_state.params)
    if n_params:
        cols = st.columns(n_params)
        for param_idx, param in enumerate(st.session_state.params):
            with cols[param_idx]:
                param_name_key = f"param_name_{param['param_id']}"
                if param_name_key not in st.session_state:
                    st.session_state[param_name_key] = param["param_name"]
                pcol1, pcol2 = st.columns([3, 1], vertical_alignment="bottom")
                new_param_name = pcol1.text_input(
                    "Parameter",
                    key=param_name_key,
                )
                st.session_state.params[param_idx]["param_name"] = new_param_name
                if pcol2.button(
                    ":material/delete:",
                    type="tertiary",
                    key=f"delete_param_{param['param_id']}"
                ):
                    # TODO: Remove constraints involving this parameter
                    st.session_state.params.pop(param_idx)
                    st.rerun()
        cols = st.columns(n_params)
        for param_idx, param in enumerate(st.session_state.params):
            with cols[param_idx]:
                for value_idx, value in enumerate(param["values"]):
                    vcol1, vcol2 = st.columns([3, 1], vertical_alignment="bottom")
                    value_name_key = f"value_name_{param['param_id']}_{value['value_id']}"
                    if value_name_key not in st.session_state:
                        st.session_state[value_name_key] = value["value_name"]
                    new_value_name = vcol1.text_input(
                        "Verdi",
                        key=value_name_key,
                        label_visibility="collapsed" if value_idx > 0 else "visible",
                    )
                    st.session_state.params[param_idx]["values"][value_idx]["value_name"] = new_value_name
                    if vcol2.button(
                        ":material/delete:",
                        type="tertiary",
                        key=f"delete_value_{param['param_id']}_{value['value_id']}"
                    ):
                        # TODO: Remove constraints involving this value
                        st.session_state.params[param_idx]["values"].pop(value_idx)
                        st.rerun()
        st.divider()
        st.subheader("Legg til verdier")
        cols = st.columns(n_params)
        for param_idx, param in enumerate(st.session_state.params):
            with cols[param_idx]:
                with st.form(f"values_form_{param['param_id']}", clear_on_submit=True, border=False):
                    vform_col1, vform_col2 = st.columns([3, 1], vertical_alignment="bottom")
                    new_value_name = vform_col1.text_input(
                        param["param_name"],
                        placeholder="Skriv inn verdi",
                        key=f"new_value_name_{param['param_id']}",
                    )
                    submit_value = vform_col2.form_submit_button(":material/add_2:", type="tertiary")
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
    st.subheader("Legg til parametere")
    cols = st.columns(max(n_params, 1))
    with cols[0].form("params_form", clear_on_submit=True, border=False):
        pform_col1, pform_col2 = st.columns([3, 1])
        new_param_name = pform_col1.text_input(
            "Ny parameter",
            placeholder="Skriv inn parameternavn",
            label_visibility="collapsed",
        )
        submit_param = pform_col2.form_submit_button(":material/add_2:", type="tertiary")
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