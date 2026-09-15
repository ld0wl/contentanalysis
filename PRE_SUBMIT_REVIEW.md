# PRE_SUBMIT_REVIEW — INQUIRY 投前审计（第 3 版包：ghost-ref 清理后）

- 目标期刊：*INQUIRY: The Journal of Health Care Organization, Provision, and Financing*（Sage，双盲，OA，APC $3200）
- 刊规依据：https://journals.sagepub.com/author-instructions/INQ ＋ 本地摘录 `inq_guidelines.md`
- 栏目：Original Research（≤5000 词含表、≤3 表、结构化摘要 ≤250 词、AMA 上标引注）
- 审计日期：2026-09-15
- 审计范围：**仅格式/合规/引用一致性**。未改写任何科学结论、样本量、码本数字。
- 审计对象（以本轮最新上传为准，早期两版仅作对照）：

| 文件 | SHA-256 前 12 位 | 说明 |
|---|---|---|
| `inq_manuscript_blind.docx`（e038） | `46502ef4c665` | 匿名主稿，Option A 三表版 + 参考文献 1–33 |
| `inq_title_page.docx`（7993） | `b70656920a83` | 标题页，内容与上一版逐字相同 |
| `inq_cover_letter.docx`（7d86） | `d5ef3e1938df` | 封面信，**内容与上一版逐字相同（未随 Option A 更新）** |
| `inq_README.md`（d3f6） / `inq_CHANGELOG.md`（410c） | `746e17df8afd` / `14479ffcdf11` | 说明文件 |

---

## 1. 总判定

**结论：条件放行（GO after must-fix）。当前文件状态 = NO-GO，修完下列 4 项 must-fix 后可投。**

- 前两版的两个阻塞项（5 表/≈6.1–6.5k 词；17 条 ghost 参考文献）在本版**均已消除**。压词后复审已完成：实测 body+tables 远低于 5000。
- 剩余 must-fix 全部是格式/措辞层面（封面信过期、AMA 引用编号顺序、DIGITAL HEALTH 残留句、匿名伦理声明缺失），**不涉及科学内容**，预计修改量很小。
- 领域贴合度（卫生组织/供给/筹资）仍是编辑初审最大风险，封面信目前只用 "insofar as" 弱化承接，建议加强但不作为阻塞。

## 2. 硬性检查 Pass/Fail 一览

| 检查项 | 结果 | 实测证据 |
|---|---|---|
| 双盲匿名 | **PASS** | 主稿全文 0 次命中：作者名、SCUT/South China/Guangzhou、ORCID、邮箱、Grok；无 Guarantor/CRediT/Acknowledgements 正文；docx 元数据 author=`python-docx`，无修订痕迹、无批注 |
| 结构化摘要 ≤250 | **PASS** | 237 词（含 5 个小标题）/ 232 词（不含小标题）；README 记 242；与 `inq_structured_abstract.md` 逐段一致；与前两版完全相同 |
| 关键词 ≥5 | **PASS** | 8 个 |
| 词数 ≤5000（含表，不含摘要/关键词/参考文献） | **PASS** | 本审计口径：正文 4602 + 表格单元格 246 = **4848**；README 口径 4952。两种口径均 <5000。若把匿名 COI（14 词）也算入仍 <5000 |
| 表数 ≤3 | **PASS** | 正文 3 表（Table 1 framings / Table 2 stances / Table 3 synthesis），置于参考文献之后（符合 "tables at end"）；正文无 Table 4/5 残留；S2/S3 已正确指向 Supplemental |
| 参考文献：无 ghost / 无 orphan / 序列完整 | **PASS** | 33 条参考文献，编号 1–33 连续；45 处上标全部数字；被引集合 = {1…33}；ghost 0，orphan 0 |
| 参考文献：AMA 首现顺序编号 | **FAIL（must-fix #2）** | 首现顺序为 …20, 21, **27, 25, 26, 22, 23, 24**, 28… — 22–27 六条不按首现顺序 |
| AMA 上标位置 | 部分不合（should-fix） | 45 处上标全部前置空格，44 处置于句号/逗号**之前**（AMA 要求紧贴文字、置于句号逗号之后） |
| 匿名 COI 声明置于 References 前 | **PASS** | 标题 "Declaration of Conflicting Interests" + 刊规原句，在 References 之前 |
| 匿名伦理声明在主稿内 | **FAIL（must-fix #4）** | 主稿只写 "Ethics are restated under Statements and Declarations"，但盲稿内**不存在**该节（已移到标题页） |
| GenAI 非作者 | **PASS** | 标题页 Acknowledgements 披露 xAI Grok 用途并声明非作者；封面信同步声明 |
| 主稿左右边距 ≈3 cm | **PASS** | L=3.00 cm / R=3.00 cm（上下 2.54）；Letter 纸 |
| 双倍行距、10/12 pt | **PASS（附注）** | 全文 line=480（双倍）；正文 12 pt Times New Roman；Table 3 为 8 pt（见 should-fix） |
| 封面信 | **FAIL（must-fix #1）** | 内容与压词前版本逐字相同，仍声明 "压词/减表尚未执行"，与主稿实况矛盾 |
| 标题页 | **PASS** | 作者/ORCID/邮箱/单位、Guarantor、伦理（无需审批，公开数据）、知情同意 N/A、Funding、CRediT、AI 披露、数据可用性、COI 齐全 |
| 上传清单 | 待确认 | Figure 1 单独文件、Supplemental（S2/S3 新增）按 README 清单准备；见 should-fix #6 |

