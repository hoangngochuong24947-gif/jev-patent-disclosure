#!/usr/bin/env python3
"""
patent_intake_gate.py — 专利交底材料完备性与类型评估门禁 (System-1 Patent Intake Gate)
=============================================================================
结合 TypeSafe Jev，对发明人/工程师提供的原始素材在 300ms 内完成事实完备性量规打分、
专利法定类型判决（发明/实用/外观）以及公知常识区分度初审。

用法：
  python skills/patent-disclosure/tools/patent_intake_gate.py --text "原始技术交底说明..."
  python skills/patent-disclosure/tools/patent_intake_gate.py --file path/to/brief.md
  python skills/patent-disclosure/tools/patent_intake_gate.py --mock-brief
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

DECISIONS_ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "~typesafe/jev-latest"


def resolve_openrouter_key() -> Optional[str]:
    """尝试从环境变量、.env 文件中获取 OpenRouter Key"""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key and key.startswith("sk-or-"):
        return key

    # 递归查找当前目录及父级目录中的 .env
    current = os.path.abspath(os.getcwd())
    while current != os.path.dirname(current):
        env_path = os.path.join(current, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("OPENROUTER_API_KEY="):
                            val = line.split("=", 1)[1].strip("'\" \t")
                            if val.startswith("sk-or-"):
                                return val
            except Exception:
                pass
        current = os.path.dirname(current)
    return None


def query_jev_direct(state: str, questions: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """无需外部 CLI，直接通过 Python 内置 urllib 请求 OpenRouter Jev Alpha 端点"""
    payload = {
        "model": DEFAULT_MODEL,
        "state": state,
        "questions": questions
    }
    req = urllib.request.Request(
        DECISIONS_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "jev-patent-disclosure"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("answers", {})


def query_jev(state: str, questions: Dict[str, Any]) -> Dict[str, Any]:
    """混合策略：优先使用本地 jev CLI，不存在则自愈回退到原生 HTTP API"""
    jev_path = shutil.which("jev")
    if jev_path:
        try:
            cmd = [
                jev_path, "decide",
                "--state", state,
                "--questions", json.dumps(questions, ensure_ascii=False),
                "--answers-only"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout.strip())
        except Exception:
            pass  # 回退到原生 HTTP

    api_key = resolve_openrouter_key()
    if api_key:
        try:
            return query_jev_direct(state, questions, api_key)
        except Exception as e:
            print(f"Error querying OpenRouter Decisions API: {e}", file=sys.stderr)
            sys.exit(1)

    print(
        "Error: OPENROUTER_API_KEY is not set and 'jev' CLI is not found in PATH.\n"
        "Please run: export OPENROUTER_API_KEY='sk-or-v1-...'\n"
        "Or install jev: pip install typesafe-jev",
        file=sys.stderr
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Jev-powered Patent Intake Completeness & Type Gate")
    parser.add_argument("--text", help="Raw technical description text")
    parser.add_argument("--file", help="Path to input markdown or text file")
    parser.add_argument("--mock-brief", action="store_true", help="Run with synthetic test brief")
    parser.add_argument("--json", action="store_true", help="Print raw JSON only")

    args = parser.parse_args()

    if args.mock_brief:
        input_text = """
        技术方案：一种基于多级显存缓存换入换出的高通量晶体扩散模型并行生成方法。
        背景问题：在单卡 32GB 显存下，MatterGen 扩散生成 500 个晶体结构时容易发生 CUDA OOM。
        核心机理：构建基于 Jev 快思考的启发式显存调度器，包含 Fast Prefilter 阶段的拓扑筛选，
        当显存水位达到 85% 阈值时触发异步梯度卸载与 CPU 内存交换环，交换块大小动态设定为 128MB。
        """
        source_name = "mock-brief"
    elif args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            input_text = f.read()
        source_name = os.path.basename(args.file)
    elif args.text:
        input_text = args.text
        source_name = "cli-text"
    else:
        print("Error: Must provide --text, --file, or --mock-brief.", file=sys.stderr)
        sys.exit(1)

    state_snippet = input_text[:4000].strip()

    questions = {
        "disclosure_completeness": {
            "type": "score",
            "instructions": "Evaluate the factual sufficiency and clarity of the technical disclosure",
            "criteria": [
                "Level 0: Vague concept or business idea, lacking concrete technical mechanism",
                "Level 1: Contains technical flow but lacks key parameter bounds, formulas, or system topology",
                "Level 2: Fully detailed, with verifiable technical solution, embodiments, and distinct boundary"
            ]
        },
        "patent_category": {
            "type": "choice",
            "instructions": "Determine the optimal patent application type",
            "criteria": {
                "invention": "Method, algorithmic process, neural architecture, chemical composition, or complex software flow",
                "utility_model": "Pure physical structure, circuit connection, or mechanical enclosure",
                "design": "Visual aesthetic appearance, external industrial shape, or GUI layout"
            }
        },
        "has_distinguishable_novelty": {
            "type": "noul",
            "instructions": "Does this solution present an observable distinction from standard off-the-shelf textbooks or public libraries?"
        },
        "missing_facts_checklist": {
            "type": "choice",
            "instructions": "Identify the primary missing factual element requiring inventor clarification",
            "criteria": {
                "sufficient": "No critical facts missing, ready to draft disclosure and claims",
                "missing_topology_or_figures": "Lacks block diagram, hardware structure, or UI layout",
                "missing_parameters_or_bounds": "Lacks numerical ranges, thresholds, or concrete configurations",
                "missing_algorithm_steps": "Lacks step-by-step logic flow or mathematical formulation"
            }
        }
    }

    answers = query_jev(state_snippet, questions)

    comp_score = answers.get("disclosure_completeness", {}).get("score", 0.0)
    category = answers.get("patent_category", {}).get("choice", "invention")
    novelty_prob = answers.get("has_distinguishable_novelty", {}).get("noul", 0.0)
    missing = answers.get("missing_facts_checklist", {}).get("choice", "sufficient")
    confidence = answers.get("patent_category", {}).get("confidence", 0.0)

    is_ready = comp_score >= 1.5

    result = {
        "source": source_name,
        "disclosure_completeness_score": round(comp_score, 2),
        "patent_category": category,
        "novelty_distinction_prob": round(novelty_prob, 3),
        "confidence": round(confidence, 3),
        "missing_element": missing,
        "is_ready_to_draft": is_ready,
        "action_guidance": (
            f"READY: Material sufficiency level {comp_score:.2f} >= 1.5. Proceed to Step 2–8 drafting under category '{category}'."
            if is_ready else
            f"NEEDS_FACTS: Material sufficiency level {comp_score:.2f} < 1.5. Primary gap: '{missing}'. Ask inventor for targeted facts before drafting."
        )
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"INTAKE_GATE_JSON: {json.dumps(result, ensure_ascii=False)}")
        print(f"Completeness Score : {comp_score:.2f} / 2.00")
        print(f"Patent Category    : {category} (Confidence: {confidence:.2f})")
        print(f"Novelty Prob       : {novelty_prob:.2f}")
        print(f"Missing Element    : {missing}")
        print(f"Action Guidance    : {result['action_guidance']}")

    sys.exit(0 if is_ready else 2)


if __name__ == "__main__":
    main()
