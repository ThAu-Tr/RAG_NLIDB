from vanna.qdrant import Qdrant_VectorStore
from vanna.openai import OpenAI_Chat

from vanna.types import TrainingPlan
from vanna.utils import deterministic_uuid
from qdrant_client import models
import scripts.sql_skeleton as sk
import json
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from scripts.vn_qsBase_session import VN_QsBase
from scripts.vn_session import VN_session

import duckdb
import scripts.openai_cookbook as oc

from collections import defaultdict, deque
import re
import ast

import sqlglot
from sqlglot.errors import ParseError

load_dotenv('.env')

class VN_QuerySystem(Qdrant_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        Qdrant_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

        #self.graph = self.get_join_graph('Chinook')

        # For Example-Select-Module
        config_zero ={
            "client": config.get("client"),
            "fastembed_model": config.get("fastembed_model"),
            "n_results": 11,
            "documentation_collection_name": config.get("documentation_collection_name"), #"zero_documentation", #config.get("documentation_collection_name"),
            "ddl_collection_name": config.get("ddl_collection_name"),
            "sql_collection_name": "zero_sql",
            "api_key": config.get("api_key"),
            "model": "gpt-4o-mini", #config.get("model"),
            "temperature": config.get("temperature")
        }

        self.vn_zero = VN_QsBase(config=config_zero)

        config_preSelection ={
            "client": config.get("client"),
            "fastembed_model": config.get("fastembed_model"),
            "n_results": 500,
            "documentation_collection_name": config.get("documentation_collection_name"),
            "ddl_collection_name": config.get("ddl_collection_name"),
            "sql_collection_name": config.get("sql_collection_name"),
            "temperature": config.get("temperature")
        }

        self.vn_preSelection = VN_QsBase(config=config_preSelection)
        self.n_results = config.get("n_results", 10)
        self._session = VN_session()   
        self.model = config.get("model")

    # Overwrite, um Prompts zu speichern
    def generate_sql(self, question: str, allow_llm_to_see_data=False, **kwargs) -> tuple:
        
        if self.config is not None:
            initial_prompt = self.config.get("initial_prompt", None)
        else:
            initial_prompt = None
        question_sql_list = self.get_similar_question_sql(question, **kwargs)
        ddl_list = self.get_related_ddl(question, **kwargs)
        doc_list = self.get_related_documentation(question, **kwargs)
        utterance_list = self._session.get_history()[-6:-1]
        prompt = self.get_sql_prompt(
            initial_prompt=initial_prompt,
            question=question,
            question_sql_list=question_sql_list,
            ddl_list=ddl_list,
            doc_list=doc_list,
            utterance_list = utterance_list,
            **kwargs,
        )
        self.log(title="SQL Prompt", message=prompt)
        llm_response = self.submit_prompt(prompt, **kwargs)
        self.log(title="LLM Response", message=llm_response)
                                        
        return self.extract_sql(llm_response), prompt

    # Prompt-Modul
    ## Table Representation
    def convert_ddlToSchema(self,ddl:str) -> str:
        chrList = ['"',"'","`", '\t', '\\t']
        for chr in chrList:
            ddl = ddl.replace(chr,' ')

        code_lines = ddl.split('\n')
        schema = code_lines[0].strip().removeprefix('CREATE TABLE')
        code_lines = code_lines[1:]
        for cl in code_lines:
            if cl.startswith(','):
                cl = cl.replace(',', '')
            cl = cl.strip()
            if cl.upper().startswith('PRIMARY KEY'):
                continue
            if ('FOREIGN KEY' in cl.upper()  or len(cl)==1): 
                schema +=cl.replace('( ', '(').replace(' )', ')') + ' '
            else:
                firstWord = cl.split(' ')[0]
                schema += firstWord + ', '

        if not(schema.strip().endswith(')')):
            schema = schema + ')'
        result = ')'.join(schema.rsplit(', )', 1)).strip()
    
        return result
    
    def get_exampleValues(self, tbl_name, db_name) -> str:
        self.connect_to_duckdb(st.secrets.get('dbLoc') + '/' + db_name + '/' + db_name + '.duckdb')
        sql = 'SELECT * FROM "' + tbl_name + '" ORDER BY RANDOM() LIMIT 2'
        example_dict = self.run_sql(sql).to_dict('list')
        return 'Value-Examples: ' + str(example_dict).replace('{', '').replace('}', '')

    def add_ddl(self, ddl: str, **kwargs) -> str:
        schema = self.convert_ddlToSchema(ddl)
        exampleValues = self.get_exampleValues(kwargs.get('tbl_name'), kwargs.get('db_name'))
        schema += ' \n' + exampleValues
        return super().add_ddl(schema)
    
    
    ## Prompt Representation
    #   Override of VannaBase. Newly implemented according to (Gao et al., 2023)
    def get_sql_prompt(
        self,
        initial_prompt : str,
        question: str,
        question_sql_list: list,
        ddl_list: list,
        doc_list: list,
        utterance_list: list,
        **kwargs,
    ):

        if initial_prompt is None:
            initial_prompt = f"You are a {self.dialect} expert. Generate {self.dialect} SQL query only and with no explanation. Instead of '*' always name all the columns. If there are duplicate column names, use aliases by using the table-name as a prefix with an '_' as a seperator. \n"
            #initial_prompt += """When combining multiple fact tables:
#1. Identify the grain of each fact table.
#2. Combine them only through shared dimensions or a shared key set that preserves grain.
#3. Use all required predicates for the join, not a subset.
#4. If grains differ, aggregate first to a common grain.
#5. Avoid joins that can multiply rows."""

        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        if self.static_documentation != "":
            doc_list.append(self.static_documentation)

        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )

        message_log = [self.system_message(initial_prompt)]

        if len(question_sql_list) > 0:
            message_log.append(self.system_message('Some example SQL queries are provided based on similar problems:'))

        for example in question_sql_list:
            if example is None:
                print("example is None")
            else:
                if example is not None and "question" in example and "sql" in example:
                    #message_log.append(self.user_message(example["question"]))
                    message_log.append(self.assistant_message(example["sql"]))

        if len(utterance_list) > 0:
            message_log.append(self.system_message('Past interactions in this session: '))
        
        for utterance in utterance_list:
            if utterance is None:
                print("no history")
            else:
                if utterance is not None and "question" in utterance and "query" in utterance:
                    message_log.append(self.user_message(utterance["question"]))
                    if utterance["query"] is not None:
                        message_log.append(self.assistant_message(utterance["query"]))
                    if utterance["summary"] is not None:
                        message_log.append(self.assistant_message("Result-Summary: " + utterance["summary"]))
        
        message_log.append(self.system_message("Answer the following:"))#f"The System has interpreted the user-question as:\n'{kwargs.get('plan')}'\n\n. Based on that interpretation, generate a SQL-Query for the following:"))
            
        message_log.append(self.user_message(question))

        return message_log
    
    def add_ddl_to_prompt(
        self, initial_prompt: str, ddl_list: list[str], max_tokens: int = 14000
    ) -> str:
        if len(ddl_list) > 0:
            initial_prompt += '\n' + f"{self.dialect} SQL tables, with their properties:\n\n"

            for ddl in ddl_list:
                if (
                    self.str_to_approx_token_count(initial_prompt)
                    + self.str_to_approx_token_count(ddl)
                    < max_tokens
                ):
                    initial_prompt += f"{ddl}\n"

        return initial_prompt
    """
    def get_related_ddl(self, question: str, **kwargs) -> list:
        results = self._client.query_points(
            self.ddl_collection_name,
            query=self.generate_embedding(question),
            #limit=self.n_results,
            with_payload=True,
        ).points

        return [result.payload["ddl"] for result in results]
    """    
    # Schema-Linking-Modul
    def get_related_ddl(self, question: str, **kwargs) -> list:
        preliminary_sql = kwargs.get('preliminary_sql')
        preliminary_tables = self.extract_table_names_from_sql(preliminary_sql)
        ddl_list = self.get_intermediate_ddl(preliminary_tables)

        key_ddl_list = list(set(ddl_list))
        #tables = self.extract_table_name(key_ddl_list)
        #intermediates = self.get_intermediates(tables)
        #intermediate_ddl_list = self.get_intermediate_ddl(intermediates)
        #rint(intermediate_ddl_list)
        return key_ddl_list #+ intermediate_ddl_list

    def extract_table_names_from_sql(self, sql: str):
        try:
            expression = sqlglot.parse_one(sql)
            tables = {table.name for table in expression.find_all(sqlglot.exp.Table)}
            return list(tables)
        
        except ParseError as e:

            # Attempt simple fallback extraction (basic FROM/JOIN regex)
            pattern = r'(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][\w.]*)'
            tables = re.findall(pattern, sql, re.IGNORECASE)
            return list(set(tables))
    
    def extract_table_name(self, ddl_list:list) -> list:
        tables = []
        for ddl in ddl_list:
            ddl_clean = ddl.replace('(',' ')
            table = ddl_clean.split(' ')[0]
            tables.append(table)
        return tables
    
    def get_intermediate_ddl(self,intermediates):
        training_data = self.get_training_data()
        ddls = list(training_data[training_data['training_data_type']=='ddl']['content'])
        return [ddl for ddl in ddls if ddl.startswith(tuple(intermediates))]
    
    def bfs_connected(self, start, allowed_nodes, graph):
        visited = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in graph[node]:
                if neighbor in allowed_nodes and neighbor not in visited:
                    queue.append(neighbor)
        return visited
    
    def get_intermediates(self, tables):
        table_set = set(tables)
        components = []
        seen = set()

        for table in tables:
            if table not in seen:
                component = self.bfs_connected(table, table_set,self.graph)
                components.append(component)
                seen.update(component)

        if len(components) == 1:
            return []
        else:
            required_intermediates = set()
            base_component = components[0]
            remaining_components = components[1:]

            for comp in remaining_components:
                target_found = False
                for target in comp:
                    queue = deque([(target, [])])
                    visited = set()
                    while queue:
                        current, path = queue.popleft()
                        if current in base_component:
                            intermediates = [node for node in path if node not in table_set]
                            required_intermediates.update(intermediates)
                            target_found = True
                            break
                        visited.add(current)
                        for neighbor in self.graph[current]:
                            if neighbor not in visited:
                                queue.append((neighbor, path + [neighbor]))
                    if target_found:
                        break

            return list(required_intermediates)
    
    
    # Example-Select-Module
    def train(
        self,
        question: str = None,
        sql: str = None,
        ddl: str = None,
        documentation: str = None,
        plan: TrainingPlan = None,
        db_id: str = None,
        **kwargs
    ) -> str:
        
        if db_id:
            sql_skeleton = sk.extract_skeleton(sk.normalization(sql),sk.get_db_schemas(json.load(open(st.secrets.get('tabLoc'))))[db_id])
            return self.add_question_sql(question=question, sql=sql, sql_skeleton=sql_skeleton)
        if ddl:
            print("Adding ddl:", ddl)
            return self.add_ddl(ddl,**kwargs)
        else: 
            super().train(question,sql,ddl,documentation,plan)

        
    def get_jaccard_similarity(self, set1, set2):
            # intersection of two sets
        intersection = len(set1.intersection(set2))
            # Unions of two sets
        union = len(set1.union(set2))
     
        return intersection / union

    def remove_prefix_before_dot(self, sql):
        return re.sub(r'\b\w+\.', '', sql)
    
    def remove_column_aliases(self, sql):
    # Replace "AS alias" (case-insensitive) with nothing
        return re.sub(r'\s+AS\s+\w+', '', sql, flags=re.IGNORECASE)
    
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        sql = kwargs.get('preliminary_sql')
        
        try:
            """
            sql = self.remove_prefix_before_dot(self.remove_column_aliases(sql))

            sql_normalized = sk.normalization(sql)
            all_db_infos = json.load(open(st.secrets.get('tabLoc')))
            db_schemas = sk.get_db_schemas(all_db_infos)
            sql_skeleton = sk.extract_skeleton(sql_normalized,db_schemas[kwargs.get('db_id')])

            sql_skeleton = sql_skeleton.replace('join', '').replace('left', '').replace('right', '').replace('inner', '').replace('outer', '').replace('full', '').replace('cross', '')
            print(sql_skeleton)

            """
            sql_skeleton = self.get_skeleton_sql(sql)
            print(sql_skeleton)
            

        except:
            sql_skeleton = sql
            print("NO SKELETON")

        zpred = set(sql_skeleton.split(' '))

        q_candidates = self.vn_preSelection.get_similar_question_sql(question)
        for q in q_candidates:
            candi = set(q['sql_skeleton'].split(' '))
            q['jaccard_similarity'] = self.get_jaccard_similarity(zpred,candi)


        df = pd.DataFrame.from_dict(q_candidates)
        df['initialOrder'] = df.index
        try:
            df = df.sort_values(by=['jaccard_similarity','initialOrder'], ascending=[False,True], axis=0)
        except:
            df = df.sort_values(by='initialOrder', ascending=True, axis=0)
            
            cols_to_add = ['question', 'sql']
            for col in cols_to_add:
                if col not in df.columns:
                    df[col] = None

        df = df.head(self.n_results)
        df = df[['question','sql']]

        return df.to_dict(orient='records')
    
    def get_skeleton_sql(self, sql, **kwargs):
        prompt = self.get_skeleton_prompt(sql)
        llm_response = self.vn_zero.submit_prompt(prompt, **kwargs)
        sql_skeleton = self.extract_dict_value(llm_response, "sql_skeleton")
        return sql_skeleton
    
    def get_skeleton_prompt(self, sql):
        initial_prompt = "You are a helpful data assistant specialized in the {self.dialect} dialect. Your task is to extract the SQL-Skeleton of a SQL-Query similiar to the following examples: \n"
        initial_prompt +=  ('Example 1' + '\n' + 
                            'SQL-Query: ' + 'SELECT count(*) FROM Customers_cards WHERE card_type_code  =  "Debit"' + '\n' +
                            'SQL-Skeleton: ' + 'select count ( _ ) from _ where _' + '\n' +
                            '\n' +
                            'Example 2' + '\n' +
                            'SQL-Query: ' + 'SELECT Payment_Method_Code ,  Date_Payment_Made ,  Amount_Payment FROM Payments ORDER BY Date_Payment_Made ASC' + '\n' +
                            'SQL-Skeleton: ' + 'select _ from _ order by _ asc' + '\n' +
                            '\n' +
                            'Example 3' + '\n' +
                            'SQL-Query: ' + 'SELECT count(*) ,  T1.name FROM airports AS T1 JOIN routes AS T2 ON T1.apid  =  T2.src_apid GROUP BY T1.name' + '\n' +
                            'SQL-Skeleton: ' + 'select count ( _ ) , _ from _ group by _' + '\n' +
                            '\n' +
                            'Example 4' + '\n' +
                            'SQL-Query: ' + 'SELECT t1.lname FROM authors AS t1 JOIN authorship AS t2 ON t1.authid  =  t2.authid JOIN papers AS t3 ON t2.paperid  =  t3.paperid GROUP BY t1.fname ,  t1.lname ORDER BY count(*) DESC LIMIT 1' + '\n' +
                            'SQL-Skeleton: ' + 'select _ from _ group by _ order by count ( _ ) desc limit _' + '\n'
                            '\n' +
                            'Example 5' + '\n' +
                            'SQL-Query: ' + 'SELECT name FROM physician WHERE POSITION LIKE "%senior%"' + '\n' +
                            'SQL-Skeleton: ' + 'select _ from _ where _ like _' + '\n'
                            )
        
        initial_prompt += '\n Please respond with a Python-Dictionary storing the key "sql_skeleton" written as a one-liner. '
        initial_prompt += '\n The value for "sql_skeleton" should only consist of the SQL-Skeleton. It should include aggregate-functions, but not include joins, aliases or any extra information. + \n'
        
        message_log = [self.system_message(initial_prompt)]

        message_log.append(self.system_message('Extract the SQL-Skeleton for the following SQL-Query:'))
        message_log.append(self.user_message(sql))

        return message_log


    
    def add_question_sql(self, question: str, sql: str, sql_skeleton: str = None, **kwargs) -> str:
        if sql_skeleton:
        
            question_answer = "Question: {0}\n\nSQL: {1}".format(question, sql)
            id = deterministic_uuid(question_answer)

            self._client.upsert(
                self.sql_collection_name,
                points=[
                    models.PointStruct(
                        id=id,
                        vector=self.generate_embedding(question_answer),
                        payload={
                            "question": question,
                            "sql": sql,
                            "sql_skeleton": sql_skeleton
                        },
                    )
                ],
            )

    # Correction-Modul
    def generate_and_correct_sql(self, question: str, **kwargs) -> str:
        history = self._session.get_history()[-6:]
        self.vn_zero._session.set_history(history)
        preliminary_sql = self.vn_zero.generate_sql(question, **kwargs)[0]
        if not self.is_sql_valid(preliminary_sql):
            return "", "Not a text-to-sql-question", ""

        sql, prompt = self.generate_sql(question, preliminary_sql=preliminary_sql, **kwargs)
        if not self.is_sql_valid(sql):
            return "", "Not a text-to-sql-question", ""

        db_id = kwargs.get('db_id')
        db_path = st.secrets.get('dbLoc') + '/' + db_id + '/' + db_id + '.duckdb'
        executable, message = self.check_sql(sql,db_path)

        if executable:
            return sql, message, prompt
        else:
            self.log(title="SQL Correction needed: 1. Attempt", message=message)
            return self.correct_sql(question, sql, message, db_path, 1, preliminary_sql = preliminary_sql, **kwargs)
        

    def check_sql(self,predicted_sql,db_path):
        self.connect_to_duckdb(db_path)
        try:
            df = self.run_sql(predicted_sql)
        except Exception as e:
            return False, str(e)
    
        if len(df) > 0:
            return True, None
        else:
            return False, "sql returns no value"
        
    def correct_sql(self, question, sql, message, db_path, attempt, **kwargs) -> str:
        correction_prompt = self.get_correction_prompt(question, sql, message, **kwargs)
        self.log(title="Correction Prompt", message=correction_prompt)
        corrected_llm_response = self.submit_prompt(correction_prompt)
        corrected_sql = self.extract_dict_value(corrected_llm_response, "corrected_SQL")
        executable, new_message = self.check_sql(corrected_sql, db_path)
        if executable or attempt == 2:
            return self.extract_sql(corrected_sql), new_message, correction_prompt
        else:
            self.log(title="SQL Correction needed: " + str(attempt + 1) + '. Attempt', message=new_message)
            return self.correct_sql(question, corrected_sql, new_message, db_path, attempt + 1, **kwargs) 

    def get_correction_prompt(self, question, sql, message, **kwargs) -> str:
        initial_prompt = f"You are a {self.dialect} expert. There is a SQL-Query generated based on the following Database Schema to respond to the Question. Executing this SQL-Query has resulted in an error and you need to fix it based on the Error-Message. \n"#, while following the System-Interpretation. \n"
        #initial_prompt += """When combining multiple fact tables:
