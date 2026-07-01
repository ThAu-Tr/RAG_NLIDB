import streamlit as st
import pandas as pd
from scripts import vanna_calls_ds as vc
import time
import sqlite3
import os
from eralchemy2 import render_er
import streamlit_mermaid as stmd
import re
import itertools
import shutil
from pathlib import Path

st.title("Databases")

#st.markdown("""
#Manage the databases available to the system and integrate new data sources. 
#You can combine one or multiple CSV-files into a realtional SQLite-database.
#with automatic primary and foreign key detection and explore them with the provided ER-diagrams. 

st.markdown("""           
Manage the databases available to the system and integrate new data sources. 
You can combine one or multiple CSV-files into a relational SQLite-database. 
When multiple files are uploaded, the system will attempt to identify primary and foreign keys based on column names and column characteristics.
Additionally, an **ER-diagram** will be created to visualize tables and relationships.  
""")

st.warning("""
⚠️ This application runs on the Streamlit Community Cloud. Uploaded data may not be stored permanently 
and should not contain confidential or sensitive company information. A list of example datasets are provided below to test the system without uploading your data.
""")

with st.expander("Example Datasets"):
    #st.markdown("""
#You can download example datasets below to test the system without uploading your own data.
#""")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ##### *CSV-Files*
        - Chinook Database (SQLite)  
        Download: https://example.com/chinook.sqlite
        - second link
        - third link            
        """)

    with col2:
        st.markdown("""
        ##### *SQLite-Databases*
        - Sakila Database  
                    Download: https://github.com/bradleygrant/sakila-sqlite3
        - Northwind Database  
                    Download: https://github.com/jpwhite3/northwind-SQLite3
        - third link 

        """)

with st.expander("Disclaimer"):
    st.markdown("""
