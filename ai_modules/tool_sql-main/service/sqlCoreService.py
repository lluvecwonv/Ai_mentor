from util.langchainLlmClient import LangchainLlmClient
from util.dbClient import DbClient

from langchain_community.agent_toolkits import create_sql_agent

from langchain_core.messages import HumanMessage, SystemMessage

class SqlCoreService():

    def __init__(self):
        self.langchainLlmClient = LangchainLlmClient()
        self.dbClient = DbClient()
        
    def create_agent(self):

        self.agent_executor = create_sql_agent(llm = self.langchainLlmClient.llm, db = self.dbClient.db, agent_type = "openai-tools", verbose = True)

    def create_prompt(self, query: str):
        messages = [
            SystemMessage(content = """
                          - If the question includes the name of the department, please give priority to the department name.
                          - Bot’s responses must always be in **Korean**, no matter what language the user uses to ask the question.
                          - When answering, Bot **MUST NOT mention** anything about databases, tables, or the tools available to you.
                          - Bot should **think autonomously** for any questions that are not directly available in the database. If such a situation arises, answer with your own knowledge of JBNU, but ensure the answer remains relevant to the university.
                          - When using SQL queries, especially with `LIKE`, try to use the **shortest** possible keywords to retrieve as much relevant information as possible. However, do not mention the usage of SQL or any related tools in your responses.
                          - When using DESC and ASC, set the data rate to half of DESC to ASC to avoid bias.
                          - If the user’s input contains multiple languages, reply in Korean, ensuring clarity and relevance.
                          - Your answers should be specific, clear, and informative about Jeonbuk University (JBNU) at all times.
                          - If the question involves a department or major (e.g., '전자공학부' or '간호학과'), remove '과' or '부' from the name and use only the base term for searching (e.g., '전자공학' or '간호학').
                          - RDB Table is : "jbnu_college : 단과대학 목록", "jbnu_department : 학과 (학부) 목록", "jbnu_class : 학과 (학부)에 개설된 과목 목록"
                          """),
            HumanMessage(content = query)
        ]
        
        return messages

    def execute(self, query: str):

        return self.agent_executor.invoke(self.create_prompt(query))["output"]
