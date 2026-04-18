# Auto-Research 架構與使用方法

## 核心目標（2026-04-18 更新）

### 真正的目標不是分數

**錯誤目標：**
- ❌ 讓分數達到 85%
- ❌ 分數夠高就不修了
- ❌ 只修能快速讓分數達標的問題

**正確目標：**
- ✅ 提升軟體品質，減少缺陷
- ✅ 發現的問題要修，與分數無關
- ✅ 分數只是測量工具，不是終點

### 發現就修原則

```
發現任何問題 → 評估嚴重性 → 如果可修就修 → 無法修才跳過
```

**與分數無關：**
- 分數 100% 但還有可修的 warning → 繼續修
- 分數 50% 但所有可修的都修完了 → 停止
- 修完發現新問題 → 繼續修

### 迭代的真正意義

**不是：**
- ❌ 3 次機會把分數拉到 85%

**而是：**
- ✅ 3 次「評估→發現問題→修復→驗證」循環
- ✅ 每次循環都盡可能修所有可修的問題
- ✅ 持續改善，直到沒有可修的問題為止

---

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
| D4_Secrets | detect-secrets | 100 - verified_secrets × 20 |
| D5_Complexity | lizard | 100 - avg_cc × 5 |
| D6_Architecture | pydeps | 100 - cycles × 20 - cross_layer × 10 |
| D7_Readability | grep | docstring檔案數 / 總檔案數 × 100 |
| D8_ErrorHandling | grep | min(100, except_blocks × 10) |
| D9_Documentation | grep | (docstring≥3行 或 ≥50字的檔案) / 總檔案數 × 100 |

---

## D6_Architecture 公式詳解（2026-04-18 修正）

### 為什麼舊公式無效

舊公式用 `radon cc -a` 測「平均複雜度等级」：
```
D6_Architecture: 100 - C_rank × 20
```

**實際效果：**
- avg grade A → 100分
- avg grade B → 80分
- avg grade C → 60分

**這不是 architecture score，這是 complexity score 的另一種表達。**

問題：
- 一個爛架構可以全部是簡單函數（CC<10, grade A）→ 拿 100分
- 一個好架構模組化佳但某個核心類調用鏈複雜（grade B）→ 拿 80分
- 基本上是 binary：要嘛 100 要嘛 80，沒有區分度

### Architecture 應該測什麼

| 維度 | 測什麼 | 工具 |
|------|--------|------|
| D5 Complexity | 函數內部邏輯分支數 | radon/lizard (CC) |
| **D6 Architecture** | **模組之間的依賴關係** | **pydeps (dep graph)** |

Architecture 關心的核心問題：
- 循環依賴 (A→B→C→A) → 架構高壓線
- 跨層依賴 (高層直接依賴低層細節) → 違反分層原則
- 扇出過高 (一個模組依賴20個) → 結構不良
- 扇入過低 (某模組沒人用) → 可能是 dead code

### 新公式

```
D6_Architecture: 100 - (cycles × 20) - (cross_layer × 10)
```

**工具：** `pydeps --no-show --format=dot <package>` 產生依賴圖

| 問題類型 | 權重 | 說明 |
|----------|------|------|
| 循環依賴 (每個) | -20 | 模組之間形成環路，牽一髮動全身 |
| 跨層依賴 (每個) | -10 | 高層業務邏輯直接依賴低層實作細節 |

**扣分上限：** 最低 0 分（不鎖死）

**評估方式：**
```bash
# 檢測循環依賴
pydeps --no-show --format=cycles <package>

# 檢測跨層依賴（需配合 layer config）
# 例如：business.py 不應直接 import persistence/db.py 的細節
```

### 範例

```
Good Architecture (score=100):
  governance/  → escalation_engine/
  kill_switch/ → circuit_breaker/, state_manager/
  (無循環，層次清晰)

Bad Architecture (score=70):
  governance_trigger.py ──imports──► api_clients/anthropic.py
                                            ▲
         models.py ──imports──────────────┘
  (models → clients → governance 形成循環)
  扣分: 1 cycle × 20 = -20, 3 cross_layer × 10 = -30
  Score: 100 - 20 - 30 = 50
```

### pydeps 安裝

```bash
pip install pydeps
```

### 局限性

- 需要 package 有 `__init__.py`（Python 標準）
- 跨層依賴需要人工定義「哪些是高層、哪些是低層」
- 如果無法自動化，可用人工 audit 替代，count 問題數量

---

## D9_Documentation 公式詳解（2026-04-18 修正）

### 為什麼舊公式有問題

舊公式測 `@param/@return/@raises` 標籤：
```
D9_Documentation: @param/@return/@raises 檔案數 / 總檔案數 × 100
```

**問題：**
- 強迫特定格式（@param、Google style、NumPy style）
- 不在乎文件內容是否有用的實質
- 格式合規 ≠ 文件有用

### 新公式

```
D9_Documentation: (docstring ≥3行 或 ≥50字 的檔案) / 總檔案數 × 100
```

**「實質內容」定義：**
| 條件 | 標準 |
|------|------|
| 行數標準 | docstring ≥ 3 行 |
| 字數標準 | docstring ≥ 50 字 |
| 滿足其一即可 | OR 邏輯 |

**排除（structural files，不影響分數）：**
- `"""..."""` 或 `"""."""` 空白文件
- 只有一行標題無說明
- 只有 TODO/FIXME 佔位
- **Structural definition files**（enum, exception, interface 定義檔）:
  - 命名本身就是文件，擴充沒有實際價值
  - 例如：`enums.py`, `exceptions.py`, `__init__.py`
  - 當前被排除的檔案（共 11 個）：
    - `implement/governance/{enums,models,exceptions}.py`
    - `implement/llm_cascade/{enums,exceptions}.py`
    - `implement/mcp/{__init__,data_perimeter,saif_identity_middleware}.py`
    - `implement/security/{prompt_shield,detection_modes,shield_enums}.py`

