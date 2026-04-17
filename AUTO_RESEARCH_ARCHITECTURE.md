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

---

## 透明度協議（2026-04-18 新增）

### 核心原則

**看見數字 ≠ 數字正確。工具輸出 ≠ 預期結果。**

每次評估必須：
1. **驗證工具原始輸出** — 不要只看處理後的數字，要看 stdout/stderr
2. **交叉確認** — 用另一個方法驗證同一個結論
3. **完整範圍** — 測試所有相關目錄/檔案，不只部分
4. **不確定就說不確定** — 「應該是」不是結論，「不確定」才是

---

### Sub-Agent 任務透明度要求

**每次 spawn sub-agent 前，必須：**

1. **完整驗證所有 9 個維度**（不是只驗證懷疑有問題的）
2. **每個維度都要有原始工具輸出截圖/文字**
3. **明確列出每個維度的：問題數量、檔案位置、具體行號**

**每次 sub-agent 回報後，必須：**

1. **每個 iteration 完成後強制中斷 report**（不是等最後一次）
2. **驗證中斷時的進度：修了什麼、剩什麼、分數變化**
3. **不滿意就停在該 iteration，不繼續**

**最終 commit 前，必須：**

1. **所有 9 個維度重新驗證一次**
2. **完整 iteration-by-iteration 記錄**
3. **每個維度的：之前分數 → 之後分數 → 變化**
4. **按維度列出：修了什麼（檔案+行號）、為什麼沒修完、剩餘問題**

---

### 迭代式品質改善流程（正確版）

```
┌─────────────────────────────────────────────────────────────┐
│  AUTO-RESEARCH QUALITY IMPROVEMENT                          │
└─────────────────────────────────────────────────────────────┘

PHASE 0: 基準建立（完整驗證）
  ┌──────────────────────────────────────────────────────────┐
  │ 1. 跑所有 9 個維度的原始工具命令                        │
  │ 2. 記錄原始輸出（stdout/stderr）                        │
  │ 3. 確認問題數量、檔案、行號                             │
  │ 4. 計算分數並驗證（不是只看 Dashboard）                  │
  │ 5. 寫入 PROCESS_LOG.md                                  │
  └──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ITERATION 1 → 驗證分數 → 修復 → 驗證 → 中斷 report      │
│  ITERATION 2 → 驗證分數 → 修復 → 驗證 → 中斷 report      │
│  ITERATION 3 → 驗證分數 → 修復 → 驗證 → 中斷 report      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE N+1: 最終驗證                                        │
│  ┌────────────────────────────────────────────────────────┐│
│  │ 1. 重新跑所有 9 個維度驗證                             ││
│  │ 2. 填入最終分數對比表                                  ││
│  │ 3. 列出：修了什麼、剩什麼、技術債                      ││
│  │ 4. Commit with structured message                       ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### Iteration Report 模板

每個 iteration 結束時，必須有以下結構的 report：

```markdown
## Iteration N Report

### 分數變化
| D | Dimension | 之前 | 之後 | 變化 |
|---|-----------|------|------|------|
| D1 | Linting | 0% | XX% | +XX% |
| ... | ... | ... | ... | ... |

### 維度修復詳情
| D | 修了什麼 | 檔案:行號 | 為什麼沒修完 |
|---|---------|----------|------------|
| D1 | F401 自動清理 | governance:14 | — |
| D1 | F821 修復 | llm_cascade:247 | — |
| D5 | — | — | 268 個 CC>15，核心邏輯 |

### 問題嚴重性分類
| Severity | 本次修復 | 剩餘 |
|----------|---------|------|
| Critical | 2 | 0 |
| Warning | 5 | 22 |
| Info | 10 | 5 |

### 原始工具輸出（截圖/文字）
```
[粘貼原始輸出]
```

### 是否繼續下一個 iteration？
- [ ] 是（已確認改善，準備繼續）
- [ ] 否（問題無法在本次解決，記錄技術債）
```

---

### PROCESS_LOG.md 結構

```markdown
# AutoResearch Process Log — [專案名]

## 透明度要求清單

- [ ] 基準：所有 9 個維度都有原始工具輸出
- [ ] 每次 iteration：都有中斷 report
- [ ] 最終驗證：所有維度重新跑一次
- [ ] Commit message：結構化，包含分數對比

## 基準（Iteration 0）

[填入所有 9 個維度的驗證結果]

## Iteration 1

[Report Template 內容]

## Iteration 2

[Report Template 內容]

## Iteration 3

[Report Template 內容]

## 最終結果

[最終分數對比表]

## Technical Debt

[列出無法在 3 次內解決的問題]
```

---

### 教訓（2026-04-18）

1. **「工具是客觀的」不等於「我看懂了」**
   - ruff 輸出 42 errors，但我之前只看到 7 個
   - 因為只檢查了部分目錄，沒有全部遍歷

2. **部分驗證 = 沒有驗證**
   - 如果只測 governance + llm_cascade，但漏了 mcp + security
   - 結論可能是完全錯誤的

3. **Dashboard 輸出可信的前提是 evaluator 邏輯正確**
   - D9 在 DocEvaluator 有 bug 時顯示 95.8%
   - 但真實分數是 0%
   - 工具輸出需要交叉驗證

4. **Sub-agent 的 final report 不等於透明**
   - 如果沒有 iteration-by-iteration 過程
   - 無法確認是否真的跑了 3 個 iteration
   - 也無法確認每次修了什麼

---

*最後更新：2026-04-18 00:47 GMT+8*