Please note that this part of the system was not part of the core thesis implementation, but rather introduced as a convenience feature to allow flexible data integration.
As such, 
the automatic detection of primary and foreign keys is experimental. It was not part of the core thesis implementation, but rather introduced as a convenience feature to allow flexible data integration. 
As such, it has **not** been **extensively validated** and may fail to identify relationships, especially when column names **differ significantly** (e.g., SupportRepId vs. EmployeeId).
""")

st.divider()

def get_tableList(db_name):
    con = sqlite3.connect(st.secrets.get('dbLoc') + db_name + '/' + db_name + '.sqlite')
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    result = [item[0] for item in cursor.fetchall()]
    return result

def get_columnList(db_name,table_name):
    con = sqlite3.connect(st.secrets.get('dbLoc') + db_name + '/' + db_name + '.sqlite')
    cursor = con.cursor()
    cursor.execute("select * from "+ table_name + ";")
    columnList = list(map(lambda x: x[0], cursor.description))
    return columnList

def turn_listToString(li:list):
    liString = str(li).replace('[','(').replace(']',')')
    return liString

def write_newDBList():
    new_display = []
    for index, row in database_df.iterrows():
        domain = row['Domain']
        display = st.session_state.get('display_' + domain)
        new_display.append(display)

    database_df['Display'] = new_display
    database_df.to_csv(st.secrets.get('dbList'), sep=',', index=False)


dbFile = vc.get_dbFile()
database_df = dbFile

domain_val = st.selectbox(
    "Which domain would you like to see?",
    eval(vc.get_dbString(filter=False)),
    index=None,
    placeholder="Select...",
    )
if not domain_val is None:
    #domain_val = domain_val.replace(' ', '_')
    st.toggle("Dynamic", value=False, key="dynamic_er-diagram")
    direction = st.radio(
        "Set rendering direction:",
        ["Left to Right", "Top to Bottom"],
        horizontal=True,
        disabled= not st.session_state.get("dynamic_er-diagram"),
        label_visibility='collapsed'
    )

    if st.session_state.get("dynamic_er-diagram"):
        if direction == 'Left to Right': direct = '_LR'
        else: direct = ''

        code = vc.read_file('./ER-Diagram/erd_from_'+ domain_val + direct + '_sqlite.md')
        stmd.st_mermaid(eval(code))
    else:
        st.image('./ER-Diagram/erd_from_'+ domain_val +'_sqlite.png')

    st.divider()

    with st.expander("Danger Zone"):
    
        st.error("Deleting a database permanently removes it.")    
        deletable = database_df.loc[database_df["Domain"] == domain_val, "Deleteable"].iloc[0]
        curDB_Flag = False
        current_db = vc.get_runtimeParams()['db_mono']

        if domain_val == current_db:
            st.warning(
                f"The database **{domain_val}** is currently used by the chat. "
                "Please switch the chat to another database before deleting it."
            )
            curDB_Flag = True

        if not deletable:
            st.warning("This database is protected and cannot be deleted.")

        confirm_delete = st.checkbox(
            f"I understand that '{domain_val}' will be permanently deleted.",
            key=f"confirm_delete_{domain_val}",
            disabled=not deletable or curDB_Flag
        )

        delete_clicked = st.button(
            "Delete database",
            type='primary',
            disabled=not deletable or curDB_Flag
        )

        if delete_clicked:
            if not confirm_delete:
                st.warning("Please confirm deletion first.")
        
            else:
                try:                
                    db_folder = os.path.join(st.secrets.get("dbLoc"), domain_val)

                    er_file ="./ER-Diagram/erd_from_" + domain_val
                    er_png = er_file + "_sqlite.png"
                    er_mdTD = er_file + "_sqlite.md"
                    er_mdLR = er_file + "_LR_sqlite.md"
                    files_to_delete = [er_png, er_mdTD, er_mdLR]

                    if os.path.exists(db_folder):
                        shutil.rmtree(db_folder)

                    database_df.drop(
                        database_df[database_df["Domain"] == domain_val].index,
                        inplace=True
                    )
                    write_newDBList()

                    st.success(f"Database **{domain_val}** deleted successfully.")

                    for filename in files_to_delete:
                        file = Path(filename)
                        if file.exists():
                            file.unlink()

                    st.rerun()

                except Exception as e:
                    st.error(f"Error deleting database: {e}")


middle = int((len(dbFile))/2)
df1 = dbFile.iloc[:middle,:]
df2 = dbFile.iloc[middle:,:]

with st.form('display'):
    col1, col2 = st.columns(2)
    with col1:
        for index, row in df1.iterrows():
            domain = row['Domain']
            display = row['Display']
            st.toggle('Display **' + domain + '**', value=display, key = 'display_' + domain)

    with col2: 
        for index, row in df2.iterrows():
            domain = row['Domain']
            display = row['Display']
            st.toggle('Display **' + domain + '**', value=display, key = 'display_' + domain)

    submitted = st.form_submit_button("Save")
    if submitted:
        write_newDBList()
        st.write('Selection saved successfully')
        time.sleep(2)
        st.rerun()  

def upload_csvToSQLite(connection, df):
    #df = pd.read_csv(csv, encoding_errors='replace')
    #df.columns = df.columns.str.strip()
    #name = csv_name.split(".")[0]
    df.to_sql(df.attrs['name'], connection, if_exists = 'append', index=False)

def modify_erForChat(db_name):
    fileName = './ER-Diagram/erd_from_'+ db_name
    file =  fileName +'_sqlite.md'
    fileLR = fileName +'_LR_sqlite.md'
    #code for Top-to-Down
    code = vc.read_file('./ER-Diagram/erd_from_'+ db_name +'_sqlite.md')
    mermCode = '"""\n' + code.split('\n\n')[1] + '\n"""'
    vc.write_file(file,mermCode)
    #Code for Left-to-Right
    pos = mermCode.find('classDiagram\n') + len('classDiagram\n')
    lrCode = mermCode[:pos] + 'direction LR\n' + mermCode[pos:]
    vc.write_file(fileLR,lrCode)

def render_erForChat(db_name):
    database = "sqlite:///" + st.secrets.get('dbLoc') + '/' + db_name + '/' + db_name + ".sqlite"
    render_er(database, './ER-Diagram/erd_from_'+ db_name +'_sqlite.png')
    render_er(database, './ER-Diagram/erd_from_'+ db_name +'_sqlite.md')
    modify_erForChat(db_name)
    return 'ER-Diagram created successfully'

def validate_input(db_name):
    if db_name == '' or db_name is None:
        return False
    if db_name in database_df['Domain'].to_list():
        return False
    else: return True

def get_create_table_string(tablename, connection):
    sql = """
    select * from sqlite_master where name = "{}" and type = "table"
    """.format(tablename) 
    result = connection.execute(sql)

    create_table_string = result.fetchmany()[0][4]
    return create_table_string

def add_pk_to_create_table_string(create_table_string, colname):
    regex = "(\n.+{}[^,]+)(,)".format(colname)
    return re.sub(regex, "\\1 PRIMARY KEY,",  create_table_string, count=1)

def add_fk_to_create_table_string(create_table_string, fk_dict):
    create_table_string = create_table_string[:-1] + ','

    for fk, ck in fk_dict.items():
        ck_l = ck.split('.')
        fk_constraint = '\nFOREIGN KEY (' + fk.split('.')[1] + ') REFERENCES ' + ck_l[0] + ' (' + ck_l[1] +'),'
        create_table_string += fk_constraint

    create_table_string = create_table_string[:-1] + ')'
    return create_table_string

def add_pk_to_sqlite_table(tablename, primary_key, fk_dict, connection):
    cts = get_create_table_string(tablename, connection)
    cts = add_pk_to_create_table_string(cts, primary_key)
    
    if len(fk_dict) > 0: 
        cts = add_fk_to_create_table_string(cts,fk_dict)

    template = """
    BEGIN TRANSACTION;
        ALTER TABLE {tablename} RENAME TO {tablename}_old_;

        {cts};

        INSERT INTO {tablename} SELECT * FROM {tablename}_old_;

        DROP TABLE {tablename}_old_;

    COMMIT TRANSACTION;
    """

    create_and_drop_sql = template.format(tablename = tablename, cts = cts)

    print(create_and_drop_sql)
    try:
        connection.executescript(create_and_drop_sql)
    except Exception as e:
        print(f"An error occurred: {e}")

def create_sqlite_table(df, primary_key, fk_dict, connection):
    cts = pd.io.sql.get_schema(df, df.attrs['name'])
    cts = add_pk_to_create_table_string(cts, primary_key)
    
    if len(fk_dict) > 0: 
        cts = add_fk_to_create_table_string(cts,fk_dict)

    template = """
    BEGIN TRANSACTION;

        {cts};

    COMMIT TRANSACTION;
    """

    create_and_drop_sql = template.format(cts = cts)

    print(create_and_drop_sql)
    try:
        connection.executescript(create_and_drop_sql)
    except Exception as e:
        print(f"An error occurred: {e}")

def build_fileinfo_map(all_fileInfo):
    # table name is the first token before the first space
    return {s.split(" ", 1)[0].lower(): s for s in all_fileInfo}

def check_uniqueConstraintForPk(pk,file_info):
    if not pk:
        return False
    
    # extract row_count
    row_count_match = re.search(r"row count:\s*(\d+)", file_info)
    if row_count_match is None:
        return False
    row_count = int(row_count_match.group(1))

    # extract unique value vount for pk
    pattern = rf"'{re.escape(pk)}':\s*(\d+)"
    unique_match = re.search(pattern, file_info)
    if unique_match is None:
        return False
    unique_count = int(unique_match.group(1))

    return unique_count == row_count

def filter_fk_dict(fk_dict, df_map, min_overlap=0.8):
    filtered = {}
    table_names = list(df_map)

    for k, v in fk_dict.items():
        try:
            src_table, src_col = k.lower().split('.')
            ref_table, ref_col = v.lower().split('.')
        except ValueError:
            continue

        if ref_table not in table_names:
            continue
        if src_table not in df_map or ref_table not in df_map:
            continue

        src_df = df_map[src_table]
        ref_df = df_map[ref_table]

        if src_col not in src_df.columns or ref_col not in ref_df.columns:
            continue

        src_values = set(src_df[src_col].dropna().astype(str).str.strip().str.lower())
        ref_values = set(ref_df[ref_col].dropna().astype(str).str.strip().str.lower())            
        
        if not src_values:
            continue

        overlap = len(src_values & ref_values) / len(src_values)

        if overlap >= min_overlap:
            filtered[k] = v
            
    return filtered

def setUp_database(df_list,pred_pk_dict,pred_fk_dict, all_fileInfo,connection):
    fileinfo_map = build_fileinfo_map(all_fileInfo)
    df_map = {df.attrs['name'].lower(): df for df in df_list}

    for df in df_list:
        name = df.attrs['name']
        name_lower = name.lower()

        pk = pred_pk_dict.get(name) or pred_pk_dict.get(name_lower)

        fk_candidates = dict(filter(lambda item: name == item[0].split('.')[0], pred_fk_dict.items()))

        fk_dict = filter_fk_dict(fk_candidates, df_map)
        print(fk_dict)

        file_info = fileinfo_map.get(name_lower)

        if not check_uniqueConstraintForPk(pk,file_info):
            pk = None
                    
        create_sqlite_table(df, pk, fk_dict, connection)
        upload_csvToSQLite(connection, df)

def validate_sqlite_with_tables(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """)
        tables = cursor.fetchall()
        conn.close()

        return len(tables) > 0, [t[0] for t in tables]

    except sqlite3.Error:
        return False, []
    

