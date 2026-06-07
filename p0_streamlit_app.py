import streamlit as st

# Page Setup
home_page = st.Page(page="pages/p1_about.py", title="About", icon=":material/home:", default=True)
chat_page = st.Page(page="pages/p2_chat.py", title="Chat", icon=":material/smart_toy:")
#database_page = st.Page(page="pages/p3_database.py", title="Databases", icon=":material/database_upload:")
contact_page = st.Page(page="pages/p4_contact.py", title="Contact", icon=":material/contact_page:")

# Navigation Setup
pg = st.navigation(pages=[home_page,chat_page,contact_page])#database_page,contact_page])

# Run Navigation
pg.run()