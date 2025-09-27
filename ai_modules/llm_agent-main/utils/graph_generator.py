"""
커리큘럼 그래프 생성 유틸리티
"""
import io
import base64
import re
import logging
from pathlib import Path

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import seaborn as sns

logger = logging.getLogger(__name__)

# 한글 폰트 설정
HERE = Path(__file__).resolve().parent.parent
FONT_PATH = HERE / "NanumGothic-Regular.ttf"

if FONT_PATH.exists():
    mpl.font_manager.fontManager.addfont(str(FONT_PATH))
    font_prop = fm.FontProperties(fname=str(FONT_PATH))
    mpl.rcParams['font.family'] = font_prop.get_name()
    mpl.rcParams['font.sans-serif'] = font_prop.get_name()
    mpl.rcParams['axes.unicode_minus'] = False
else:
    font_prop = None


def assign_positions(G):
    """그래프 위치 할당 - 임시 구현"""
    try:
        pos = nx.spring_layout(G, seed=42)
        semester_labels = {}
        return pos, semester_labels
    except Exception as e:
        logger.error(f"위치 할당 실패: {e}")
        return {}, {}


def generate_graph_base64(sections: dict) -> str:
    """커리큘럼 그래프 생성"""
    try:
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
        depts = sorted({G.nodes[n]["department"] for n in G.nodes()})
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
        if semester_labels:
            min_y = min(pos.values(), key=lambda v: v[1])[1]
            label_y = min_y - 0.4

            for sem, (x, _) in semester_labels.items():
                plt.text(
                    x, label_y,
                    sem.replace("학기_", ""),
                    fontproperties=font_prop,
                    fontsize=11,
                    fontweight='bold',
                    ha='center'
                )

        # 6) 범례
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

    except Exception as e:
        logger.error(f"그래프 생성 실패: {e}")
        raise Exception(f"그래프 생성 실패: {str(e)}")