with st.sidebar:
    st.caption("Upload one or multiple CSV files") #st.caption("Upload either multiple CSV files or one SQLite database.")
    with st.form("database_uploader", clear_on_submit=True):
        st.markdown("### Upload database")

        uploaded_csv_files = st.file_uploader("Upload CSV files", type = ['csv'], accept_multiple_files=True)
        #uploaded_sqlite_file = st.file_uploader("Upload SQLite database", type = ['sqlite', 'db', 'sqlite3'], accept_multiple_files=False)
        db_name = st.text_input("Name of the database", placeholder='Name your database', label_visibility='collapsed')
        user_message = st.text_input(
                "User Message",
                label_visibility="collapsed",
                placeholder="Add key hints (optional)"
            )
        
        submitted = st.form_submit_button("Upload")

        if submitted:
            # basic validation
            has_csv = uploaded_csv_files is not None and len(uploaded_csv_files) > 0
            #has_sqlite = uploaded_sqlite_file is not None

            if not validate_input(db_name):
                if db_name == '':
                    st.write('Please give your database a name.')
                else:
                    st.write('**' + db_name + '** already exist. Please reorganize your input.')

            #elif has_csv and has_sqlite:
                #st.write("Please upload either CSV files or one SQLite database, not both.")    

            elif not has_csv: #and not has_sqlite:
                st.write("Please upload at least one CSV file.")     

            else:   
                db_folder = st.secrets.get('dbLoc') + '/' + db_name
                if not os.path.exists(db_folder): 
                    os.makedirs(db_folder)

                db_path = db_folder + '/' + db_name + ".sqlite"

                try:
                    if has_csv:
                        connection = sqlite3.connect(db_path)
                        pred_pk_dict, pred_fk_dict, df_list, all_fileInfo = vc.predict_PKnFK_cached(uploaded_csv_files,user_message)
                        print(pred_pk_dict)
                        print(pred_fk_dict)
                        print(all_fileInfo)
                        setUp_database(df_list,pred_pk_dict,pred_fk_dict,all_fileInfo, connection)
                        connection.close()
                        st.write('Database **' + db_name + '** successfully created from CSV files.')

                    #elif has_sqlite:
                        #with open(db_path, "wb") as f:
                        #    f.write(uploaded_sqlite_file.getbuffer())

                        #connection = sqlite3.connect(db_path)
                        #connection.execute("SELECT name FROM sqlite_master LIMIT 1;")
                        #connection.close()

                        #is_valid, tables = validate_sqlite_with_tables(db_path)

                        #if not is_valid:
                            #os.remove(db_path)
                            #st.error("The uploaded file is not a valid SQLite database with readable tables.")
                        #else:
                            #st.write(f"Database **{db_name}** successfully uploaded.")

                    # post-processing for both
                    er_message = render_erForChat(db_name)
                    st.write(er_message)

                    new_domainID = len(database_df)
                    new_row = {'DomainID':new_domainID, 'Domain':db_name, 'Display':True, 'Deleteable':True}
                    database_df.loc[new_domainID] = new_row
                    write_newDBList()
                    st.write('New database added to selection')
                
                except Exception as e:
                    st.error(f"Upload failed: {e}")

            time.sleep(2)
            st.rerun()