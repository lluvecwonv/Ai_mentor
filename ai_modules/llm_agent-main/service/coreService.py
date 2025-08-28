import json
import requests
import re
import tiktoken 

from util.llmClient import LlmClient
from util.dbClient import DbClient

class CoreService():
    
    def __init__(self):
        self.llmClient = LlmClient()
        self.dbClient = DbClient()
        self.dbClient.connect()

        self.prompt_tools = [
            {"tool_name": "FINISH", "tool_description": "If the user's question is already fully answered, reply with FINISH.", "api_key": "FINISH", "api_value": "<FINISH>", "api_url": "FINISH"},
            {"tool_name": "JBNU_SQL", "tool_description": "Accepts a natural‐language query about JBNU (colleges, departments, courses, professors) and returns the corresponding data. Do not send raw SQL.", "api_key": "query", "api_value": "<USER_QUESTION>", "api_url": "http://localhost:7999/agent"},
            {"tool_name": "FALLBACK", "tool_description": "Generate an answer for general or non-JBNU questions using fallback logic.", "api_key": "query", "api_value": "<USER_QUESTION>", "api_url": "http://localhost:7998/agent"},
            {"tool_name": "VECTOR_SEARCH", "tool_description": "Recommends courses similar to a given course name based on vector similarity. The 'count' defaults to 5 if the user does not specify a number.", "api_key": "count, key", "api_value": "<INTEGER_DEFAULT_5>, <COURSE_NAME>", "api_url": "http://localhost:7997/search"},
            {"tool_name": "CURRICULUM_RECOMMEND", "tool_description": "Accepts a natural-language learning goal and desired number of courses/departments, then returns a personalized curriculum recommendation.", "api_key": "query", "api_value": "<USER_GOAL>", "api_url": "http://localhost:7996/chat"}
        ]

        self.tool_urls = {t['tool_name']: t.get('api_url', t['tool_name']) for t in self.prompt_tools}

    def _trim_messages_to_fit_token_limit(self, messages: list, max_tokens: int = 8000):
        """메시지 리스트를 최신순으로 max_tokens에 맞게 잘라냅니다."""
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        token_count = 0
        trimmed_messages = []

        for msg in reversed(messages):
            # ★★★ 수정됨: 딕셔너리 접근(msg['...'])을 객체 속성 접근(msg....)으로 변경 ★★★
            msg_tokens = len(encoding.encode(msg.role)) + len(encoding.encode(msg.content)) + 10
            
            if token_count + msg_tokens > max_tokens:
                break
            
            token_count += msg_tokens
            trimmed_messages.append(msg)
        
        return list(reversed(trimmed_messages))
    
    def _build_api_body(self, api_key_str: str, api_value_str: str) -> dict:
        """
        LLM이 생성한 "key1, key2" 와 "value1, value2" 문자열을
        {"key1": "value1", "key2": value2} 딕셔너리로 파싱합니다.
        """
        api_body = {}
        if not all(isinstance(s, str) for s in [api_key_str, api_value_str]):
            return api_body

        keys = [k.strip() for k in api_key_str.split(',')]
        values = [v.strip() for v in api_value_str.split(',')]

        if len(keys) != len(values):
            print(f"Warning: Mismatched keys and values. Treating as single query.")
            return {"query": api_value_str}

        for key, value in zip(keys, values):
            # 값이 정수 형태이면 int로 변환
            if value.isdigit():
                api_body[key] = int(value)
            else:
                api_body[key] = value
        
        return api_body


    # --------------------------------------------------------------------------
    # 1. 라우터 프롬프트 (첫 번째 LLM 호출용)
    #    - 작업이 단일 단계로 끝날지, 여러 단계가 필요할지 판단
    # --------------------------------------------------------------------------
    ROUTER_SYSTEM_PROMPT = """
You are a planning agent. Your job is to analyze the user's conversation history and decide on a plan to answer their request.

You have two plans available:
1.  **single_step**: If the entire request can be resolved by calling a single tool, choose this plan.
2.  **multi_step**: If the request requires multiple tool calls or complex reasoning, choose this plan.

Based on the conversation history, return a JSON object with your plan.
- For **single_step**, specify the tool, api_key, and api_value.
- For **multi_step**, you don't need to specify a tool.

Example for single_step (DB Query):
{{
    "plan_type": "single_step",
    "tool_name": "JBNU_SQL",
    "api_key": "query",
    "api_value": "컴퓨터공학부에 대해 알려줘.",
    "reason": "The user is asking a direct question about a department."
}}

Example for single_step (Vector Search without count specified):
{{
    "plan_type": "single_step",
    "tool_name": "VECTOR_SEARCH",
    "api_key": "key, count",
    "api_value": "자료구조, 5",
    "reason": "The user wants courses similar to '자료구조' and did not specify a number, so the default of 5 is used."
}}

Example for single_step (Vector Search with count specified):
{{
    "plan_type": "single_step",
    "tool_name": "VECTOR_SEARCH",
    "api_key": "key, count",
    "api_value": "데이터베이스, 3",
    "reason": "The user specifically asked for 3 courses similar to '데이터베이스'."
}}

Example for multi_step:
{{
    "plan_type": "multi_step",
    "reason": "The user wants to find a professor, then find courses they teach."
}}

Available Tools:
{tools}

Now, create your plan. Respond strictly with a single JSON object.
"""

    # --------------------------------------------------------------------------
    # 2. ReAct 에이전트 프롬프트 (여러 번 돌리는 경우에만 사용)
    # --------------------------------------------------------------------------
    REACT_AGENT_SYSTEM_PROMPT = """
You are a sophisticated AI agent. Your primary goal is to select the most appropriate tool by analyzing the **ENTIRE conversation history** and the **Previous Tool Result**.

Your Task:
Based on the full context, choose the next single tool to use.

Guidelines:
1.  **If `Previous Tool Result` is 'INIT', you must choose exactly one tool. Do NOT return the FINISH JSON.**
2.  If the conversation goal is fully achieved, return the FINISH JSON object:
    {{"tool_name":"FINISH", "api_key": "FINISH", "api_value": "FINISH", "reason":"The user's request is fully resolved."}}
3.  Otherwise, return exactly one JSON object with the next tool to call:
    •   **tool_name**: The exact name of the tool to use.
    •   **api_key**: The key for the tool's API (e.g., "query", "key").
    •   **api_value**: The value for the tool's API (e.g., "컴퓨터공학부", "데이터베이스").
    •   **reason**: A brief rationale for this specific step.
Available Tools:
{tools}

Conversation History:
    {client_question}

Previous Tool Result:
    {before_result}

Respond strictly with a single JSON object.
"""


    def run_agent(self, messages: list):
        """
        메인 에이전트 실행 함수 (새로운 진입점)
        1. 라우터를 호출하여 계획 수립
        2. 계획에 따라 단일 실행 또는 멀티스텝 체인 실행
        """
        print("Step 1: Routing Query...")
        trimmed_messages = self._trim_messages_to_fit_token_limit(messages)
        routing_decision = self._route_query(trimmed_messages)
        plan_type = routing_decision.get("plan_type")

        if plan_type == "single_step":
            print("Plan: Single step. Executing directly.")
            print(f"tool_name:{routing_decision.get('tool_name')}, reason:{routing_decision.get('reason')}")
            tool_name = routing_decision.get("tool_name")
            api_key = routing_decision.get("api_key")
            api_value = routing_decision.get("api_value")


            tool_result_json = self._execute_single_tool(tool_name, api_key, api_value, trimmed_messages)

            api_body_for_log = self._build_api_body(api_key, api_value)

            history_data = {
                "steps": [
                    {
                        "step_number": 1,
                        "tool_name": tool_name,
                        "tool_input": api_body_for_log,
                        "tool_response": tool_result_json.get('message') or json.dumps(tool_result_json),
                        "reason": routing_decision.get('reason', 'Single step execution')
                    }
                ]
            }

            return history_data
        elif plan_type == "multi_step":
            print("Plan: Multi step. Starting ReAct chain.")
            return self._execute_multi_step_chain(trimmed_messages)
        else:
            print("Error: Could not determine a plan. Falling back to default.")
            tool_name = "FALLBACK"
            tool_result_json = self._execute_single_tool(tool_name, None, None, trimmed_messages)

            history_data = {
                "steps": [
                    {
                        "step_number": 1,
                        "tool_name": tool_name,
                        "tool_input": {"query": messages[-1].content},
                        "tool_response": tool_result_json.get('message') or json.dumps(tool_result_json),
                        "reason": "Router failed, executing fallback."
                    }
                ]
            }
            return history_data

    def _route_query(self, messages: list):
        """(내부 함수) 첫 번째 LLM 호출: 어떤 계획을 사용할지 결정"""
    
        system_prompt_for_router = self.ROUTER_SYSTEM_PROMPT.format(
            tools=json.dumps(self.prompt_tools, ensure_ascii=False, indent=2)
        )


        # ★★★ 새로운 방식으로 LLM 호출 ★★★
        request_messages = [
            {"role": "system", "content": system_prompt_for_router},
            # client_question_str_list의 각 요소를 user 메시지로 변환
            *({"role": msg.role, "content": msg.content} for msg in messages)
        ]
        # json_mode=True로 설정하여 안정적으로 JSON을 받음
        resp = self.llmClient.call_llm(request_messages, json_mode=True)
        raw = resp.choices[0].message.content.strip()

        try:
            # 이제 re.search가 필요 없을 가능성이 높지만, 안전을 위해 유지
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"plan_type": "fallback", "reason": "Failed to parse router response."}
        # json_mode=True로 설정하여 안정적으로 JSON을 받음


    def _execute_single_tool(self, tool_name: str, api_key: str, api_value: str, messages: list):
        """(내부 함수) 단일 도구를 직접 실행하고 결과를 반환"""
        if tool_name not in self.tool_urls:
            return {"error": f"Tool '{tool_name}' not found."}

        url = self.tool_urls[tool_name]

        if tool_name == "FALLBACK":
            body_to_send = {"messages": [msg.dict() for msg in messages]}
        else:
            body_to_send = self._build_api_body(api_key, api_value)

        print(f"Executing single tool: {tool_name} with body: {body_to_send}")
        
        try:
            response = requests.post(url, json=body_to_send)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def _execute_multi_step_chain(self, messages: list):
        """(내부 함수) ReAct 패턴을 사용하여 여러 단계를 거쳐 작업 수행"""
        client_question = "".join([f"- {msg.role}: {msg.content}\n" for msg in messages])
        
        before_result = 'INIT'
        history_data = {"steps": []}
        step_number = 1

        while True:
            print(f"\n--- ReAct Step {step_number} ---")
            
            system_prompt = self.REACT_AGENT_SYSTEM_PROMPT.format(
                client_question=client_question,
                before_result=before_result,
                tools=json.dumps(self.prompt_tools, ensure_ascii=False, indent=2)
            )

            request_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Based on the context, what is the next single tool to use? Provide your response in the required JSON format."}
            ]
            
            resp = self.llmClient.call_llm(
                request_messages,
                json_mode=True
            )
            raw = resp.choices[0].message.content.strip()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print("Error parsing LLM response. Breaking loop.")
                history_data['error'] = 'Failed to parse LLM response'
                break

            tool_name = data.get("tool_name", "").strip()
            api_key = data.get("api_key")
            api_value = data.get("api_value")
            # api_key와 api_value로 도구 서버가 받을 api_body 딕셔너리를 조립
            api_body = {api_key: api_value} if api_key and api_value is not None else {}
            
            reason = data.get("reason", "").strip()

            print(f"LLM Decision: Use tool '{tool_name}' because '{reason}'")

            if tool_name == "FINISH":
                print("FINISH signal received. Chain complete.")
                return history_data

            if tool_name not in self.tool_urls:
                before_result = f"Error: Tool '{tool_name}' not found. Please choose from the available tools."
                step_number += 1
                continue

            tool_result_json = self._execute_single_tool(tool_name, api_key, api_value, messages)
            tool_result = tool_result_json.get('message') or json.dumps(tool_result_json)

            history_data["steps"].append({
                "step_number": step_number, "tool_name": tool_name,
                "tool_input": api_body, "tool_response": tool_result, "reason": reason
            })

            before_result = tool_result
            step_number += 1
            if step_number > 5: # 무한 루프 방지
                print("Max steps reached. Forcing FINISH.")
                break

        return history_data