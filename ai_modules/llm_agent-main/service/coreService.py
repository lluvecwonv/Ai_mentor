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
        before_result = 'INIT'
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
                1. If Before Result is 'INIT', that means this is the **first tool-calling step**.
                - In this case, you MUST choose exactly one tool from the list below.
                - NEVER reply with FINISH|FINISH|FINISH at the first step.
                2. After the first step, if the user's question has been fully answered by your previous tool call, reply:
                    FINISH|FINISH|FINISH
                and stop — do not call any more tools.
                3. Otherwise, choose exactly one tool and respond with one line in the format:
                    tool_name|api_body|reason
                - tool_name must match exactly one from the tool list.
                - api_body must be a valid JSON string.
                - reason should be brief and NOT repeat the tool name.
                4. DO NOT include extra `|` characters in any of the three fields.

                Tool list:
                    {for_prompt_tool_list}

                Respond strictly using only one of the two allowed forms above.
                """

            # print(system_prompt)

            # 요청 및 결과
            response = self.llmClient.call_llm(system_prompt, query, json.dumps(histroy_data))
            response_data = response.choices[0].message.content
            
            response_data = re.sub(r"tool_name\|api_body\|.+", "", response_data).strip()
            response_data = response_data.split("|", 2)
            response_tool_name, response_api_body, response_choice_reason = (
                part.strip() for part in response_data
            )

            print("response_data: ",response_data)


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
                    "tool_description": tool_info["description"],
                    "tool_input": response_api_body,
                    "tool_response": tool_result,
                    "reason": response_choice_reason
                })

                step_number += 1
                query = tool_result
                before_result = tool_result

            print("-------------------------------------------------------------------------------------------------------------")
