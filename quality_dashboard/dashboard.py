#!/usr/bin/env python3
"""
Quality Dashboard - 品質監控儀表板
追蹤技術債趨勢、熱點圖、進化報告

Usage:
    python3 dashboard.py                    # 執行評估 + 產生 HTML
    python3 dashboard.py --report          # 顯示進化報告
    python3 dashboard.py --trend           # 顯示趨勢圖
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import statistics

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DimensionScore:
    name: str
    score: float
    weight: float
    issues: List[str] = field(default_factory=list)
    tool_driven: bool = True
    tool_name: str = ""
    
@dataclass
class IterationResult:
    iteration: int
    timestamp: str
    dimensions: Dict[str, DimensionScore]
    total_score: float
    technical_debt: float
    hotspots: Dict[str, float] = field(default_factory=dict)
    improvements: List[str] = field(default_factory=list)
    agent_actions: List[str] = field(default_factory=list)

# ============================================================================
# TOOL-DRIVEN EVALUATORS
# ============================================================================

def run_tool(cmd: List[str], timeout: int = 30, cwd: str = None) -> tuple:
    """執行工具並返回 (stdout, stderr, returncode)"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

class LintingEvaluator:
    name = "Linting"
    weight = 0.10
    
    def evaluate(self, project_path: str) -> DimensionScore:
        stdout, _, rc = run_tool(["ruff", "check", f"{project_path}/03-development/src", "--ignore=D100,E501,F401"])
        error_count = len([l for l in stdout.split('\n') if l.strip() and l.startswith('F')])
        score = max(0, 100 - error_count * 5)
        issues = [l.strip() for l in stdout.split('\n') if l.strip() and l.startswith('F')][:5]
        return DimensionScore(self.name, score, self.weight, issues, True, "ruff")

class TypeSafetyEvaluator:
    name = "Type Safety"
    weight = 0.15
    
    def evaluate(self, project_path: str) -> DimensionScore:
        stdout, _, rc = run_tool(["mypy", f"{project_path}/03-development/src", "--ignore-missing-imports", "--no-error-summary"], timeout=60)
        error_count = stdout.count(": error:")
        score = max(0, 100 - error_count * 10)
        issues = [l.strip() for l in stdout.split('\n') if ': error:' in l][:5]
        return DimensionScore(self.name, score, self.weight, issues, True, "mypy")

class CoverageEvaluator:
    name = "Test Coverage"
    weight = 0.20
    
    def evaluate(self, project_path: str) -> DimensionScore:
        # Use 03-development/tests (not project-root/tests symlink) to avoid duplicate collection
        stdout, _, rc = run_tool(["python3", "-m", "pytest", f"{project_path}/03-development/tests",
                                 "--cov=src", "--cov-report=term-missing", "--tb=no", "-q"],
                                timeout=60, cwd=project_path)
        coverage = 0
        for line in stdout.split('\n'):
            if 'TOTAL' in line:
                parts = line.replace('%', ' ').split()
                # Find the coverage percentage (last number in TOTAL line)
                nums = [float(p) for p in parts if p.replace('.', '').isdigit()]
                if nums:
                    coverage = nums[-1]  # Last number is percentage
        issues = [] if coverage >= 70 else [f"Coverage {coverage:.0f}% < 70%"]
        return DimensionScore(self.name, coverage, self.weight, issues, True, "pytest-cov")

class SecurityEvaluator:
    name = "Security"
    weight = 0.15
    
    def evaluate(self, project_path: str) -> DimensionScore:
        stdout, _, rc = run_tool(["bandit", "-r", f"{project_path}/03-development/src", "-f", "json", "-ll"], timeout=60)
        try:
            data = json.loads(stdout)
            high = data["metrics"]["_totals"]["SEVERITY.HIGH"]
            medium = data["metrics"]["_totals"]["SEVERITY.MEDIUM"]
            score = max(0, 100 - high * 20 - medium * 10)
            issues = [f"HIGH: {high}", f"MEDIUM: {medium}"]
        except:
            score = 100
            issues = ["No issues found"]
        return DimensionScore(self.name, score, self.weight, issues, True, "bandit")

