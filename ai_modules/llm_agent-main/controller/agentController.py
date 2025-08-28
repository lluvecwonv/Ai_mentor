from typing import List
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import traceback
import re, io, base64
from pathlib import Path

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import seaborn as sns

from service.coreService import CoreService
from aov import assign_positions

from util.llmClient import LlmClient

router = APIRouter()
core_service = CoreService()
llm_client    = LlmClient()

class Message(BaseModel):
    role: str
    content: str

class RequestBody(BaseModel):
    stream: bool
    model: str
    messages: List[Message]

# — 한글 폰트 설정 (NanumGothic) — 
HERE      = Path(__file__).resolve().parent.parent
FONT_PATH = HERE / "NanumGothic-Regular.ttf"

if FONT_PATH.exists():
    mpl.font_manager.fontManager.addfont(str(FONT_PATH))
    # font_prop 을 전역으로 보관
    font_prop = fm.FontProperties(fname=str(FONT_PATH))
    # rcParams 에 등록
    mpl.rcParams['font.family']        = font_prop.get_name()
    mpl.rcParams['font.sans-serif']    = font_prop.get_name()
    mpl.rcParams['axes.unicode_minus'] = False
else:
    font_prop = None  # 폰트가 없으면 None

def format_sse(data: str) -> str:
    # 각 줄을 'data: …' 로 감싸고, '\n\n' 으로 이벤트 종료
    return "".join(f"data: {line}\n" for line in data.splitlines()) + "\n\n"

def parse_course_sections_with_preamble(text: str) -> dict:
    parts = re.split(r'^===\s*(.+?)\s*===\s*$', text, flags=re.MULTILINE)
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
            elif re.match(r'^\d+학년\s*\d+학기$', L):
                curr["학년·학기"] = L
            elif L.startswith("선수과목:"):
                curr["선수과목"] = L.split(":",1)[1].strip()
        if curr:
            courses.append(curr)
        result[dept] = courses

    return result

# … (폰트 설정, import 등 생략) …

def generate_graph_base64(sections: dict) -> str:
    # 1) DiGraph 생성
    G = nx.DiGraph()
    allowed = {c["강좌명"] for lst in sections.values() for c in lst}

    for dept, lst in sections.items():
        for c in lst:
            name = c["강좌명"]
            m = re.match(r'(\d+)학년\s*(\d+)학기', c.get("학년·학기",""))
            grade, sem = (m.group(1), m.group(2)) if m else ("","")
            G.add_node(name,
                       department=dept,
                       student_grade=grade,
                       semester=sem)

        for c in lst:
            tgt = c["강좌명"]
            for p in filter(None, map(str.strip, c.get("선수과목","").split(","))):
                if p in allowed:
                    G.add_edge(p, tgt)

    # 2) 위치 계산
    pos, semester_labels = assign_positions(G)
    missing = [n for n in G.nodes() if n not in pos]
    if missing:
        spring = nx.spring_layout(G, seed=42)
        for n in missing:
            pos[n] = spring[n]

    # 3) 색상 매핑
    depts   = sorted({G.nodes[n]["department"] for n in G.nodes()})
    palette = sns.color_palette("Set3", n_colors=len(depts))
    color_map = {d: palette[i] for i, d in enumerate(depts)}
    node_colors = [color_map[G.nodes[n]["department"]] for n in G.nodes()]

    # 4) 그리기
    plt.figure(figsize=(12,8))
    nx.draw_networkx_nodes(
        G, pos,
        node_size=800,
        node_color=node_colors,
        edgecolors="black",
        linewidths=1.0
    )
    nx.draw_networkx_edges(
        G, pos,
        arrowstyle='-|>',
        arrowsize=8,
        width=1.0,
        edge_color='gray'
    )
    # 노드 라벨 (한글 폰트 적용)
    nx.draw_networkx_labels(
        G, pos,
        labels={n: n for n in G.nodes()},
        font_size=8,
        font_color='black',
        font_family=font_prop.get_name() if font_prop else 'sans-serif',
        font_weight='normal',
        alpha=None,
        verticalalignment='center',
        horizontalalignment='center'
    )

    # 5) 학기 레이블
    # 최하단 y좌표 계산
    min_y = min(pos.values(), key=lambda v: v[1])[1]
    label_y = min_y - 0.4  # 학기 텍스트를 그 아래로

    # 학기 레이블 출력 (위치 y는 고정)
    for sem, (x, _) in semester_labels.items():
        plt.text(
            x, label_y,
            sem.replace("학기_", ""),
            fontproperties=font_prop,
            fontsize=11,
            fontweight='bold',
            ha='center'
        )

    # 6) 범례 (한글 폰트 적용)
    patches = [
        plt.Line2D([0],[0], marker='o', color='w',
                   markerfacecolor=color_map[d],
                   markeredgecolor='black',
                   markersize=12, label=d)
        for d in depts
    ]
    plt.legend(
        handles=patches,
        title="학과별 색상",
        prop=font_prop,
        loc="upper right"
    )

    plt.axis('off')
    plt.tight_layout()

    # 7) PNG → base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')



@router.post("/agent")
async def agent_api(request_body: RequestBody) -> JSONResponse:

    history = core_service.run_agent(request_body.messages)
    step = history["steps"][-1]
    raw  = step["tool_response"]
    final = raw
    image_md =""

    
    if step["tool_name"] == "CURRICULUM_RECOMMEND":
        try:
            parsed   = parse_course_sections_with_preamble(raw)
            final = parsed.pop("preamble", "")
            graph_b64 = generate_graph_base64(parsed)
            image_md = f"data: ![Curriculum Graph](data:image/png;base64,{graph_b64})"
            

            # final = f"{preamble}\n\n![Curriculum Graph](data:image/png;base64,{graph_b64})"
        except Exception:
            tb = traceback.format_exc()
            print("🚨 /agent 예외:\n", tb)
            return JSONResponse(status_code=500,
                                content={"error":"그래프 생성 실패","trace":tb})


    # 2) 이제 번역 단계: stream 여부 따라 분기
    # if request_body.stream:
    #     def event_gen():
    #         for chunk in llm_client.chat(final, stream=True):
    #             delta = chunk.choices[0].delta
    #             if delta.content:
    #                 yield delta.content
    #         # 번역 텍스트가 다 내려간 뒤, 이미지 마크다운을 그대로 추가
    #         yield format_sse(image_md)

    #     return StreamingResponse(event_gen(), media_type="text/event-stream")

    # # 비스트리밍 모드
    # resp       = llm_client.chat(final, stream=False)
    # translated = resp.choices[0].message.content
    # content    = f"{translated}{image_md}"

    content    = f"{final}{image_md}"
    return JSONResponse({
        "choices": [{
            "index": 0,
            "message": {"role":"assistant","content": content},
            "finish_reason":"stop"
       }]
    })

