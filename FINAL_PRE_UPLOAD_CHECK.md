# FINAL_PRE_UPLOAD_CHECK — INQUIRY（Sage）上传前终检

- 检查日期：2026-09-15
- 检查对象（仅此批最新上传）：

| 文件 | SHA-256 前 12 位 |
|---|---|
| `inq_manuscript_blind.docx`（39f5） | `94388b696f73` |
| `inq_title_page.docx`（0de4） | `b70656920a83`（与上一版完全相同，无需改动） |
| `inq_cover_letter.docx`（7847） | `a64dd6832ce1` |
| `inq_README.md`（dbf3） / `inq_CHANGELOG.md`（a470） | `3f66d39860ae` / `11c8f1b43364` |

- 依据：`PRE_SUBMIT_REVIEW.md` §3 四项 must-fix + 本轮新增表题位置要求 + INQUIRY 刊规硬条款。
- 范围：格式/合规/引用一致性。未改写科学内容。

---

## 判定：**GO**

`PRE_SUBMIT_REVIEW.md` 列出的 4 项 must-fix 全部实测已修；6 项预期状态全部通过；刊规硬条款全部通过。无剩余阻塞项。

## 6 项预期状态逐项核验

| # | 预期 | 结果 | 实测证据 |
|---|---|---|---|
| 1 | 封面信不再说"压缩未执行"；Option A 已完成；scope 提到 provision / help-seeking / escalation | **PASS** | 第 4 段："Option A compression is complete … ≤5000 words … and 3 tables … moved to Supplemental Tables S2 and S3"；第 3 段含 "care provision"、"help-seeking pathways"、"escalation to formal care"、"institutionally bounded capacity (hotline scale-up and parent-helper roles)"；APC $3200 自付、无 waiver、三次前投披露、作者/ORCID 保留 |
| 2 | AMA 首现顺序 1–33 连续，Roske=22 … Laba=27 | **PASS** | 45 处上标首现序列 = 1,2,…,33 严格递增；文献表 22 Roske / 23 Brause / 24 Bucher 2012 / 25 Bareis / 26 Richter / 27 Laba；ghost 0，orphan 0，编号 1–33 连续 |
| 3 | 无 "DIGITAL HEALTH has published" 残留 | **PASS** | 全文 "DIGITAL HEALTH" 0 命中；两句已改为 "Douyin health-education work has been published ^19" / "A summative content analysis of English-language TikTok mental-health videos has been published ^33"，引用号不变 |
| 4 | 盲稿含匿名伦理句 | **PASS** | Methods "Reflexivity and trustworthiness" 末句："Ethical approval was not required: the analysis used only publicly available Douyin videos and first-level comments; no participants were recruited or contacted."；"Ethics are restated under Statements and Declarations" 已删；无机构名 |
| 5 | References 后结构 = T1 题+注 → 表 → 空行 → T2 题+注 → 表 → 空行 → T3 题+注 → 表；Results 无完整 "Table N. …" 题 | **PASS** | 文末块序列实测：`ref 33` → `Table 1.` 题 → 注 → [表] → [空] → `Table 2.` 题 → 注 → [表] → [空] → `Table 3.` 题 → 注 → [表]（文档结束）；正文中 "Table N. " 完整题 0 处，仅剩短呼叫 "(Table 1)"、"Table 1 reports…"、"Table 2 reports…"、"Table 3 synthesises…" |
| 6 | ≤3 表；正文+表 ≤5000；结构化摘要 ≤250；双盲；COI 在 References 前；无作者泄露 | **PASS** | 见下表 |

## 刊规硬条款

| 项 | 结果 | 实测 |
|---|---|---|
| 表数 ≤3 | PASS | 3 表，全部在 References 之后；正文无 Table 4/5 残留；S2/S3 呼叫指向 Supplemental |
| 词数 ≤5000（含表；不含摘要/关键词/参考文献） | PASS | 正文 4500 + 文末表题/注 41 + 表格单元格 246 = **4787**（含匿名 COI 14 词亦 <5000）；README 口径 ≈4952 |
| 结构化摘要 ≤250 | PASS | 237 词（含 Background/Objective/Methods/Results/Conclusions 标签）/ 232 词（不含）；与前三版逐字相同 |
| 关键词 ≥5 | PASS | 8 个 |
| 双盲匿名 | PASS | 主稿 0 命中：作者姓名、SCUT / South China / Guangzhou、ORCID、邮箱、Grok、Guarantor/CRediT/Acknowledgements 正文；docx 元数据 author=`python-docx`；无修订痕迹、无批注、无内嵌图片 |
| 匿名 COI 在 References 前 | PASS | "Declaration of Conflicting Interests" + 刊规原句，紧接 Conclusion 之后、References 之前 |
| AMA 上标引注 | PASS | 45 处全部为 `vertAlign=superscript` 数字，与文献表双射 |
| GenAI 非作者 | PASS | 标题页 Acknowledgements 披露 xAI Grok 用途并声明非作者；封面信同步 |
| 主稿左右边距 ≈3 cm | PASS | L=3.00 / R=3.00 cm |
| 双倍行距、10/12 pt | PASS | line=480；正文 12 pt Times New Roman；参考文献 10 pt；Table 3 为 8 pt（可接受，见非阻塞备注） |
| 标题页 | PASS | 作者/ORCID/邮箱/单位、Guarantor、伦理、知情同意、Funding、CRediT、AI 披露、数据可用性、COI 齐全（与上一版相同） |

## 非阻塞备注（不影响 GO，可留待修回）

- AMA 上标位置仍为 `text ^1.`（前置空格、在句号前），AMA 规范为 `text.^1`。README 已标记【未做】。Sage 排版阶段通常会统一，不构成退稿理由。
- Table 3 单元格 8 pt；ref 13 期刊名 "Journalism and Media" 未缩写；页码范围用 en dash。
- README 列出的 Supplemental（codebook、Table S1、Figure S1、SRQR）在正文无呼叫，仅 S2/S3 被引用；上传时确保清单一致即可。

## 上传清单（Sage Track）

1. Cover letter — `cover_letter.docx`（7847 版）
2. Title Page — `title_page.docx`（0de4 版；含去匿名 Statements and Declarations）
3. Main Document（anonymized）— `manuscript_blind.docx`（39f5 版；表在文末，题注随表）
4. Figure 1 — `Figure_1_sampling_flow.png`（单独文件；勿嵌入主稿）
5. Supplemental Material — codebook、Figure S1、Table S1、**Table S2（speakers）**、**Table S3（presentation formats）**、SRQR checklist
6. 系统表单：文章类型 Original Research；关键词与主稿 8 个一致；作者顺序 Chuqi Wang → Mingzhe Gao（通讯）；ORCID 与标题页一致；确认 APC $3200 自付、无 waiver；勾选"生成式 AI 非作者、已披露"
7. 上传后预览 PDF：核对 Table 3 七列在 Letter 页内可读、上标未丢失、边距 3 cm 保持
