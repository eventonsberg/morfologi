import streamlit as st

def descriptions():
    if not st.session_state.params:
        st.info("Ingen parametere lagt til.")
        return

    for param in st.session_state.params:
        with st.expander(f"**{param['param_name']}**"):
            param_description_key = f"param_desc_{param['param_id']}"
            new_param_desc = st.text_area(
                "Beskrivelse",
                value=param["param_description"],
                placeholder="Angi parameterbeskrivelse...",
                key=param_description_key,
                label_visibility="collapsed",
            )
            param["param_description"] = new_param_desc

            if param["values"]:
                for value in param["values"]:
                    vcol1, vcol2 = st.columns([1, 4])
                    vcol1.markdown(f"**{value['value_name']}**")
                    value_description_key = f"value_desc_{value['value_id']}"
                    new_value_desc = vcol2.text_area(
                        "Beskrivelse",
                        value=value["value_description"],
                        placeholder="Angi verdibeskrivelse...",
                        key=value_description_key,
                        label_visibility="collapsed",
                    )
                    value["value_description"] = new_value_desc
