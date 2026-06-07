import streamlit as st

st.set_page_config(
    page_title="Contact",
    layout="centered"
)

st.title("Contact")

st.markdown("""
Bei Fragen zum Projekt, zur Masterarbeit oder zu möglichen Einsatzszenarien können Sie mich über folgende Kanäle erreichen.
""")

with st.container(border=True):
    st.markdown("**📧 E-Mail**")
    st.markdown("thai-au.tran@outlook.com")

    st.markdown("**💻 GitHub**")
    st.markdown("[github.com/ThAu-Tr](https://github.com/ThAu-Tr)")

st.info("""
Quellcode und weitere projektspezifische Materialien können bei Bedarf über die oben genannten Kontaktkanäle angefragt werden.
""")