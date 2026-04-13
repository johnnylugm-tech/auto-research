"""
AutoResearch - 軟體品質提升工具

使用方式:
    from auto_research import QualityDashboard, AgentDrivenAutoResearch
"""

__version__ = "1.0.0"
__author__ = "Johnny Lu"

from .quality_dashboard.dashboard import QualityDashboard
from .agent.agent_auto_research import AgentDrivenAutoResearch

__all__ = ["QualityDashboard", "AgentDrivenAutoResearch"]