## 3. Must-fix（投稿前必须完成，全部为格式/措辞层）

1. **封面信过期（`inq_cover_letter.docx`）。** 第 4 段仍写：*"Word-count and table-count compression to meet INQUIRY's Original Research limits … is marked for web-side decision and is not executed in this format pack."* 与本版主稿（3 表、<5000 词）矛盾，编辑会直接看到。改为已完成压缩的表述（或删去该句），并同步说明两表下沉为 Supplemental Table S2/S3。同时建议把开头 "insofar as" 的弱承接改为更明确的 scope 论证（见 should-fix #7）。

2. **参考文献编号未按 AMA 首现顺序。** Roske（现 27）在 Introduction 第 3 段首现，早于 Brause（25）、Bucher 2012（26）、Bareis/Richter/Laba（22–24）。需第二次重映射（仅改编号，不改文献本身）：

   | 现号 | → 新号 | 文献 |
   |---|---|---|
   | 27 | 22 | Roske 2026 |
   | 25 | 23 | Brause 2025 |
   | 26 | 24 | Bucher 2012 |
   | 22 | 25 | Bareis & Katzenbach 2022 |
   | 23 | 26 | Richter 2025 |
   | 24 | 27 | Laba 2026 |

   其余 1–21、28–33 不变。涉及上标位置：P013/P018（27）、P015/P019/P040（25）、P020（26）、P106（22,23,24 与 22,23）、P119（22,23）、P105（20,27）。改完请重新跑一次 orphan/ghost 校验。

3. **"DIGITAL HEALTH has published …" 残留两句（针对前一目标刊的措辞）。** Discussion "Comparison with prior work"：
   - *"DIGITAL HEALTH has published Douyin health-education work ^19."*
   - *"DIGITAL HEALTH has published a summative content analysis of English-language TikTok mental-health videos ^33."*
   这是为 DIGITAL HEALTH 投稿写的"贴刊"句，对 INQUIRY 无意义且暴露转投痕迹。仅改主语（如 "Douyin health-education work has been published^19" / "A summative content analysis … has been published^33"），不动引用与论点。

4. **盲稿缺少匿名伦理声明。** Methods 末句 "Ethics are restated under Statements and Declarations" 指向盲稿中不存在的章节。刊规要求涉及人类数据的稿件在主稿内说明是否获伦理审批。建议在匿名 COI 之前（或替换该句）加一句匿名版：*"Ethical approval was not required: the analysis used only publicly available Douyin videos and first-level comments; no participants were recruited or contacted."*（与标题页表述一致，不含机构名）。

## 4. Should-fix（建议修，不阻塞投稿）

