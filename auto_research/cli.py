#!/usr/bin/env python3
"""
AutoResearch CLI - 軟體品質提升工具

Usage:
    python3 -m auto_research.cli assess --project /path/to/project --phase 4
    python3 -m auto_research.cli run --project /path/to/project --phase 4 --iterations 3
    python3 -m auto_research.cli fix --project /path/to/project --dimension D4
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from quality_dashboard.dashboard import QualityDashboard
from agent.agent_auto_research import AgentDrivenAutoResearch


def cmd_assess(args):
    """執行維度評估"""
    dashboard = QualityDashboard(args.project, phase=args.phase)
    results = dashboard.run_assessment()
    
    print(f"\n{'='*60}")
    print(f"📊 Quality Assessment - Phase {args.phase}")
    print(f"{'='*60}")
    
    total = 0
    for dim, score in results.items():
        status = "✅" if score >= 85 else "⚠️"
        print(f"  {status} {dim}: {score:.1f}%")
        total += score
    
    print(f"\n  Total: {total/len(results):.1f}%")
    return 0


def cmd_run(args):
    """執行 AutoResearch 迭代"""
    print(f"\n{'='*60}")
    print(f"🔬 AutoResearch - Phase {args.phase}")
    print(f"{'='*60}")
    
    agent = AgentDrivenAutoResearch(args.project, phase=args.phase)
    result = agent.run(max_iterations=args.iterations)
    
    print(f"\n{'='*60}")
    print(f"📊 AutoResearch Result")
    print(f"{'='*60}")
    print(f"  Iterations: {result.get('iterations', 0)}")
    print(f"  Improvement: {result.get('improvement', 0):.1f}%")
    
    return 0


def cmd_fix(args):
    """修復單一維度"""
    print(f"\n🔧 Fixing dimension: {args.dimension}")
    print(f"   Project: {args.project}")
    
    agent = AgentDrivenAutoResearch(args.project, phase=args.phase or 4)
    result = agent.run(max_iterations=1)
    
    print(f"\n✅ Fix complete")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="AutoResearch - 軟體品質提升工具"
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # assess
    assess_parser = subparsers.add_parser("assess", help="執行維度評估")
    assess_parser.add_argument("--project", required=True, help="專案路徑")
    assess_parser.add_argument("--phase", type=int, default=4, help="Phase (預設: 4)")
    assess_parser.set_defaults(func=cmd_assess)
    
    # run
    run_parser = subparsers.add_parser("run", help="執行 AutoResearch")
    run_parser.add_argument("--project", required=True, help="專案路徑")
    run_parser.add_argument("--phase", type=int, default=4, help="Phase (預設: 4)")
    run_parser.add_argument("--iterations", type=int, default=3, help="迭代次數 (預設: 3)")
    run_parser.set_defaults(func=cmd_run)
    
    # fix
    fix_parser = subparsers.add_parser("fix", help="修復單一維度")
    fix_parser.add_argument("--project", required=True, help="專案路徑")
    fix_parser.add_argument("--dimension", required=True, help="維度 (D1-D9)")
    fix_parser.add_argument("--phase", type=int, default=4, help="Phase (預設: 4)")
    fix_parser.set_defaults(func=cmd_fix)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())