#1. Identify the grain of each fact table.
#2. Combine them only through shared dimensions or a shared key set that preserves grain.
#3. Use all required predicates for the join, not a subset.
#4. If grains differ, aggregate first to a common grain.
#5. Avoid joins that can multiply rows."""
        ddl_list = self.get_related_ddl(question, **kwargs)
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        initial_prompt += '\n' + f"Question:\n{question} \n"
        #initial_prompt += '\n' + f"System-Interpretation:\n{kwargs.get('plan')} \n"
        initial_prompt += '\n' + f"Executed SQL:\n{sql} \n"
        initial_prompt += '\n' + f"Error-Message:\n{message} \n"
        
        """
        doc_list = self.get_related_documentation(question)
        if self.static_documentation != "":
            doc_list.append(self.static_documentation)

        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )
        """

        initial_prompt += '\n Please respond with a Python-Dictionary storing the key "corrected_SQL" written as a one-liner. \n'

        message_log = [self.system_message(initial_prompt)]

        # Added for multi-turn-functionality
        utterance_list = self._session.get_history()[-6:-1]
        if len(utterance_list) > 0:
            message_log.append(self.system_message('Past interactions in this session: '))
            
        for utterance in utterance_list:
            if utterance is None:
                print("no history")
            else:
                if utterance is not None and "question" in utterance and "query" in utterance:
                    message_log.append(self.user_message(utterance["question"]))
                    #if utterance["query"] is not None:
                        #message_log.append(self.assistant_message(utterance["query"]))
                    #if utterance["summary"] is not None:
                        #message_log.append(self.assistant_message("Result-Summary: " + utterance["summary"]))

        return message_log
    
    def extract_dict_value(self, llm_response: str, key: str):

        pattern = r'\{.*?\}'

        matches = re.findall(pattern, llm_response, re.DOTALL)
        for match in matches:
            try:
                result = ast.literal_eval(match)
                if isinstance(result, dict):
                    return result[key]
            except (ValueError, SyntaxError, KeyError):
                continue

        print("No valid dictionary found.")
        return None


    # Added to stay within the context-window
    def generate_summary(self, question: str, df: pd.DataFrame, **kwargs) -> str:
        summary_prompt = self.get_summary_prompt(question, df, **kwargs)
        summary = self.vn_zero.submit_prompt(summary_prompt, **kwargs)
        return summary

    def get_summary_prompt(self, question: str, df: pd.DataFrame, **kwargs) -> str:
        alternatives = kwargs.get('alternatives')
        #self.log(title="Alternatives", message=str(alternatives))
        
        message_log = [
            self.system_message(
                f"You are a helpful data assistant. The user asked the question: '{question}'\n\nThe following is a pandas DataFrame with the results of the query: \n{df[:100].to_markdown()}\n\n"
            ),
            self.user_message(
                "Briefly summarize the data based on the question that was asked. " +
                #"Do not respond with any additional explanation beyond the summary." +
                self._response_language()
            ),
        ]

        if alternatives is not None:
            message_log.append(
                self.user_message(
                f"Start a new paragraph before briefly summarizing the following alternatives without asking the user to choose. Instead, invite the user to let you know, if they'd like to see the result for any of them: {str(alternatives)} "
                "If the list is empty, make something up that is related to the user question."
                "Do not respond with any additional explanation beyond the summary and invitation."
                ))



        num_tokens = oc.num_tokens_from_messages(message_log, self.model)
        context_window = self.get_context_window(self.model)
        if num_tokens < (context_window / 2):
            return message_log
        else: 
            row = len(df)
            reduce = round(row * 0.75)
            return self.get_summary_prompt(question, df[:reduce])

    def get_context_window(self, model_name):
        context_windows = {
            'gpt-3.5-turbo': 4096,
            'gpt-3.5-turbo-16k': 16384,
            'gpt-4': 8192,
            'gpt-4-32k': 32768,
            'gpt-4-turbo': 128000,
            'gpt-4o': 128000,
            'gpt-4o-mini': 128000,
            'gpt-4.1': 1000000,
            'gpt-4.1-mini': 1000000,
            'gpt-5-mini': 400000,
            'gpt-5.4-mini': 400000
        }
        return context_windows.get(model_name)
    
    # For multi-turn szenario
    def setUp_newSession(self):
        self._session = VN_session()
    
    def get_currentSession(self) -> VN_session:
        return self._session

    # For pracical usage
    def check_sql_for_release(self, predicted_sql, db_path):
        conn = duckdb.connect(db_path)
        #conn.text_factory = bytes
        cursor = conn.cursor()
        try:
            cursor.execute(predicted_sql)
        except Exception as e:
            return False, predicted_sql, str(e)
    
        return True, predicted_sql, None
    
    # Interpretation-Modul
    def get_interpretation(self, question, **kwargs):
        ddl_list = self.get_all_ddl()
        utterance_list = self._session.get_history()[-6:-1]
        prompt = self.get_interpretation_prompt(question, ddl_list, utterance_list)
        llm_response = self.vn_zero.submit_prompt(prompt, **kwargs)
        plan = self.extract_dict_value(llm_response, "most_likely")
        alternatives = self.extract_dict_value(llm_response, "alternatives")
        
        return plan, alternatives

    def get_interpretation_prompt(self, question, ddl_list, utterance_list):
        initial_prompt = "You are a Database Expert System specialized in the {self.dialect} dialect. Your task is to interpret the user's natural language question, describe the most likely interpretation and generate a Python-list of other plausible interpretations or intentions behind it. These interpretations will serve as alternative plans for generating a SQL query in later steps. Use the provided database-schema and the conversation-context to guide your analysis. \n"

        initial_prompt += '\n Please respond with a Python-Dictionary storing the two keys "most_likely" and "alternatives" written as a one-liner. '
        initial_prompt += '\n The value for "most_likely" should be the interpretation that is going to satisfy the user best and not include any extra information. '
        initial_prompt += '\n The value for "alternatives" must be a Python-list. The values for that list needs to be brief description of the other alternatives and not include any extra information. If there is only one clear primary interpretation, return [] \n'

        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        message_log = [self.system_message(initial_prompt)]
        
        # Added for multi-turn-functionality
        if len(utterance_list) > 0:
            message_log.append(self.system_message('Past interactions in this session: '))
            
        for utterance in utterance_list:
            if utterance is None:
                print("no history")
            else:
                if utterance is not None and "question" in utterance and "query" in utterance:
                    message_log.append(self.user_message(utterance["question"]))
                    if utterance["query"] is not None:
                        message_log.append(self.assistant_message(utterance["query"]))
                    if utterance["summary"] is not None:
                        message_log.append(self.assistant_message("Result-Summary: " + utterance["summary"]))
        
        message_log.append(self.system_message('Classify the following question:'))
        message_log.append(self.user_message(question))

        return message_log