class ComplexityEvaluator:
    name = "Complexity"
    weight = 0.10
    
    def evaluate(self, project_path: str) -> DimensionScore:
        # Only analyze src, not tests
        src_path = f"{project_path}/03-development/src"
        stdout, _, rc = run_tool(["lizard", src_path, "-L", "15"], timeout=30)
        hotspots = {}
        for line in stdout.split('\n'):
            if '.py' in line and 'location' not in line and line.strip():
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        cc = int(parts[1])
                        loc = parts[-1]  # e.g. func@110-255@path/to/file.py
                        # Extract file path: parts[-1].split('@')[-1] = path/to/file.py
                        # We want just the module path like src/processing/ssml_parser.py
                        file_path = '/'.join(loc.split('@')[-1].split('/')[3:])  # skip 03-development/src/
                        if cc > 15:
                            hotspots[file_path] = cc
                    except:
                        continue
        avg_cc = statistics.mean(hotspots.values()) if hotspots else 0
        score = max(0, 100 - avg_cc * 5)
        issues = [f"CC > 15: {k}" for k in list(hotspots.keys())[:3]]
        return DimensionScore(self.name, min(100, score), self.weight, issues, False, "lizard")

# ============================================================================
# AGENT-DRIVEN EVALUATORS (需要 LLM 或人工)
# ============================================================================

class ArchitectureEvaluator:
    name = "Architecture"
    weight = 0.10
    
    def evaluate(self, project_path: str) -> DimensionScore:
        # Only analyze src, not tests
        src_path = f"{project_path}/03-development/src"
        stdout, _, rc = run_tool(["radon", "cc", src_path, "-a"], timeout=30)
        # Only calculate C/D/E as issues, A/B are good quality
        issues = [l.strip() for l in stdout.split('\n') if ' - C' in l or ' - D' in l or ' - E' in l][:3]
        score = max(0, 100 - len(issues) * 10)
        return DimensionScore(self.name, score, self.weight, issues if issues else ["No major issues"], False, "radon")

class ReadabilityEvaluator:
    name = "Readability"
    weight = 0.10
    
    def evaluate(self, project_path: str) -> DimensionScore:
        # 靜態指標：平均函數長度、註釋密度
        stdout, _, rc = run_tool(["grep", "-r", "-h", '"""', project_path, "--include=*.py"], timeout=30)
        doc_count = len([l for l in stdout.split('\n') if l.strip()])
        stdout2, _, _ = run_tool(["find", project_path, "-name", "*.py"], timeout=10)
        total = len([l for l in stdout2.split('\n') if l.strip() and '.py' in l])
        ratio = (doc_count / max(total, 1)) * 100
        score = min(100, ratio * 2)  # 粗略估算
        issues = [f"{doc_count}/{total} files with docstrings (estimate)"]
        return DimensionScore(self.name, score, self.weight, issues, False, "agent")

class ErrorHandlingEvaluator:
    name = "Error Handling"
    weight = 0.05
    
    def evaluate(self, project_path: str) -> DimensionScore:
        stdout, _, rc = run_tool(["grep", "-r", "-c", "except", project_path, "--include=*.py"], timeout=30)
        catch_count = 0
        for line in stdout.split('\n'):
            if ':' in line:
                try:
                    catch_count += int(line.split(':')[1])
                except:
                    continue
        score = min(100, 50 + catch_count * 2)
        issues = [f"{catch_count} try-except blocks found"]
        return DimensionScore(self.name, score, self.weight, issues, False, "agent")

class DocumentationEvaluator:
    name = "Documentation"
    weight = 0.05
    
    def evaluate(self, project_path: str) -> DimensionScore:
        stdout, _, rc = run_tool(["grep", "-r", "-l", '"""', project_path, "--include=*.py"], timeout=30)
        doc_count = len([l for l in stdout.split('\n') if l.strip()])
        stdout2, _, _ = run_tool(["find", project_path, "-name", "*.py", "-type", "f"], timeout=10)
        total = len([l for l in stdout2.split('\n') if l.strip()])
        coverage = (doc_count / max(total, 1)) * 100
        issues = [f"{doc_count}/{total} files with docstrings"]
        return DimensionScore(self.name, coverage, self.weight, issues, False, "agent")

# ============================================================================
# QUALITY DASHBOARD
# ============================================================================