1. **AMA 上标位置。** 全部 45 处形如 `design ^1.`（上标前有空格、在句号前）。AMA：`design.^1`（紧贴、在句号/逗号后；分号/冒号前）。可批量处理。
2. **表题与表体分离。** Table 1/2/3 的标题与脚注留在正文位置，而表格本体在 References 之后无标题。建议把 caption + note 随表移到文末（正文只留 "(Table 1)" 呼叫），避免审稿人看到无题表格。
3. **Li 2023（ref 2）"mostly specialised" 残留。** CHANGELOG 声明已删，但只删了 Introduction；Discussion "Comparison with prior work" 首句仍为 *"… and mostly concerns specialised agents ^2"*。lit-verify 结论是该表述"仅凭摘要不足以支持"。请作者核对全文后决定保留或删除后半句（不改研究本身的结论）。
4. **参考文献 AMA 细节。** (a) ref 13 期刊名 "Journalism and Media" 未缩写（NLM 缩写为 *Journal Media*）；(b) 页码范围用了 en dash（AMA 用连字符）；(c) ref 29/30 "Epub ahead of print" 建议改为 AMA 的 "Published online [date]. doi:…" 形式（无日期则保留现状，不得编造页码——README 已明确）。
5. **Table 3 为 8 pt。** 刊规写 "10/12 point"。7 列宽表用 8 pt 可理解，但可考虑 9–10 pt 或横向页；若保持 8 pt 请确认 PDF 转换后可读。
6. **Supplemental 引用完整性。** 正文仅呼叫 Supplemental Table S2、S3；README 列出的 codebook、Figure S1、Table S1、SRQR 在正文无呼叫。建议在 Methods 末或 Declarations 前加一句 "Supplemental material (codebook, Table S1–S3, Figure S1, SRQR checklist) is available online"，或至少确保上传文件与呼叫一致。
7. **封面信 scope 论证偏弱。** INQUIRY 定位为 health care organization / provision / financing；现稿是健康传播/平台内容分析，封面信以 "insofar as" 承接。建议明确落到 provision 与 help-seeking pathway、service expectations、escalation to formal care 的关系，并点出 institutionally bounded capacity（热线扩容、家长助手）这一与"服务供给组织"直接相关的发现。仍是判断风险，不算格式错误。
8. **首页说明括号句。** 主稿首页 `[Anonymized manuscript for double-anonymized peer review …]` 一句是给编辑看的说明，可保留；若保留请确保不计入词数（当前审计未计入）。

## 5. lit-verify 已知项对照（本版状态）

| 项 | 状态 |
|---|---|
| 0 orphan 上标 / 0 缺文献 / 0 编号错 | ✅ 保持（45 上标 ↔ 33 文献全对应） |
| 17 条 ghost 文献（旧 20,22,24–27,30,33,36–44） | ✅ 已删除；另删旧 35 Bucher 2018；总数 51 → 33 |
| ref 35（Bucher 2018）过载 | ✅ 已从 "national care imaginary" 句移除并删条；该句现只引 Bareis/Richter |
| ref 34（Bucher 2012，现 26）过载 | ✅ 已从 no-API 抽样框句移除；仅保留在 "recommendation opaque / like counts" 一句（1 处） |
| ref 2 "mostly specialised" 摘要不足支持 | ⚠️ **部分完成**：Introduction 已删，Discussion 仍保留（should-fix #3） |
| Option A（保留旧表 1+4+5） | ✅ 已执行；旧表 2/3 → S2/S3；"压词后需复审" 已完成复审（见 §2 词数行） |

## 6. 词数明细（供复核）

| 段 | 本审计（whitespace 分词） |
|---|---|
| Introduction → Conclusion 正文（含各级标题、Figure 1 图题 6 词、三条表题+脚注 41 词） | 4602 |
| 三表单元格文字 | 246（T1 37 / T2 62 / T3 147） |
| **正文 + 表** | **4848** |
| 匿名 COI（不计） | 14 |
| 摘要 | 237（含标签）/ 232 |
| 前两版对照 | 第 1 版 6042+354=**6396**（5 表）；第 2 版 4616+246=**4862**（3 表） |

README 记 4952，差异来自分词口径（数字、括号、κ 等符号是否单算），不影响结论。

## 7. 审计方法

- `python-docx` 直接解析 docx XML：按 `w:vertAlign=superscript` 抽取上标引注；统计 `w:tbl` 数量与位置；读取 `w:sectPr` 边距、`w:spacing` 行距、`w:sz` 字号；检查 `w:ins/w:del/w:comment*`；读取核心属性。
- 匿名性：对主稿全文 grep 作者姓名、单位、城市、ORCID、邮箱、AI 工具名、致谢/贡献/资助关键词。
- 与前两版主稿逐段 diff，确认本轮改动仅限 CHANGELOG 声明的引用/措辞处；摘要、表格数字、五框架名称、327/137/32/25 等冻结数字无变化。
- 标题页与封面信：与上一版逐字 diff，结果为零差异（因此封面信过期）。
