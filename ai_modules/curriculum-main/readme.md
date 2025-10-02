# Curriculum Recommendation & Graph Builder

> **Model & Graph-Based Department and Course Recommendation Pipeline**
>
> * OpenAI Embedding / Chat Completion API
> * FAISS-based Dense Retriever & Class Retriever
> * MySQL/MariaDB Course Metadata
> * NetworkX Graph + SVG/PNG Visualization

---

## 📁 Project Structure

```
├─ aov.py                   # Graph generation & visualization module
├─ dense_retriver.py        # Department/Course embedding index & search
├─ db/
│   └─ db_search.py         # DB connection & query wrapper
├─ dataset/
│   ├─ dataset.py           # Dataset class collection
│   └─ data/                # department, query, db configuration JSON
├─ open_ai.py               # OpenAI API utilities (Embedding, LLM query expansion)
├─ utils.py                 # Common utility functions
├─ main.py                  # **Execution entry point**
└─ result/                  # Log & graph output folder
```

---

## 🚀 Quick Start Example

```bash
python main.py \
  --openai_api_key $OPENAI_API_KEY \
  --query_prompt_path data/query_prompt.txt \
  --query_path data/val_expand_random.json \
  --department_path data/depart_info.json \
  --save_path result \
  --prerequisite_path prerequisities/result_hyun_j \
  --top_k 5 \
  --query_exp         # Use query expansion
```

After execution, the following files will be generated under `result/`:

| File/Folder                | Description                                      |
| -------------------------- | ------------------------------------------------ |
| `result.log`               | INFO logs (candidate scores, graph node counts, etc.) |
| `recommendations_*/*.svg`  | NetworkX → Graphviz rendering results           |
| `recommendations_*/*.json` | Node & edge information (original / LLM-selected / refined) |

---

## 🧩 Main Component Overview

### 1. DenseRetriever / classRetriever

| Feature              | Description                                        |
| -------------------- | -------------------------------------------------- |
| Index Building       | OpenAI Embedding → FAISS L2 index save & reuse     |
| Search (`retrieve`)  | Returns top-k similar departments/courses to query vector |
| Department Diversity | Post-processing to prevent same-department bias    |

### 2. `recursive_top1_selection()`

1. Fetch **top-1 course candidates per department** and sort by score (descending)
2. If max score < **0.43** → Stop search, only perform graph expansion
3. Select up to 2 courses from different departments and add to `already_selected_classes`
4. Expand prerequisite/postrequisite graph using `build_prereq_postreq()`
5. Recursively repeat if unvisited nodes remain

### 3. Graph Visualization

* **`visualize_and_sort_department_graphs`** – Sort department subgraphs & SVG rendering
* **`selected_edge_by_llm`** – LLM evaluates edge importance to extract subgraph

---

## 🔑 Main CLI Arguments

| Argument         | Default | Meaning                              |
| ---------------- | ------- | ------------------------------------ |
| `--query_exp`    | *False* | Whether to use expanded query (LLM)  |
| `--department_y` | *False* | GT department fixed vs. FAISS search |
| `--top_k`        | 1       | Top-k nearest departments            |

See full argument list with `python main.py -h`.

---

## 📝 Logging & Debugging Tips

* All INFO-level messages are logged in **result.log**
* `recursive_top1_selection` logs node count, max score, selected department at each step - useful for threshold (0.43) tuning
* Recommended to wrap DB connection in `finally: db_handler.close()` pattern for exception handling

---

## 🔌 FastAPI Inference Service

### Architecture Overview

```
main.py                # FastAPI app
└─ process_query()      # Korean query → recommendation pipeline invocation
```

| Step | Function              | Description                                                                     |
| ---- | --------------------- | ------------------------------------------------------------------------------- |
| 1    | **`/chat` POST**      | Receives QueryRequest (query, `required_dept_count`)                            |
| 2    | **`process_query()`** | • Query expansion → embedding<br>• Department selection → TF-IDF / GPT-Emb / graph-based recommendation<br>• Save results as JSON + graph + TXT |
| 3    | **Recursive Search**  | Build prerequisite/postrequisite connection graph using `recursive_top1_selection()` |

### Main Environment Variables & Arguments

| Name             | Default | Description                        |
| ---------------- | ------- | ---------------------------------- |
| `OPENAI_API_KEY` | –       | OpenAI Embed & Chat API token      |
| `PORT`           | 6006    | uvicorn service port               |
| `db.json`        | –       | DB connection info (host, user, pwd…) |

### Execution Example

```bash
export OPENAI_API_KEY="sk-..."
uvicorn main:app --host 0.0.0.0 --port 6006
```

#### Request

```bash
curl -X POST http://localhost:6006/chat \
     -H "Content-Type: application/json" \
     -d '{"query":"Knowledge needed for data science-based startup", "required_dept_count":30}'
```

#### Response Example (JSON)

```json
{
  "meta_info": {
    "user_query": "Knowledge needed for data science-based startup",
    "expanded_query": "...",
    "selected_departments": ["Industrial Engineering", "Business Administration"]
  },
  "recommended_courses": [
    {
      "class_id": "IE4010",
      "name": "Data Science Project",
      "department": "Industrial Engineering",
      "score": 0.91
    },
    {
      "class_id": "BA3002",
      "name": "Venture Entrepreneurship",
      "department": "Business Administration",
      "score": 0.88
    }
  ]
}
```

#### Real-time HTML Preview

Calling the `/chat/ui` endpoint renders the recommendation list directly in the browser as a table.

```bash
curl -X POST http://localhost:6006/chat/ui \
     -H "Content-Type: application/json" \
     -d '{"query":"Knowledge needed for data science-based startup", "required_dept_count":30}'
```

(The endpoint returns HTML visualized with `<table>` + department color chips.)