**納入：**
- 3+ 行說明
- 50+ 字的功能描述
- 任何有意義的參數/返回值/用途說明（不限格式）

### 範例

```python
# ❌ 空白文件（不納入）
def foo(x):
    """pass"""
    pass

# ❌ 只有一行（不納入）
def bar(y):
    """Handle bar."""
    pass

# ✅ ≥3行（納入）
def baz(z):
    """
    Process baz.
    Args:
        z: input value
    """
    pass

# ✅ ≥50字（納入）
def qux(a, b):
    """Calculate qux with given tolerance. Returns None on failure."""
    pass
```

### 局限性

- 行數/字數閾值是人為設定，可能需根據專案調整
- 未來可加入「是否有 Args/Returns/Raises 說明」作為子維度

---

## D4_Secrets 公式詳解（2026-04-18 修正）

### 為什麼舊公式（AQG）無效

AQG 的 D4 問題：
- Critical: docstring 提到 `OPENAI_API_KEY` 被當成 hardcoded secret
- Warning: "function too long" 被當成安全問題
- 全部是 false positive，測的是「代碼質量」而非「安全」

**Framework 的安全問題不是 SQLi/XSS，而是 credential leak。**

### 新公式

```
D4_Secrets: 100 - verified_secrets × 20
```

**工具:** `detect-secrets`（inline scan，僅測當前 working directory）

| 條件 | 分數 |
|------|------|
| 0 verified secrets | 100% |
| 1 verified secret | 80% |
| 2 verified secrets | 60% |
| 3+ | 0% |

**Scope:** 只測 `implement/` 五個 Feature 目錄

**不掃:**
- Git history（不掃 historical commits）
- 文件目錄（如有假的 API key 範例）
- Local config 檔案

### 局限性

- `is_verified: false` 的 findings 會被忽略
- 文件中的假 key 不會造成扣分

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
│  每個 Iteration 修所有低於 85% 的維度，不只一個              │
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
│  ITERATION 1                                                       │
│  ┌────────────────────────────────────────────────────────┐│
│  │ 1. 跑全部 9 個維度評估（不是只跑上次失敗的）           ││
│  │ 2. 找出所有 < 85% 的維度                               ││
│  │ 3. 修所有能修的問題（一次修完所有維度）                ││
│  │ 4. 驗證全部 9 個維度的新分數                          ││
│  │ 5. 強制中斷，報告維度維修護     │
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ITERATION 2                                                       │
│  （重複：跑全部 9 個 → 修所有 < 85% → 驗證 → 中斷 report）│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  ITERATION 3                                                       │
│  （重複同上）                                                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE N+1: 最終驗證                                        │
│  ┌────────────────────────────────────────────────────────┐│
│  │ 1. 重新跑所有 9 個維度驗證                             ││
│  │ 2. 填入最終分數對比表                                  ││
│  │ 3. Commit with structured message                       ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**核心原則：每個 iteration 修所有有問題的維度，不是只修一個**

---

### Iteration Report 模板

每個 iteration 結束時，必須有以下結構的 report：

```markdown
## Iteration N Report

### 分數變化（全部 9 個維度）
| D | Dimension | 之前 | 之後 | 變化 | 狀態 |
|---|-----------|------|------|------|------|
| D1 | Linting | X% | Y% | +/-Y% | ✅/❌ |
| D2 | TypeSafety | X% | Y% | +/-Y% | ✅/❌ |
| D3 | TestCoverage | X% | Y% | +/-Y% | ✅/❌ |
| D4 | Security | X% | Y% | +/-Y% | ✅/❌ |
| D5 | Complexity | X% | Y% | +/-Y% | ✅/❌ |
| D6 | Architecture | X% | Y% | +/-Y% | ✅/❌ |
| D7 | Readability | X% | Y% | +/-Y% | ✅/❌ |
| D8 | ErrorHandling | X% | Y% | +/-Y% | ✅/❌ |
| D9 | Documentation | X% | Y% | +/-Y% | ✅/❌ |

### 維度修復詳情（所有 < 85% 的維度）
| D | 修了什麼 | 檔案:行號 | 為什麼沒修完 |
|---|---------|----------|------------|
| D1 | F401 清理 52 個 | governance/__init__.py:14 | — |
| D1 | F821 修復 httpx | llm_cascade/api.py:247 | — |
| D5 | — | — | 268 個 CC>15，核心邏輯 |

### 原始工具輸出（每個維度都要有）
```
[ruff output]
[mypy output]
[pytest-cov output]
[AQG output]
[lizard output]
...
```

### 是否繼續下一個 iteration？
- [ ] 是（已確認改善，準備繼續）
- [ ] 否（3 輪用完，記錄技術債）
```

### Iteration 邏輯（每輪都修所有問題維度）

**錯誤邏輯：**
- ❌ Iteration 1 只修 D1
- ❌ Iteration 2 只修 D4 + D5
- ❌ Iteration 3 只修 D6 + D9

**正確邏輯：**
- ✅ 每個 Iteration 開始時，評估全部 9 個維度
- ✅ 找出所有 < 85% 的維度
- ✅ 一次修所有能修的問題
- ✅ 驗證全部 9 個維度的新分數
- ✅ 中斷 report

**3 輪的意義：3 次完整的「評估→修復→驗證」循環，而不是每輪只修特定維度**

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
