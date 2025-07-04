import json
import requests
import re

from util.llmClient import LlmClient
from util.dbClient import DbClient

class CoreService():
    
    def __init__(self):
        self.llmClient = LlmClient()
        self.dbClient = DbClient()
        self.dbClient.connect()

    def dynamic_tool_chain(self, query: str):
        
        client_question = query
        before_result = ' '
        histroy_data = {
            "steps": []
        }

        step_number = 1

        while True:

            # tool list 불러오기 -> json 형태로 넣어줌?
            sql = "SELECT * FROM jbnu_tool_list"
            tool_list = self.dbClient.execute_query(sql)
            for_prompt_tool_list = []
            for tool in tool_list:

                data_set = {
                    "tool_name" : tool['tool_name'],
                    "tool_description" : tool['description'],
                    "api_body" : tool["api_body"]
                }
                
                for_prompt_tool_list.append(data_set)

            system_prompt = f"""
                Client Question :
                    {client_question}
                Before Result : 
                    {before_result}

                Guidelines :
                    - Look at "Client Question :" and "Before Result" and if the question is sufficiently answered, reply FINISH|FINISH|FINISH.
                    - You are an intelligent AI bot specialized in providing information about Jeonbuk University (JBNU). Users will ask questions related to JBNU, and you, as "Bot", should answer them.
                    - Please use the list of tools below to answer user questions so that responses can be generated based on your tools (you must follow up according to the response guidlines).
                    - You can use multiple tools (more than 0) and configure the tools freely, and I will ask you questions about the results of using each tool.
                    - If there is JSON in the response, avoid escaping it.
                    - If this is the first step (i.e., before_result is empty), you must select and call at least one tool before replying with FINISH|FINISH|FINISH.

                Tool list :
                    {for_prompt_tool_list}

                You Must respond as following formatt Divide based on | :
                    tool_name|api_body|Reasons for choosing this tool and summary of the process

                Ensure your response follows this format exactly. dot not use other formatt like JSON 
            """
            # print(system_prompt)

            # 요청 및 결과
            response = self.llmClient.call_llm(system_prompt, query, json.dumps(histroy_data))
            response_data = response.choices[0].message.content
            
            response_data = re.sub(r"tool_name\|api_body\|.+", "", response_data).strip()
            response_data = response_data.split("|")

            print("response_data: ",response_data)

            response_tool_name = response_data[0]
            response_api_body = response_data[1]
            response_choice_reason = response_data[2]

            if response_tool_name == "FINISH":

                return histroy_data
            else:

                sql = f"SELECT * FROM jbnu_tool_list WHERE tool_name = '{response_tool_name}'"
                tool_info = self.dbClient.execute_query(sql)[0]

                print("사용할 api_url: ", tool_info["api_url"])
                tool_call_response = requests.post(tool_info['api_url'], json = json.loads(response_api_body))
                tool_result = tool_call_response.json()['message']
                print("tool 사용 결과: ",tool_result)

                histroy_data["steps"].append({
                    "step_number": step_number,
                    "tool_name": response_tool_name,
                    "tool_input": response_api_body,
                    "tool_response": tool_result,
                    "reason": response_choice_reason
                })

                step_number += 1
                query = tool_result
                before_result = tool_result

            print("-------------------------------------------------------------------------------------------------------------")
