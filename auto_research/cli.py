#!/usr/bin/env python3
"""
AutoResearch CLI - 軟體品質提升工具

Usage:
    python3 -m auto_research.cli assess --project /path/to/project --phase 4
    python3 -m auto_research.cli run --project /path/to/project --phase 4 --iterations 3
    python3 -m auto_research.cli fix --project /path/to/project --dimension D4

Architecture:
    - This CLI spawns an AutoResearch Coordinator sub-agent via sessions_spawn
    - The sub-agent has full OpenClaw runtime access for coordination
    - Python scripts (dashboard.py) are pure evaluation tools
    - Complex decisions (refactoring, fixes) happen in the sub-agent
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
    """Execute AutoResearch via sub-agent (not Mock Agent)
    
    This function spawns a Coordinator sub-agent that uses sessions_spawn
    to coordinate real LLM-driven fixes. The Python scripts (dashboard.py)
    are evaluation-only engines.
    """
    print(f"\n{'='*60}")
    print(f"🔬 AutoResearch - Phase {args.phase} ({args.iterations} iterations)")
    print(f"{'='*60}")
    print(f"Project: {args.project}")
    print(f"\nSpawning AutoResearch Coordinator sub-agent...")
    print("(Sub-agent has full OpenClaw runtime + sessions_spawn access)")
    
    # Check if we're in an OpenClaw context by trying to import the spawn function
    try:
        from openclaw_tools import sessions_spawn
        HAS_SPAWN = True
    except ImportError:
        HAS_SPAWN = False
    
    if HAS_SPAWN:
        task = f"""## AutoResearch Coordinator Task

You are the AutoResearch Coordinator. Your job:

### Project
`{args.project}`

### Phase
{args.phase}

### Iterations
{args.iterations}

### Configuration
The project has a `.quality_dashboard/auto_research.json` config file.
Read it to get `scan_paths` (the directories to evaluate).

### Your Job (run {args.iterations} iterations):

1. **Evaluate current state**: Run QualityDashboard assessment on the project.
   ```python
   import sys
   sys.path.insert(0, '/Users/johnny/auto-research')
   sys.path.insert(0, '/Users/johnny/agent-quality-guard-v2')
   from quality_dashboard.dashboard import QualityDashboard
   dashboard = QualityDashboard('{args.project}')
   result = dashboard.run_evaluation()
   for name, dim in result.dimensions.items():
       print(f'{name}: {dim.score:.1f}%')
   ```

2. **For each iteration**:
   - Run evaluation to get current scores
   - Identify which dimensions are below 85%
   - For each failing dimension, make ACTUAL CODE FIXES in the project files
   - After fixes, re-run evaluation
   - Report improvement

3. **Dimensions to fix** (use the evaluation output to know which fail):
   - D1_Linting (ruff check): Fix ruff errors
   - D4_Security (AQG): Address real security issues, filter docstring false positives
   - D5_Complexity (lizard): Simplify functions with CC > 15
   - D6_Architecture (radon): Reduce C-rank methods

4. **Evaluation tools** (these run via Python subprocess):
   ```bash
   # Linting
   ruff check {args.project}/implement/governance
   ruff check {args.project}/implement/kill_switch
   ruff check {args.project}/implement/llm_cascade
   ruff check {args.project}/implement/mcp
   ruff check {args.project}/implement/security
   
   # Coverage
   python3 -m pytest test/governance --cov=implement/governance --cov-report=term -q
   ```

5. **Report** after each iteration: which dimensions improved and by how much.

6. **At the end**: Commit your changes to the project git repo.

### Environment
- Working directory: `/Users/johnny/auto-research`
- AQG path: `/Users/johnny/agent-quality-guard-v2`
- Project path: `{args.project}`

### Important
- You have sessions_spawn access - use it if you need to delegate sub-tasks
- Make ACTUAL code changes, not just suggestions
- After each fix, verify with evaluation
- Be honest about what improved and what didn't
"""
        
        result = sessions_spawn(
            task=task,
            label="auto-research-coordinator",
            runtime="subagent",
            mode="run",
            timeoutSeconds=1800 * args.iterations
        )
        
        print(f"\n{'='*60}")
        print(f"📊 AutoResearch Complete")
        print(f"{'='*60}")
        return 0 if result else 1
    else:
        print("\n⚠️  Warning: sessions_spawn not available.")
        print("   Falling back to AgentDrivenAutoResearch (Mock Agent)...")
        print("   Note: Mock Agent cannot make real fixes.\n")
        agent = AgentDrivenAutoResearch(args.project, phase=args.phase)
        result = agent.run(max_iterations=args.iterations)
        print(f"\n  Iterations: {result.get('iterations', 0)}")
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