# Additional Functionalities
    # Suggest a Question
    def generate_questions(self, **kwargs) -> list[str]:
        ddl_list = self.get_all_ddl()
        utterance_list = self._session.get_history()[-5:]
        prompt = self.get_question_prompt(ddl_list, utterance_list, **kwargs)
        llm_response = self.vn_zero.submit_prompt(prompt, **kwargs)
        return self.extract_questionList(llm_response)
    
    def get_all_ddl(self):
        trainingData = self.get_training_data()
        ddlData = trainingData[trainingData.training_data_type=='ddl']
        return ddlData['content'].tolist()
    
    def extract_sql(self, llm_response):
        if llm_response:
            return super().extract_sql(llm_response)
        else:
            return "SQL could not be generated"
        
    def get_question_prompt(self,ddl_list, utterance_list, **kwargs):
        initial_prompt = f"Generate 5 questions about the following database, that can be answered with a SQL query. This means that the question should have specific values and can be given to a NLIDB without any changes. Consider what users asked in the past and suggest questions that help them explore the database. "
        initial_prompt += "Return just the question without any additional explanation. The ouput needs to be in one python-list written as a one-liner."
        initial_prompt += self._response_language()
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        message_log = [self.system_message(initial_prompt)]

        if len(utterance_list) > 0:
            message_log.append(self.system_message('Past interactions in this session: '))
        
        for utterance in utterance_list:
            if utterance is None:
                print("no history")
            else:
                if utterance is not None and "question" in utterance and "query" in utterance:
                    message_log.append(self.user_message(utterance["question"]))
                    if utterance["query"] is not None:
                        message_log.append(self.assistant_message(utterance["query"]))
                    if utterance["summary"] is not None:
                        message_log.append(self.assistant_message("Result-Summary: " + utterance["summary"]))

        return message_log
    
    def extract_questionList(self, llm_response: str) -> list[str]:

        start = "["
        end = "]"

        # Find the index of the start substring
        idx1 = llm_response.find(start)

        # Find the index of the end substring, starting after the start substring
        idx2 = llm_response.find(end, idx1 + len(start))

        # Check if both delimiters are found and extract the substring between them
        if idx1 != -1 and idx2 != -1:
            res = llm_response[idx1 + len(start):idx2]
            return eval('[' + res + ']')

        else:
            print("Delimiters not found")

    # Generate Plot
    def should_generate_chart(self, df: pd.DataFrame) -> bool:
        if super().should_generate_chart(df):
            num_columns = list(df.select_dtypes(include=['number']))
            return any(not col.lower().endswith("id") for col in num_columns)
        else:
            return False
        
    def generate_plotly_code_on_demand(self, df, message, **kwargs):
        system_msg = f"The following is a pandas DataFrame 'df': \n{df}"

        message_log = [
            self.system_message(system_msg),
            self.user_message(
                "Can you generate the Python plotly code to chart the results of the dataframe? Assume the data is in a pandas dataframe called 'df'. If there is only one value in the dataframe, use an Indicator. Respond with only Python code. Do not answer with any explanations -- just the code."
            ),
        ]

        if(message):
            message_log.append(self.system_message("Take especially the following user-message into consideration:"))
            message_log.append(self.user_message(message))
            message_log.append(self.system_message("If multiple charts are requested, use make_subplots to combine them to one fig"))



        plotly_code = self.submit_prompt(message_log, kwargs=kwargs)
        print(plotly_code)

        return self._sanitize_plotly_code(self._extract_python_code(plotly_code))
    
    def generate_sql_explanation_on_demand(self, sql, related_question, **kwargs):
        message_log = [
            self.system_message(
                f"You are a helpful data assistant. The user has asked the question: '{related_question}'\n\nThe following is the generated query: \n{sql}\n\n"
            ),
            self.system_message(
                "Briefly explain the query based on the question that was asked. While keeping it as short as possible, explain each clause-type and subselect. Do not respond with any additional information beyond the explanation." +
                self._response_language()
            ),
        ]

        explanation = self.vn_zero.submit_prompt(message_log, **kwargs)

        return explanation
    
    def generate_error_response(self, question, message, **kwargs):
        message_log = [
            self.system_message(
                f"You are a helpful data assistant. In order to generate a sql-query the user has asked the question: '{question}'\n\nThe following is the message of the system or database: \n{message}\n\n"
            ),
            self.system_message(
                "Briefly explain why a SQL couldn't be generated for that question. " \
                "If a user asked a question unrelated to text-to-sql, make a professional remark to their question. Refer them afterwards to the tools 'Question Suggestion', 'Data Structure' and 'Table Preview' on the left, if they need inspiration." \
                "If a sql couldn't be generated due to an execution error, apologize for the wait and suggest a different wording for that question." \
                "Do not respond with any additional information beyond the task that was given." +
                self._response_language()
            ),
        ]

        explanation = self.vn_zero.submit_prompt(message_log, **kwargs)

        return explanation
    
    def genenerate_interpretation_respond(self, question, plan, **kwargs):
        message_log = [
            self.system_message(
                f"You are a helpful data assistant. The user has asked the following question:\n'{question}'\n\nThe system has interpreted the question as: \n{plan}\n\n"
            ),
            self.system_message(
                "Rephrase this interpretation into a short, friendly and professional explanation that confirms how the system understood the user's request. " \
                "Use natural, conversational language. Do not provide any additional information, include any questions or ask for confirmation." +
                self._response_language()
            ),
        ]

        interpretation_respond = self.vn_zero.submit_prompt(message_log, **kwargs)

        return interpretation_respond
    
    #Added for Databases
    def clean_columns(self,cols):
        return (
            cols.str.strip()
            .str.lower()
            .str.replace(r"[^\w]+", "_", regex=True)   # replace non-alphanumeric with _
            .str.replace(r"_+", "_", regex=True)       # collapse multiple _
            .str.strip("_")
        )


    def get_all_fileInfo(self,uploaded_file):
        all_fileInfo = []
        df_list = []
        table_names = []
        for file in uploaded_file:
            df = pd.read_csv(file, encoding_errors='replace', sep=None, engine='python')
            df.columns = self.clean_columns(df.columns)
            name = file.name.split('.')[0]
            df.attrs['name'] = name
            row_count = str(len(df.index))
            columns = str(list(df.columns.str.strip().values)).replace('[','(').replace(']',')')
            amt_unique = str(df.nunique(axis='index', dropna=True).to_dict()).replace('{','').replace('}','')
            amt_null = str(df.isna().sum().to_dict()).replace('{','').replace('}','')

            file_info = name + ' ' + columns + ' ; row count: ' + row_count + ' ; amount of unique values: ' + amt_unique + ' ; amount of NULL values: ' + amt_null
            all_fileInfo.append(file_info)
            df_list.append(df)
            table_names.append(name)

        return all_fileInfo, df_list, table_names

    
    def get_pk_prediction_prompt(self,file_list,message, **kwargs):
        initial_prompt = f"Predict which of the table columns should be the primary key for its table. A primary key needs to (a) have unique values for each row and (b) not have NULL values. Therefore the row count, the amount of unique values for each column and the amount of NULL values for each column are provided after each table-schema. \n"
        initial_prompt += "Each table should only have one column as a primary key. Return just the column name without any additional explanation. If none of the column is suitable as a primary key just return the value None. The ouput needs to be in one python-dictionary written as a one-liner. \n"
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, file_list, max_tokens=self.max_tokens
        )
        message_log = [self.system_message(initial_prompt)]

        if(message):
            message_log.append(self.system_message("Take especially the following user-message into consideration:"))
            message_log.append(self.user_message(message))

        return message_log
    
    
    def get_fk_prediction_prompt(self,file_list, pred_pk_dict, message, **kwargs):
        initial_prompt = f"Predict which of the table columns are foreign keys. A foreign key needs to reference a column with unique values in another table (often the primary key). Therefore the row count, the amount of unique values for each column and the amount of NULL values for each column are provided after each table-schema. The predicted primary keys for each table are provided at the end.\n"
        initial_prompt += "Not every table needs to have foreign keys. One table might have one or more foreign keys. Return the foreign-key-reference-column-pair without any additional explanation. Return the foreign key and the reference column in the following style: table.foreignKey : referenceTable.referenceColumn . The ouput needs to be in one python-dictionary written as a one-liner. \n"
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, file_list, max_tokens=self.max_tokens
        )
        initial_prompt += "Predicted primary keys: " + str(pred_pk_dict)
        message_log = [self.system_message(initial_prompt)]
        if(message):
            message_log.append(self.system_message("Take especially the following user-message into consideration:"))
            message_log.append(self.user_message(message))

        return message_log
    """

    def get_fk_prediction_prompt(self, file_list, pred_pk_dict, table_names, **kwargs):

        initial_prompt = (
            "Predict which of the table columns are foreign keys.\n"
            "A foreign key must reference a column with unique values in another listed table.\n"
            "Use ONLY the tables and columns listed below.\n"
            f"Valid table names: {table_names}\n"
            "Do NOT invent tables or columns.\n"
            "If no valid foreign keys exist, return {}.\n"
            "Return the result as a one-line Python dictionary:\n"
            "{'table.foreignKey': 'referenceTable.referenceColumn'}\n"
            "Schema:\n"
        )

        initial_prompt = self.add_ddl_to_prompt(initial_prompt, file_list, max_tokens=self.max_tokens)
        initial_prompt += "\nPredicted primary keys: " + str(pred_pk_dict)
        print(initial_prompt)

        return [self.system_message(initial_prompt)]
    """
    
    def extract_keyDict(self,llm_response):
        start = "{"
        end = "}"

        # Find the index of the start substring
        idx1 = llm_response.find(start)

        # Find the index of the end substring, starting after the start substring
        idx2 = llm_response.find(end, idx1 + len(start))

        # Check if both delimiters are found and extract the substring between them
        if idx1 != -1 and idx2 != -1:
            res = llm_response[idx1 + len(start):idx2]
            return eval('{' + res + '}')

        else:
            print("Delimiters not found")
    
    def generate_keyPrediction(self, uploaded_file, user_message, **kwargs):
        all_fileInfo, df_list, table_names = self.get_all_fileInfo(uploaded_file)

        if len(uploaded_file) < 2:
            return {all_fileInfo[0].split(" ")[0]:None},{}, df_list, all_fileInfo
        
        else:
            pk_prompt = self.get_pk_prediction_prompt(all_fileInfo, user_message, **kwargs)
            pk_llm_response = self.submit_prompt(pk_prompt, **kwargs)
            pred_pk_dict = self.extract_keyDict(pk_llm_response)
        
            fk_prompt = self.get_fk_prediction_prompt(all_fileInfo, pred_pk_dict, user_message, **kwargs)
                                                      #table_names, **kwargs)
            #print(fk_prompt)                                          
            fk_llm_response = self.submit_prompt(fk_prompt, **kwargs)
            pred_fk_dict = self.extract_keyDict(fk_llm_response)

            return pred_pk_dict, pred_fk_dict, df_list, all_fileInfo