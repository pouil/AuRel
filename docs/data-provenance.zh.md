# 第一对公开语音：来源核对与清单规范

更新：2026-10-25。本文完成数据接入前的来源核对，不表示已下载音频、选出合格配对或运行真实模型。实验范围和阈值沿用 [roadmap.zh.md](roadmap.zh.md)。下一步是实现最小清单生成器，不再扩大方案。

## 1. 数据从哪里来

使用 CREMA-D 官方仓库；本次记录的上游提交是 `1658cd342dff90010aa843eaeebd53610a08b1dc`。后续下载必须绑定这个提交，不能只记录会变化的 master。

- [来源与许可说明](https://github.com/CheyneyComputerScience/CREMA-D/blob/1658cd342dff90010aa843eaeebd53610a08b1dc/README.md)：数据库声明使用 ODbL 1.0，单项内容声明使用 DbCL 1.0。保留上游署名、论文引用和两种许可链接；AuRel 的代码许可不能替代数据许可。
- [预处理脚本](https://github.com/CheyneyComputerScience/CREMA-D/blob/1658cd342dff90010aa843eaeebd53610a08b1dc/processFinishedResponses.R)：官方处理包括排除首次情绪点击超过 10 秒的响应，不能直接把原始票数与处理后的票数混用。
- [票数汇总脚本](https://github.com/CheyneyComputerScience/CREMA-D/blob/1658cd342dff90010aa843eaeebd53610a08b1dc/tabulateVotesV2.r)：按片段和呈现方式分别统计六类情绪。
- [元数据目录](https://github.com/CheyneyComputerScience/CREMA-D/tree/1658cd342dff90010aa843eaeebd53610a08b1dc/processedResults)：存在 summaryTable.csv 和 tabulatedVotes.csv。本次仅核对目录及脚本，尚未逐行验证 CSV。

原始音频、完整标注表和权重暂不提交到 AuRel。先保存来源、获取方式、哈希和必要的逐例派生记录；若之后发布派生数据库或音频包，需另行核对相关许可义务。上游还请求使用者填写登记表；需要个人或机构信息时由用户自行决定并提交，代理不代填身份信息。

## 2. 如何避免选错标签

“演员打算表达高兴”和“听众确实听出了高兴”是两件事。NEU/HAP 文件名用于找到候选，audio-only 票数用于判断候选是否适合实验。

1. 只取声音呈现的投票。原始响应中的 queryType=1 表示声音，2 表示画面，3 表示音画。汇总脚本用 `100000 * queryType + clipNum` 构造分组行名；解析实际 CSV 时必须验证该编码及文件名映射，不靠行的前后顺序猜呈现方式。
2. 首选官方处理后的 tabulatedVotes.csv；检查 A/D/F/H/N/S 六列是非负整数，其和等于 numResponses，且分母大于零。summaryTable.csv 的 VoiceVote 仅用于交叉核对，不能单凭多数标签推算票比例。
3. 目标票比例 = 目标情绪票数 / 六类票数总和。neutral 对应 N，happy 对应 H。比例至少 0.60，并且目标为唯一最高票，才通过现有标签筛选。官方 agreement 是最高票比例，不一定是我们的目标标签比例。
4. 发现缺列、重复的声音记录、编码不明或表间冲突时记为待核对；不要偷偷改用音画票数或放宽阈值。人工可以标 uncertain。
5. 配对必须同一说话人、同一句台词。保留原始强度代码，不把不同强度或录音差异描述成“只有情绪改变”。现有台词范围 IEO/IOM/DFA/IWL 不变。

## 3. 第一版清单应记录什么

下面是待实现的数据约定，不是已经存在的命令接口。每条录音一条 JSONL；未测量值用 null，不能填入示例数字冒充结果。完整候选及排除理由另存一份，避免只保留成功样本。

| 字段 | 内容及作用 |
|---|---|
| schema_version | 固定为 1，便于以后发现格式变化 |
| dataset / source_revision | CREMA-D 和完整上游提交号 |
| source_path / source_url | 精确到 AudioWAV 下的文件及固定版本来源 |
| license_urls / attribution | 上游声明的 ODbL、DbCL 链接及数据集论文引用 |
| clip_id / speaker_id / sentence_id | 原始文件标识、说话人、台词代码 |
| pair_id / intended_emotion / intensity | 同人同句配对标识、文件名情绪、原始强度代码 |
| annotation_path / annotation_sha256 / annotation_row_id | 投票表来源、实际下载字节哈希、原始行标识 |
| annotation_modality / votes / target_vote_fraction | 必须为 audio-only；保留六类票数及目标比例 |
| audio_sha256 / bytes / sample_rate / channels / duration_seconds | 实际音频文件的哈希和解码测量，不能来自文件名猜测 |
| status / exclusion_reasons | candidate、metadata_eligible、audio_validated 或 excluded，以及明确原因列表 |
| human_review_status | pending、pass、uncertain 或 fail；机器校验不等于人工通过 |

下载检查顺序：确认不是 Git LFS 占位文本 → 解码成功 → 检查时长、非静音和截断 → 记录哈希 → 人工确认台词与情绪。官方提示 audio-only 评分使用 MP3，而计算处理使用 WAV；对选中片段须核对二者对应关系和已知异常，不能无条件将评分移植给任何同名 WAV。

本地运行产物放入已忽略的 runs/ 子目录。完成候选清单后先冻结筛选规则和选中的一对，再进行模型推理。多条录音如何稳定选取及并列处理需在生成器中明确并测试；不得按模型失败率选择。

## 4. 今天的验收与下一步

已核对：官方 README、上游提交号、两个 R 脚本、processedResults 目录；确认声音投票与音画投票必须分开，并识别最高票比例不等于目标票比例的问题。

尚未完成：CSV 行级解析、真实文件下载和哈希、第一对有效样本、真实模型输出。本次只新增本文，不修改程序和原实验阈值，因此不把已有程序测试作为数据有效性的证据。

下次只推进最小清单生成器：读取固定版本投票表，验证字段和声音来源，输出可追溯候选及排除原因；针对混入视频票、零票、重复记录和目标标签不符做小型测试。真实数据检查通过后再选第一对音频。

## 5. 人工需求表

目前没有需要你立即提供的录音或标注。以下是后续触发时才需要的操作，不阻塞清单生成器开发。

| 编号 | 何时需要 / 所需操作 | 原因 | 格式及示例 | 数量 / 耗时估计 | 验收标准 | 公开数据替代 / 是否阻塞 |
|---|---|---|---|---|---|---|
| H01 | 第一对四条件音频准备好后，盲听并标注 | 检查噪声后是否仍能判断内容和情绪 | 按 review-template.zh.md；例如内容一致=yes，情绪=uncertain，不需猜测 | 4 段，约 5–10 分钟 | 每段内容、情绪和清晰度都有判断；分歧保留 | 原始 audio-only 票数可辅助，但不能证明加噪声后的有效性；阻塞确认真实反例，不阻塞代码开发 |
| H02 | 仅当需要本人登记时，自行处理上游使用登记表 | 上游希望记录数据集使用情况 | 在上游表单填写真实情况；无需把个人信息发到聊天 | 1 次，约 3–5 分钟 | 用户确认已处理或明确暂不提交；代理不冒充填写 | 暂不自动换数据集；当前不阻塞来源核对和代码开发 |
| H03 | 仅当真实模型接入实测受阻时，选择本地运行方式 | 8GB 显存是否足够尚未验证 | 届时提供实际错误、内存/时间测量和选项；用户选择可接受耗时 | 1 次，估计 5 分钟决策 | 明确可接受方案；没有付费授权就不租算力 | 优先免费本地方案；可能阻塞模型推理，不阻塞数据准备 |

人工听音细节见 [审核模板](review-template.zh.md)。现在无需自行准备数据。
