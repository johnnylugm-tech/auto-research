# AutoResearch - 軟體品質提升工具

> 自動化的迭代式軟體品質改進系統  
> 適用於任何 Python 專案

## 安裝

```bash
pip install auto-research
```

或直接使用：

```bash
python3 -m auto_research.cli --help
```

## 使用方式

### 1. 評估維度分數

```bash
python3 -m auto_research.cli assess --project /path/to/project --phase 4
```

### 2. 執行 AutoResearch（3 輪迭代）

```bash
python3 -m auto_research.cli run --project /path/to/project --phase 4 --iterations 3
```

### 3. 修復單一維度

```bash
python3 -m auto_research.cli fix --project /path/to/project --dimension D4
```

## 9 維度品質模型

| 維度 | 說明 | 工具 | 及格 | 目標 |
|------|------|------|------|------|
| D1 | Linting | ruff | 70% | 85% |
| D2 | Type Safety | mypy | 70% | 85% |
| D3 | Test Coverage | pytest-cov | 70% | 85% |
| D4 | Security | bandit | 70% | 85% |
| D5 | Complexity | lizard | 70% | 85% |
| D6 | Architecture | radon | 70% | 85% |
| D7 | Readability | agent | 70% | 85% |
| D8 | Error Handling | agent | 60% | 85% |
| D9 | Documentation | agent | 70% | 85% |

## Phase 維度組合

| Phase | 活躍維度 |
|-------|----------|
| Phase 3 | D1, D5, D6, D7 |
| Phase 4 | D1, D2, D3, D4, D5, D6, D7 |
| Phase 5+ | D1-D9 全部 |

## 透明度報告

每個問題都有：
- **工具原始輸出**：可驗證
- **嚴重性分類**：基於工具結果（CRITICAL/HIGH/MEDIUM/LOW）
- **Before/After 數量**：可追蹤

```
📊 Iteration 1 Report
  Baseline: D1=90%, D2=0%, D3=0%, D4=30%, D5=13%, D6=70%, D7=100%
  After: D1=100%, D2=50%, D3=60%, D4=50%, D5=30%, D6=70%, D7=100%
  Issues Found: 15
    - [CRITICAL] D4: ssml_parser.py - xml.etree usage
      Tool Output: B314:blacklist Using xml.etree.ElementTree.fromstring...
    - [HIGH] D2: circuit_breaker.py - callable type
      Tool Output: error: Function "builtins.callable" is not valid as a type
  Issues Fixed: 10
  Remaining: 5 dimensions <85%
  Stop Reason: Continue to iteration 2
```

## 目錄結構

```
auto_research/
├── README.md
├── __init__.py
├── cli.py              # 命令列介面
├── quality_dashboard/   # 維度評估引擎
│   └── dashboard.py
└── agent/              # Agent 協調
    └── agent_auto_research.py
```

## License

MIT