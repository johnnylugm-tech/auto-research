# Auto-Research 架構與使用方法

## 問題診斷（2026-04-17）

### 問題 1：Mock Agent 無法執行真實修復

**原因：**
- `cli.py` → spawn `agent_auto_research.py` 作為 Python subprocess
- `agent_auto_research.py` 內的 Agent 是 Python class，無法 call OpenClaw `sessions_spawn`
- 因此只能使用 Mock Agent，無法執行真實程式碼修改

**解決方案：**
- 繞過 `agent_auto_research.py`
- 直接用 `sessions_spawn` spawn sub-agent 跑修復邏輯
- Python scripts 只用於：工具執行（ruff/mypy/AQG）、評估計算、CLI 界面

### 問題 2：D9 Documentation 評估錯誤

**原因：**
- `DocumentationEvaluator` 用 `@param/@return/@raises` 作為 docstring 標誌
- 但 methodology-v2 的 docstrings 使用 `"""` 但不用這些標籤
- 導致真實分數 0% 而非 95.8%

**解決方案：**
- 改用 `"""` 存在與否作為 docstring 評估標準
- 或接受 0% 分數作為真實反映（需手動改善程式碼）

---

## 正確使用方式

### 方式 A：手動協調（推薦用於複雜專案）

不靠 `cli.py`，直接用 `sessions_spawn` spawn sub-agent：

```
1. 評估現狀：跑 QualityDashboard
2. 分析問題：看原始工具輸出
3. 修復問題：sub-agent 直接改程式碼
4. 驗證：重新跑 QualityDashboard
5. 重複直到達標
```

### 方式 B：改造 cli.py（長期方案）

改造 `cli.py` 讓 `run` command 直接 spawn sub-agent，而不是 call `agent_auto_research.py`：

```python
def cmd_run(args):
    # Spawn sub-agent with full OpenClaw runtime
    from openclaw_tools import sessions_spawn
    sessions_spawn(
        task="""## AutoResearch Coordinator
        Project: {args.project}
        Phase: {args.phase}
        ...
        """,
        runtime="subagent",
        mode="run",
        timeoutSeconds=1800
    )
```

---

## 已知限制

| 元件 | 狀態 | 說明 |
|------|------|------|
| `cli.py` | ⚠️ 需改造 | run command 用 Mock Agent |
| `agent_auto_research.py` | ⚠️ 備用 | Mock Agent，僅評估 |
| `dashboard.py` | ✅ 已修復 | 支援 scan_paths |
| `QualityDashboard` | ✅ 正常 | 評估引擎 |
| AQG 整合 | ✅ 正常 | D4 Security |

---

## scan_paths 設定檔格式

```json
// .quality_dashboard/auto_research.json
{
  "scan_paths": [
    "implement/governance",
    "implement/kill_switch",
    "implement/llm_cascade",
    "implement/mcp",
    "implement/security"
  ],
  "target_score": 85,
  "pass_score": 70
}
```

---

## 維度評估公式

| 維度 | 工具 | 分數公式 |
|------|------|----------|
| D1_Linting | ruff | 100 - errors × 5 |
| D2_TypeSafety | mypy | 100 - errors × 10 |
| D3_Coverage | pytest-cov | 實際覆蓋率 |
| D4_Security | AQG | 100 - critical×10 - warning×2 |
| D5_Complexity | lizard | 100 - avg_cc × 5 |
| D6_Architecture | radon | 100 - C_rank × 20 |
| D7_Readability | grep | docstring檔案數 / 總檔案數 × 100 |
| D8_ErrorHandling | grep | min(100, except_blocks × 10) |
| D9_Documentation | grep | @param/@return/@raises 檔案數 / 總檔案數 × 100 |

---

*最後更新：2026-04-18 00:13 GMT+8*
