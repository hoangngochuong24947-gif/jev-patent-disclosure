#!/usr/bin/env python3
"""
demo_jev_intake_comparison.py — Demonstrates Jev System-1 vs Traditional LLM Hallucination Trap
================================================================================================
Shows how Jev intercepts vague materials and generates targeted fact checklists
instead of allowing the LLM to hallucinate fake patent features.

Usage:
    python3 examples/demo_jev_intake_comparison.py
"""

import os
import sys
import subprocess
import json

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "skills", "patent-disclosure", "tools", "patent_intake_gate.py")

CASE_VAGUE = """
我们做了一个基于人工智能的大模型显存优化方案。通过某种算法把显存动态换入换出，
从而在单卡上训练超大模型，效果非常好，节省了很多显存。
"""

CASE_DETAILED = """
技术方案：一种用于扩散生成模型的高通量拓扑显存动态卸载方法。
硬件拓扑：PCIe 4.0 x16 互连，主控为 24GB VRAM GPU 与 128GB Host RAM。
核心步骤：
1. 监控线程以 10ms 周期采集 GPU 显存水位；
2. 当显存占用超过阈值 88% 时，拦截当前层的前向激活张量计算；
3. 将非活跃层的权重张量分块（Chunk size 64MB）通过异步 CUDA Stream 流水线卸载至 Host RAM；
4. 当反向传播到达该层前 5ms，触发预取指令换入显存。
对比实验证明显存峰值降低 42%，吞吐量保持在 91% 以上。
"""

def run_gate(text: str, label: str):
    print("=" * 70)
    print(f"CASE: {label}")
    print("-" * 70)
    print(f"Input Text Snippet:\n{text.strip()}")
    print("\n>>> Calling Jev System-1 Patent Intake Gate (< 300ms)...")

    cmd = [sys.executable, SCRIPT_PATH, "--text", text, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    try:
        data = json.loads(proc.stdout.strip())
        print(f"[*] Factual Completeness : {data['disclosure_completeness_score']} / 2.00")
        print(f"[*] Patent Category      : {data['patent_category']} (Conf: {data['confidence']})")
        print(f"[*] Novelty Probability  : {data['novelty_distinction_prob']}")
        print(f"[*] Missing Element      : {data['missing_element']}")
        print(f"[*] Decision & Guidance  : {data['action_guidance']}")
        print(f"[*] Exit Code            : {proc.returncode} ({'APPROVED' if proc.returncode == 0 else 'HARD INTERCEPT'})")
    except Exception as e:
        print(f"[!] Output: {proc.stdout}\n[!] Error: {proc.stderr or e}")
    print("\n")

def main():
    print("#####################################################################")
    print("  jev-patent-disclosure — Intake Gate & Anti-Hallucination Demo      ")
    print("#####################################################################\n")

    run_gate(CASE_VAGUE, "案例 A: 粗糙概念性材料 (传统 LLM 必产生严重技术脑补与虚构)")
    run_gate(CASE_DETAILED, "案例 B: 完备工程实施例 (包含清晰物理边界、阈值与时序)")

if __name__ == "__main__":
    main()
