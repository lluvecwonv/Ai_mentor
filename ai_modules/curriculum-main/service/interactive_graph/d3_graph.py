import json


def create_interactive_graph_html(department_graphs):
    """D3.js를 사용한 인터랙티브 그래프 HTML 생성"""

    # 그래프 데이터를 JSON으로 변환
    nodes = []
    edges = []
    node_id_map = {}

    for department, G in department_graphs.items():
        for node, node_data in G.nodes(data=True):
            if node not in node_id_map:
                node_id_map[node] = len(nodes)
                nodes.append({
                    "id": str(node),
                    "name": node_data.get("class_name", "Unknown"),
                    "department": node_data.get("department", "Unknown"),
                    "grade": str(node_data.get("student_grade", "")),
                    "semester": str(node_data.get("semester", "")),
                    "description": node_data.get("description", "")
                })

        for source, target in G.edges():
            edges.append({
                "source": str(source),
                "target": str(target)
            })

    html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #FAFAFA;
        }}
        #graph {{
            width: 100%;
            height: 800px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .node {{
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .node:hover {{
            filter: brightness(1.1);
        }}
        .node circle {{
            stroke: white;
            stroke-width: 4px;
        }}
        .node text {{
            font-size: 12px;
            font-weight: bold;
            fill: white;
            text-anchor: middle;
            pointer-events: none;
        }}
        .link {{
            stroke: #BDBDBD;
            stroke-width: 3px;
            fill: none;
            marker-end: url(#arrowhead);
        }}
        .semester-label {{
            font-size: 16px;
            font-weight: bold;
            fill: #424242;
            text-anchor: middle;
        }}
        .tooltip {{
            position: absolute;
            padding: 12px;
            background: white;
            border: 2px solid #2196F3;
            border-radius: 8px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 300px;
            z-index: 1000;
        }}
        .tooltip.show {{
            opacity: 1;
        }}
        .tooltip-title {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
            color: #2196F3;
        }}
        .tooltip-content {{
            font-size: 12px;
            color: #666;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const data = {{
            nodes: {nodes_json},
            links: {edges_json}
        }};

        const width = document.getElementById('graph').clientWidth;
        const height = 800;

        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        // 화살표 정의
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 25)
            .attr("refY", 0)
            .attr("markerWidth", 8)
            .attr("markerHeight", 8)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#BDBDBD");

        // 학과별 색상
        const departments = [...new Set(data.nodes.map(d => d.department))];
        const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'];
        const colorScale = d3.scaleOrdinal()
            .domain(departments)
            .range(colors);

        // 학기별 x 좌표 계산
        const semesterMap = {{}};
        const semesters = ['1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2'];
        semesters.forEach((sem, i) => {{
            semesterMap[sem] = (i + 1) * (width / (semesters.length + 1));
        }});

        // 학기별로 노드 그룹화
        const nodesBySemester = {{}};
        data.nodes.forEach(node => {{
            const semKey = `${{node.grade}}-${{node.semester}}`;
            if (!nodesBySemester[semKey]) {{
                nodesBySemester[semKey] = [];
            }}
            nodesBySemester[semKey].push(node);
        }});

        // 연결된 노드 찾기
        const getConnectedNodes = (nodeId) => {{
            const connected = new Set();
            data.links.forEach(link => {{
                if (link.source === nodeId) connected.add(link.target);
                if (link.target === nodeId) connected.add(link.source);
            }});
            return connected;
        }};

        // 7개 이상인 학기의 과목을 재배치
        Object.entries(nodesBySemester).forEach(([semKey, nodes]) => {{
            if (nodes.length > 7) {{
                const [grade, semester] = semKey.split('-');
                const nextGrade = parseInt(grade) + 1;
                const nextSemKey = `${{nextGrade}}-${{semester}}`;

                // 연결되지 않은 노드 찾기
                const unconnectedNodes = [];
                const connectedNodes = [];

                nodes.forEach(node => {{
                    const connections = getConnectedNodes(node.id);
                    if (connections.size === 0) {{
                        unconnectedNodes.push(node);
                    }} else {{
                        connectedNodes.push(node);
                    }}
                }});

                // 7개를 초과하는 연결되지 않은 노드를 다음 학년으로 이동
                const toMove = Math.max(0, nodes.length - 7);
                const movedNodes = unconnectedNodes.splice(0, toMove);

                if (movedNodes.length > 0) {{
                    // 이동된 노드의 학년/학기 업데이트
                    movedNodes.forEach(node => {{
                        node.grade = String(nextGrade);
                        node.semester = semester;
                    }});

                    // 다음 학기 그룹에 추가
                    if (!nodesBySemester[nextSemKey]) {{
                        nodesBySemester[nextSemKey] = [];
                    }}
                    nodesBySemester[nextSemKey].push(...movedNodes);

                    // 원래 학기에서 제거
                    nodesBySemester[semKey] = [...connectedNodes, ...unconnectedNodes];
                }}
            }}
        }});

        // 각 학기의 노드들을 세로로 균등 배치
        Object.entries(nodesBySemester).forEach(([semKey, nodes]) => {{
            const xPos = semesterMap[semKey] || width / 2;
            const spacing = 70;
            const startY = 150;

            nodes.forEach((node, i) => {{
                node.x = xPos;
                node.y = startY + i * spacing;
            }});
        }});

        // 링크 그리기
        const link = svg.selectAll(".link")
            .data(data.links)
            .enter().append("path")
            .attr("class", "link")
            .attr("d", d => {{
                const source = data.nodes.find(n => n.id === d.source);
                const target = data.nodes.find(n => n.id === d.target);
                if (!source || !target) return "";
                return `M${{source.x}},${{source.y}}L${{target.x}},${{target.y}}`;
            }});

        // 노드 그룹
        const node = svg.selectAll(".node")
            .data(data.nodes)
            .enter().append("g")
            .attr("class", "node")
            .attr("transform", d => `translate(${{d.x}},${{d.y}})`);

        // 노드 원
        node.append("circle")
            .attr("r", 35)
            .attr("fill", d => colorScale(d.department));

        // 노드 텍스트
        node.append("text")
            .text(d => d.name.length > 8 ? d.name.substring(0, 7) + '...' : d.name)
            .attr("dy", 5);

        // 학기 라벨
        Object.entries(semesterMap).forEach(([sem, x]) => {{
            const [grade, semester] = sem.split('-');
            if (nodesBySemester[sem] && nodesBySemester[sem].length > 0) {{
                svg.append("rect")
                    .attr("x", x - 60)
                    .attr("y", 20)
                    .attr("width", 120)
                    .attr("height", 40)
                    .attr("fill", "#E3F2FD")
                    .attr("stroke", "#2196F3")
                    .attr("stroke-width", 2)
                    .attr("rx", 8);

                svg.append("text")
                    .attr("class", "semester-label")
                    .attr("x", x)
                    .attr("y", 45)
                    .text(`${{grade}}학년 ${{semester}}학기`);
            }}
        }});

        // 툴팁
        const tooltip = d3.select("#tooltip");

        node.on("mouseenter", function(event, d) {{
            tooltip.html(`
                <div class="tooltip-title">${{d.name}}</div>
                <div class="tooltip-content">
                    <strong>학과:</strong> ${{d.department}}<br>
                    <strong>이수 시기:</strong> ${{d.grade}}학년 ${{d.semester}}학기<br>
                    <strong>설명:</strong> ${{d.description || '정보 없음'}}
                </div>
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY + 10) + "px")
            .classed("show", true);
        }})
        .on("mouseleave", function() {{
            tooltip.classed("show", false);
        }});

        // 범례
        const legend = svg.append("g")
            .attr("transform", `translate(${{width - 150}}, 100)`);

        departments.forEach((dept, i) => {{
            const legendRow = legend.append("g")
                .attr("transform", `translate(0, ${{i * 25}})`);

            legendRow.append("circle")
                .attr("r", 8)
                .attr("fill", colorScale(dept))
                .attr("stroke", "white")
                .attr("stroke-width", 2);

            legendRow.append("text")
                .attr("x", 15)
                .attr("y", 5)
                .text(dept)
                .style("font-size", "12px")
                .style("fill", "#424242");
        }});
    </script>
</body>
</html>
    """

    html_content = html_template.format(
        nodes_json=json.dumps(nodes, ensure_ascii=False),
        edges_json=json.dumps(edges, ensure_ascii=False)
    )

    return html_content