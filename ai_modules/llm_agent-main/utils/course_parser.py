"""
과목 정보 파싱 유틸리티
"""
import re


def parse_course_sections_with_preamble(text: str) -> dict:
    """과목 섹션 파싱"""
    parts = re.split(r'^===\s*(.+?)\s*===\s*', text, flags=re.MULTILINE)
    result = {"preamble": parts[0].strip()}

    for i in range(1, len(parts), 2):
        dept = parts[i].strip()
        body = parts[i+1]
        lines = [L.strip() for L in body.splitlines() if L.strip()]

        courses = []
        curr = {}
        for L in lines:
            if L.startswith("강좌명:"):
                if curr:
                    courses.append(curr)
                curr = {"강좌명": L.split(":",1)[1].strip()}
            elif re.match(r'^\d+학년\s*\d+학기', L):
                curr["학년·학기"] = L
            elif L.startswith("선수과목:"):
                curr["선수과목"] = L.split(":",1)[1].strip()

        if curr:
            courses.append(curr)
        result[dept] = courses

    return result