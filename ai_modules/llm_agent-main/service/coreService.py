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
        history_data = {
            "steps": []
        }

        step_number = 1

        while True:
            # 1) 툴 리스트 로딩
            sql = "SELECT * FROM jbnu_tool_list"
            tool_list = self.dbClient.execute_query(sql)
            prompt_tools = [
                {
                    "tool_name": t["tool_name"],
                    "tool_description": t["description"],
                    "api_body": t["api_body"]
                }
                for t in tool_list
            ]

            # 2) 시스템 프롬프트: 항상 JSON 반환, 끝나면 FINISH JSON
            system_prompt = f"""
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


            print("response_data: ",tool_name,api_body,reason)


            if tool_name == "FINISH":

                return history_data
            else:

                sql = f"SELECT * FROM jbnu_tool_list WHERE tool_name = '{tool_name}'"
                tool_info = self.dbClient.execute_query(sql)[0]

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
