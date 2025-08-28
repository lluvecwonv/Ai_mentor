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

    def dynamic_tool_chain(self, messages: list):
        client_question = ""
        for msg in messages:
            # msg는 {"role": "user", "content": "안녕하세요"} 형태의 딕셔너리라고 가정
            client_question += f"- {msg['role']}: {msg['content']}\n"

        last_query = messages[-1]['content']

        prompt_tools = [
                {'tool_name': 'FINISH', 
                 'tool_description': "If the user's question is already fully answered, reply with FINISH|FINISH|FINISH.", 
                 'api_body': 'FINISH', 
                 'api_url': 'FINISH'},
                {'tool_name': 'JBNU_SQL', 
                 'tool_description': 'Accepts a natural‐language query about JBNU (colleges, departments, courses, professors) and returns the corresponding data. Do not send raw SQL.', 
                 'api_body': '{"query": "<USER_QUESTION>"}', 
                 'api_url': 'http://localhost:7999/agent'},
                {'tool_name': 'FALLBACK', 
                 'tool_description': 'Generate an answer for general or non-JBNU questions using fallback logic.', 
                 'api_body': '{"query": "<USER_QUESTION>"}', 
                 'api_url': 'http://localhost:7998/agent'},
                {'tool_name': 'VECTOR_SEARCH', 
                 'tool_description': 'Recommend up to 5 courses similar to the given course name based on vector similarity.', 
                 'api_body': '{"count": <INT>, "key": "<COURSE_NAME>"}', 
                 'api_url': 'http://localhost:7997/agent'},
                {'tool_name': 'CURRICULUM_RECOMMEND', 
                 'tool_description': 'Accepts a natural-language learning goal and desired number of courses/departments, then returns a personalized curriculum recommendation.', 
                 'api_body': '{"query": "<USER_GOAL>"}', 
                 'api_url': 'http://localhost:7996/agent'}
            ]
        

        ##client_question = query
        
        before_result = 'INIT'
        history_data = {
            "steps": []
        }

        step_number = 1

        while True:
            # 1) 툴 리스트 로딩
            # sql = "SELECT * FROM jbnu_tool_list"
            # tool_list = self.dbClient.execute_query(sql)
            # prompt_tools = [
            #     {
            #         "tool_name": t["tool_name"],
            #         "tool_description": t["description"],
            #         "api_body": t["api_body"]
            #     }
            #     for t in tool_list
            # ]

            
            api_url = {"FINISH":"FINISH","JBNU_SQL":"http://localhost:7999/agent","FALLBACK":"http://localhost:7998/agent",
                       "VECTOR_SEARCH":"http://localhost:7997/agent","CURRICULUM_RECOMMEND":"http://localhost:7996/agent"}
            # 2) 시스템 프롬프트: 항상 JSON 반환, 끝나면 FINISH JSON
            system_prompt = f"""
            
You are a sophisticated AI agent. Your primary goal is to select the most appropriate tool by analyzing the **ENTIRE conversation history** provided below, not just the last message.

Conversation History:
    {client_question}

Previous Tool Result:
    {before_result}

Your Task:
Based on the full conversation context and the result from the previous step, choose the next tool to use.

Guidelines:
1.  **Analyze the full `Conversation History`** to understand the user's ultimate goal. The latest message might be ambiguous (e.g., "what about that one?"), so use previous messages to resolve references.
2.  If `Previous Tool Result` is 'INIT', you must choose exactly one tool. Do not choose FINISH.
3.  If the conversation goal is fully achieved based on the history and previous results, return the FINISH JSON object and nothing else:
    {{"tool_name":"FINISH","api_body":"FINISH","reason":"The user's request has been fully resolved."}}
4.  Otherwise, return exactly one JSON object (no markdown fences, no extra text) with these keys:
    •   **tool_name**: The exact name of the tool to use.
    •   **api_body**: A valid JSON string for the tool's API. Use information from the conversation history to fill in the parameters.
    •   **reason**: A brief rationale explaining why you chose this tool based on the conversation context.

Available Tools:

Client Question:
    {client_question}
Before Result:
    {before_result}

Guidelines:
1. If Before Result is 'INIT', choose exactly one tool; do NOT return FINISH JSON.
2. Otherwise, if fully answered, return exactly this JSON (no fences, no extra text):
{{"tool_name":"FINISH","api_body":"FINISH","reason":"FINISH"}}
3. Else return exactly one JSON object (no fences, no text) with keys:
   • tool_name: exact tool name
   • api_body: valid JSON string
   • reason: brief rationale (don’t repeat tool name)

Tool list:
{json.dumps(prompt_tools, ensure_ascii=False, indent=2)}

Respond strictly with a single JSON object.
"""
           
            # 3) LLM 호출
            resp = self.llmClient.call_llm(
                system_prompt,
                query,
                json.dumps(history_data, ensure_ascii=False)
            )
            raw = resp.choices[0].message.content.strip()
            # 4) JSON 방어적 파싱
            m = re.search(r'\{[\s\S]*\}', raw)
            json_str = m.group(0) if m else raw
            data = json.loads(json_str)
            # 5) 값 추출 및 FINISH 처리
            tool_name = data.get("tool_name", "").strip()
            api_body  = data.get("api_body", "").strip()
            reason    = data.get("reason", "").strip()


            print(f"response_data: ,tool_name:{tool_name},api_body:{api_body},reason:{reason}")


            if tool_name == "FINISH":

                return history_data
            else:

                # sql = f"SELECT * FROM jbnu_tool_list WHERE tool_name = '{tool_name}'"
                # tool_info = self.dbClient.execute_query(sql)[0]

                
                desc = None
                url = None

                for t in prompt_tools:
                    if t.get("tool_name") == tool_name:
                        desc = t.get("tool_description")
                        url = t.get("api_url")
                        break

                tool_info = {"api_url":url,"description":desc}

                print("사용할 api_url: ", tool_info["api_url"])
                tool_call_response = requests.post(tool_info['api_url'], json = json.loads(api_body))
                tool_result = tool_call_response.json()['message']
                print("tool 사용 결과: ",tool_result)

                history_data["steps"].append({
                    "step_number": step_number,
                    "tool_name": tool_name,
                    "tool_description": tool_info["description"],
                    "tool_input": api_body,
                    "tool_response": tool_result,
                    "reason": reason
                })

                step_number += 1
                query = tool_result
                before_result = tool_result

            print("-------------------------------------------------------------------------------------------------------------")
