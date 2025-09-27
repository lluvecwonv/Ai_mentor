import json
import logging

logger = logging.getLogger(__name__)


def parse_llm_json_response(response_text: str) -> dict:
    """LLM 응답에서 JSON 데이터를 추출하고 파싱"""
    try:
        # JSON 블록 추출 (```json...``` 형태 처리)
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            # 첫 번째 { 부터 마지막 } 까지 추출
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("JSON 구조를 찾을 수 없음", response_text, 0)
            json_text = response_text[start:end]

        result = json.loads(json_text)
        logger.debug(f"✅ JSON 파싱 성공")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 실패: {e}")
        logger.error(f"원본 응답: {response_text}")
        return {}
    except Exception as e:
        logger.error(f"❌ JSON 추출 실패: {e}")
        return {}


def extract_sql_query_from_llm_response(response_text: str) -> str:
    """LLM 응답에서 SQL 쿼리와 추론 정보를 추출"""
    result = parse_llm_json_response(response_text)

    if not result:
        return None

    sql_query = result.get("sql_query")
    reasoning = result.get("reasoning", "")

    if sql_query and sql_query.lower() != "null":
        logger.info(f"✅ [SQL필터] SQL 쿼리 생성 완료")
        logger.info(f"📋 [SQL필터] 생성된 쿼리: {sql_query}")
        logger.info(f"💭 [SQL필터] 생성 이유: {reasoning}")
        return sql_query
    else:
        logger.info(f"ℹ️ [SQL필터] SQL 필터링 불필요")
        logger.info(f"💭 [SQL필터] 이유: {reasoning}")
        return None