class QualityDashboard:
    """品質監控儀表板"""
    
    EVALUATORS = [
        LintingEvaluator(),
        TypeSafetyEvaluator(),
        CoverageEvaluator(),
        SecurityEvaluator(),
        ComplexityEvaluator(),
        ArchitectureEvaluator(),
        ReadabilityEvaluator(),
        ErrorHandlingEvaluator(),
        DocumentationEvaluator(),
    ]
    
    def __init__(self, project_path: str, data_dir: str = ".quality_dashboard"):
        self.project_path = Path(project_path)
        self.data_dir = self.project_path / data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.history_file = self.data_dir / "history.json"
        self.evolve_file = self.data_dir / "evolution.json"
        
    def load_history(self) -> List[IterationResult]:
        if self.history_file.exists():
            with open(self.history_file) as f:
                data = json.load(f)
                return [self._dict_to_iteration(d) for d in data]
        return []
    
    def save_history(self, iterations: List[IterationResult]):
        with open(self.history_file, 'w') as f:
            json.dump([self._iteration_to_dict(i) for i in iterations], f, indent=2)
    
    def _dict_to_iteration(self, d: dict) -> IterationResult:
        dims = {}
        for k, v in d["dimensions"].items():
            dims[k] = DimensionScore(**v)
        return IterationResult(
            iteration=d["iteration"],
            timestamp=d["timestamp"],
            dimensions=dims,
            total_score=d["total_score"],
            technical_debt=d["technical_debt"],
            hotspots=d.get("hotspots", {}),
            improvements=d.get("improvements", []),
            agent_actions=d.get("agent_actions", [])
        )
    
    def _iteration_to_dict(self, i: IterationResult) -> dict:
        return {
            "iteration": i.iteration,
            "timestamp": i.timestamp,
            "dimensions": {k: asdict(v) for k, v in i.dimensions.items()},
            "total_score": i.total_score,
            "technical_debt": i.technical_debt,
            "hotspots": i.hotspots,
            "improvements": i.improvements,
            "agent_actions": i.agent_actions
        }
    
    def run_evaluation(self) -> IterationResult:
        """執行一次完整的 9 維度評估"""
        print("🔍 Running 9-Dimension Quality Evaluation...")
        
        dimensions = {}
        for i, eval in enumerate(self.EVALUATORS):
            dim_key = f"D{i+1}_{eval.name.replace(' ', '')}"
            try:
                dimensions[dim_key] = eval.evaluate(str(self.project_path))
            except Exception as e:
                dimensions[dim_key] = DimensionScore(eval.name, 50, eval.weight, [str(e)], eval.tool_driven, eval.tool_name)
        
        total_score = sum(d.score * d.weight for d in dimensions.values())
        technical_debt = 100 - total_score
        hotspots = self._identify_hotspots(dimensions)
        
        history = self.load_history()
        iteration = len(history) + 1
        
        result = IterationResult(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            dimensions=dimensions,
            total_score=total_score,
            technical_debt=technical_debt,
            hotspots=hotspots
        )
        
        history.append(result)
        self.save_history(history)
        
        print(f"\n✅ Iteration {iteration}: Score={total_score:.1f}%, Debt={technical_debt:.1f}%")
        return result
    
    def _identify_hotspots(self, dimensions: Dict[str, DimensionScore]) -> Dict[str, float]:
        hotspots = {}
        for name, dim in dimensions.items():
            if dim.score < 60:
                for issue in dim.issues:
                    if '.py' in issue:
                        hotspots[issue] = max(hotspots.get(issue, 0), 100 - dim.score)
        return hotspots
    
    def generate_trend_chart(self) -> str:
        history = self.load_history()
        if len(history) < 2:
            return "需要至少 2 次迭代才能顯示趨勢"
        
        lines = ["", "📉 技術債趨勢圖", "=" * 50]
        max_debt = max(h.technical_debt for h in history)
        
        for h in history:
            bar_len = int((h.technical_debt / max(max_debt, 1)) * 40)
            bar = "█" * bar_len
            lines.append(f"Iter {h.iteration:2d}: {bar} {h.technical_debt:5.1f}%")
        
        lines.append("=" * 50)
        trend = "↓ 改善中" if history[-1].technical_debt < history[0].technical_debt else "↑ 惡化中"
        lines.append(f"趨勢: {trend}")
        return "\n".join(lines)
    
    def generate_hotspot_map(self) -> str:
        history = self.load_history()
        if not history:
            return "沒有數據"
        
        hotspots = history[-1].hotspots
        lines = ["", "🔥 熱點圖 (Hotspot Map)", "=" * 50]
        lines.append(f"{'模組':<40} {'風險':>10}")
        lines.append("-" * 52)
        
        for file, risk in sorted(hotspots.items(), key=lambda x: -x[1])[:10]:
            bar = "🔴" * int(risk / 20) + "🟡" * int((100 - risk) / 50)
            lines.append(f"{file:<40} {risk:>6.1f}% {bar}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def generate_evolution_report(self) -> str:
        history = self.load_history()
        if len(history) < 2:
            return "需要至少 2 次迭代才能生成進化報告"
        
        lines = ["", "🚀 進化報告 (Evolution Report)", "=" * 60]
        first, last = history[0], history[-1]
        
        delta = last.total_score - first.total_score
        lines.append(f"\n📊 總分變化: {first.total_score:.1f}% → {last.total_score:.1f}%")
        lines.append(f"   {'✅ 提升' if delta > 0 else '❌ 下降'}: {abs(delta):.1f}%")
        
        debt_delta = first.technical_debt - last.technical_debt
        lines.append(f"\n📉 技術債: {first.technical_debt:.1f}% → {last.technical_debt:.1f}%")
        lines.append(f"   {'✅ 減少' if debt_delta > 0 else '❌ 增加'}: {abs(debt_delta):.1f}%")
        
        lines.append("\n" + "=" * 60)
        lines.append("📋 各維度進化")
        lines.append("-" * 60)
        lines.append(f"{'維度':<20} {'初始':>8} {'最新':>8} {'變化':>10}")
        lines.append("-" * 60)
        
        for name in first.dimensions:
            d1 = first.dimensions[name]
            d2 = last.dimensions.get(name, d1)
            delta_score = d2.score - d1.score
            arrow = "↑" if delta_score > 0 else "↓" if delta_score < 0 else "→"
            lines.append(f"{d1.name:<20} {d1.score:>7.1f}% {d2.score:>7.1f}% {arrow}{abs(delta_score):>6.1f}%")
        
        lines.append("\n" + "=" * 60)
        lines.append("🎯 AutoResearch 自動優化記錄")
        lines.append("-" * 60)
        for i, iteration in enumerate(history):
            for action in iteration.agent_actions:
                lines.append(f"  Iter {i+1}: {action}")
        if not any(h.agent_actions for h in history):
            lines.append("  (尚無記錄 - 運行第一次 AutoResearch 迭代)")
        
        return "\n".join(lines)
    
    def generate_html_dashboard(self) -> str:
        history = self.load_history()
        latest = history[-1] if history else None
        
        latest_score = latest.total_score if latest else 0
        latest_debt = latest.technical_debt if latest else 100
        latest_iter = latest.iteration if latest else 0
        latest_ts = latest.timestamp[:10] if latest else "N/A"
        
        score_color = "good" if latest_score >= 80 else "medium" if latest_score >= 60 else "bad"
        debt_color = "bad" if latest_debt <= 20 else "medium" if latest_debt <= 40 else "good"
        
        # Dimensions HTML
        dims_html = self._generate_dimensions_html(latest)
        
        # Trend ASCII
        trend_ascii = self._generate_trend_ascii(history)
        
        # Hotspots HTML
        hotspots_html = self._generate_hotspots_html(latest)
        
        # History rows
        history_rows = self._generate_history_rows(history)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Quality Dashboard - {self.project_path.name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1419; color: #e7e9ea; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ color: #1d9bf0; font-size: 28px; }}
        .header p {{ color: #71767b; margin-top: 5px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: #16181c; border-radius: 16px; padding: 20px; border: 1px solid #2f3336; }}
        .card h2 {{ font-size: 16px; color: #71767b; margin-bottom: 15px; border-bottom: 1px solid #2f3336; padding-bottom: 10px; }}
        .score {{ font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }}
        .score.good {{ color: #00ba7c; }}
        .score.medium {{ color: #ffad1f; }}
        .score.bad {{ color: #f4212e; }}
        .bar {{ height: 8px; background: #2f3336; border-radius: 4px; overflow: hidden; margin: 10px 0; }}
        .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
        .bar-fill.good {{ background: linear-gradient(90deg, #00ba7c, #00d68f); }}
        .bar-fill.medium {{ background: linear-gradient(90deg, #ffad1f, #ffdf5d); }}
        .bar-fill.bad {{ background: linear-gradient(90deg, #f4212e, #ff6b6b); }}
        .dimension {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #2f3336; }}
        .dimension:last-child {{ border-bottom: none; }}
        .dimension-name {{ font-size: 14px; }}
        .dimension-score {{ font-weight: bold; font-size: 14px; }}
        .trend-chart {{ font-family: monospace; font-size: 12px; line-height: 1.4; color: #00ba7c; white-space: pre; }}
        .hotspot {{ display: flex; justify-content: space-between; padding: 8px 0; }}
        .hotspot-file {{ font-size: 13px; color: #e7e9ea; }}
        .hotspot-risk {{ font-size: 12px; padding: 2px 8px; border-radius: 10px; }}
        .hotspot-risk.high {{ background: #f4212e; color: white; }}
        .hotspot-risk.medium {{ background: #ffad1f; color: black; }}
        .hotspot-risk.low {{ background: #00ba7c; color: white; }}
        .timestamp {{ text-align: right; font-size: 11px; color: #71767b; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Quality Dashboard</h1>
        <p>{self.project_path.name} - 技術債追蹤與進化監控</p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>總分 (Overall Score)</h2>
            <div class="score {score_color}">{latest_score:.1f}%</div>
            <div class="bar"><div class="bar-fill {score_color}" style="width: {latest_score}%"></div></div>
            <div class="timestamp">迭代 {latest_iter} - {latest_ts}</div>
        </div>
        
        <div class="card">
            <h2>技術債 (Technical Debt)</h2>
            <div class="score {debt_color}">{latest_debt:.1f}%</div>
            <div class="bar"><div class="bar-fill {debt_color}" style="width: {latest_debt}%"></div></div>
            <div class="timestamp">目標: &lt; 20%</div>
        </div>
        
        <div class="card">
            <h2>9 維度分析</h2>
            {dims_html}
        </div>
        
        <div class="card">
            <h2>📉 技術債趨勢</h2>
            <pre class="trend-chart">{trend_ascii}</pre>
        </div>
        
        <div class="card">
            <h2>🔥 熱點圖</h2>
            {hotspots_html}
        </div>
        
        <div class="card">
            <h2>🚀 進化歷史</h2>
            <div style="font-size: 13px; line-height: 1.6;">
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2f3336;">
                    <span>迭代</span>
                    <span>總分</span>
                    <span>技術債</span>
                </div>
                {history_rows}
            </div>
        </div>
    </div>
</body>
</html>"""
        
        output_file = self.data_dir / "dashboard.html"
        with open(output_file, 'w') as f:
            f.write(html)
        return str(output_file)
    
    def _generate_dimensions_html(self, latest) -> str:
        if not latest:
            return "<p style='color:#71767b'>No data yet</p>"
        parts = []
        for name, dim in latest.dimensions.items():
            color = "#00ba7c" if dim.score >= 80 else "#ffad1f" if dim.score >= 60 else "#f4212e"
            parts.append(f"""<div class="dimension">
                <span class="dimension-name">{dim.name} <small style='color:#71767b'>({dim.weight*100:.0f}%)</small></span>
                <span class="dimension-score" style='color:{color}'>{dim.score:.0f}%</span>
            </div>""")
        return "\n".join(parts)
    
    def _generate_trend_ascii(self, history: List[IterationResult]) -> str:
        if len(history) < 2:
            return "需要至少 2 次迭代"
        lines = []
        max_debt = max(h.technical_debt for h in history) if history else 100
        for h in history:
            bar_len = int((h.technical_debt / max(max_debt, 1)) * 30)
            bar = "█" * bar_len
            lines.append(f"{h.iteration:2d}: {bar} {h.technical_debt:5.1f}%")
        return "\n".join(lines)
    
    def _generate_hotspots_html(self, latest) -> str:
        if not latest or not latest.hotspots:
            return "<p style='color:#71767b'>No hotspots detected</p>"
        parts = []
        for file, risk in sorted(latest.hotspots.items(), key=lambda x: -x[1])[:5]:
            risk_class = "high" if risk > 60 else "medium" if risk > 30 else "low"
            parts.append(f"""<div class="hotspot">
                <span class="hotspot-file">{file}</span>
                <span class="hotspot-risk {risk_class}">{risk:.0f}%</span>
            </div>""")
        return "\n".join(parts)
    
    def _generate_history_rows(self, history: List[IterationResult]) -> str:
        return "\n".join([
            f"<div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2f3336;'>"
            f"<span>#{h.iteration}</span>"
            f"<span>{h.total_score:.1f}%</span>"
            f"<span>{h.technical_debt:.1f}%</span>"
            f"</div>"
            for h in history
        ])

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quality Dashboard")
    parser.add_argument("--project", default="/Users/johnny/.openclaw/workspace-musk/tts-kokoro-v613")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--trend", action="store_true")
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    
    dashboard = QualityDashboard(args.project)
    
    if args.report:
        print(dashboard.generate_evolution_report())
    elif args.trend:
        print(dashboard.generate_trend_chart())
    elif args.html:
        output = dashboard.generate_html_dashboard()
        print(f"✅ HTML Dashboard: {output}")
    else:
        result = dashboard.run_evaluation()
        print(dashboard.generate_trend_chart())
        print(dashboard.generate_hotspot_map())
        html_file = dashboard.generate_html_dashboard()
        print(f"\n🌐 HTML Dashboard: {html_file}")
