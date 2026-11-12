# 第一对公开语音：来源核对与清单规范

更新：2026-10-28。元数据生成器已在官方 CSV 上验证，第一对真实 WAV 已固定选取并通过技术检查，操作见第 6–7 节。第 1–5 节保留来源核对和数据约定；第 4 节为 10 月 25 日进度。人工语义/情绪审核和真实模型推理尚未完成。实验范围和阈值沿用 [roadmap.zh.md](roadmap.zh.md)。

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

## 6. 2026-10-26：运行元数据清单生成器

新增 `python -m aurel.crema_manifest`，仅需 Python 标准库。它读取本地两个 CSV，不联网、不运行模型，也不自动认定音频可用。请在仓库根目录运行。

先获取固定版本的两个公开文件（约 4 MB，无音视频）：

```powershell
New-Item -ItemType Directory -Force runs/crema-source | Out-Null
$cremaRoot = 'https://raw.githubusercontent.com/CheyneyComputerScience/CREMA-D/1658cd342dff90010aa843eaeebd53610a08b1dc'
Invoke-WebRequest "$cremaRoot/processedResults/tabulatedVotes.csv" -OutFile runs/crema-source/tabulatedVotes.csv
Invoke-WebRequest "$cremaRoot/SentenceFilenames.csv" -OutFile runs/crema-source/SentenceFilenames.csv
python -m aurel.crema_manifest --votes runs/crema-source/tabulatedVotes.csv --mapping runs/crema-source/SentenceFilenames.csv --source-revision 1658cd342dff90010aa843eaeebd53610a08b1dc --output runs/crema-metadata
```

若下载失败，停止并保留报错，不要拿其他版本冒充。此处 PowerShell 下载方式是供读者使用的等价操作；本次实际通过 Python urllib 从同一固定 URL 下载并校验。生成器中的 source_revision 是用户声明，工具不会联网认证其真实性，因此同时记录两个文件的 SHA-256。首次重跑可对照本次实测：

| 文件 | SHA-256 |
|---|---|
| tabulatedVotes.csv | 774d9d759cb5caf2542758a39eca8c0f1d2777f9987ff5d5adf8066d192f377b |
| SentenceFilenames.csv | d88cb50e84bbc30b2e159cdfc25e1cf87777ad97c7c41d6ab8f75d3383b8f740 |

输出目录必须不存在，防止覆盖前次结果；重跑请换新目录名。输出：

- manifest.jsonl：每条声音记录一行，保留范围外样本及排除原因，按 clip_id 排序。metadata_eligible 只表示元数据符合门槛，音频测量字段仍为 null，人工状态仍为 pending。
- summary.json：本次实测 7,442 条声音记录，434 条 metadata_eligible，7,008 条 excluded。排除原因可以重叠，不能相加当作样本数。输入表共 22,326 行，非声音行不进入清单。

生成器核对实际 CSV 的分组编号与 SentenceFilenames.csv 映射，拒绝未知呈现方式、重复记录、缺列、负数/非整数票数或票数和不符；结构损坏会终止整个生成过程，不输出看似成功的部分清单。零票和不符合范围/比例的样本保留排除理由。当前不自动选择强度版本、配对或分配开发/测试说话人。

验证：`python -m unittest discover -s tests -v` 共 11 项通过；包含原有 5 项和新增 6 项测试，覆盖视觉票混入、目标标签比例、0.60 边界、零票/并列、错误票数/模态、重复/错配和缺列。合成演示 `python -m aurel.cli --seed 42 --budget 80 --output runs/toy-check-20261026` 也通过，仍明确标记 synthetic_only。

下一步仅从清单稳定选取第一对候选并获取、校验 WAV；不能把 434 条候选说成 434 条有效音频或完整配对。人工需求仍见第 5 节，目前没有立即阻塞开发的人工任务。

## 7. 2026-10-28：第一对真实录音的技术验证

在现有清单中，87 个同人同句分组同时有 neutral 和 happy 候选。下载前固定选择规则：按 pair_id 字典序取第一个完整分组，每种情绪按 clip_id 字典序取首条。此规则用于单对开发验证，不代表随机抽样或最优情绪强度；没有根据模型输出或下载结果挑选样本，也没有改变 0.60 门槛。下载失败时保留原选择和错误，不自动替换。

在仓库根目录运行（manifest 路径按第 6 节实际输出调整，输出目录需不存在）：

```powershell
python -m aurel.crema_pair --manifest runs/crema-metadata/manifest.jsonl --output runs/first-pair --download
```

不加 --download 时只记录选择，不联网。加上后只下载选中的两个 WAV。工具先获取固定版本的 LFS 指针，再下载媒体文件，核对 SHA-256 和大小。输出 pair.json 包含选择规则、输入清单哈希、来源、逐例测量和失败记录；WAV 位于同一目录，均留在忽略的 runs/ 下，不推送音频。

| 文件 | 原始目标情绪票比例 | 时长 / 采样率 | 大小 / SHA-256 |
|---|---|---|---|
| 1001_IEO_NEU_XX.wav | 10/11 | 1.601625 秒 / 16000 Hz | 51296 字节；bbad5c4b884e8f677ef8801219b215441cba92da832fb57dfb89494ebdff8e9c |
| 1001_IEO_HAP_HI.wav | 0.60 | 1.7684375 秒 / 16000 Hz | 56634 字节；c7a8de9867f3fe4bfab59aa81a9ac32d058d0ebd814b7fb292913f7c59420690 |

本次实际运行用目录 runs/crema-pair-20261028，输入为 runs/crema-metadata-20261026/manifest.jsonl。两条文件均通过单声道 PCM16、帧完整性和非全零检查。technical_checks_passed=true 只代表这些检查；audio_validity_confirmed 仍为 false，human_review_status 仍为 pending，status 保留 metadata_eligible。技术检查无法判断句子是否正确、表演情绪是否明确或语音是否在语义上截断。MP3 评分与 WAV 的感知对应仍需审核，不能用同名和哈希代替听音。

`python -m unittest discover -s tests -v` 共 14 项通过。新增测试验证输入顺序不影响选择、不跨说话人配对、错配/重复/版本不符会拒绝，以及 LFS 占位、静音和帧缺失不会冒充正常 WAV。

尚未生成加噪声版本或调用真实模型。下一步制作这对录音的四条件材料与审核记录；听音任务在材料齐备后一次提交，当前不要求用户自行录音。权限和资料仍允许推进该步骤，尚未达到用户设定的停止上限。
