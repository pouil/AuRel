# AuRel

Metamorphic Testing of Task-Conditioned Acoustic Reliance in Audio Language Models.

## 从这里开始

先读 **[2026-11-10 proposal 校准报告与操作说明](docs/proposal-calibration.zh.md)**。当前主线：公开语音＋现成模型＋受控声学扰动＋多指标性能比较。报告优先于旧路线中冲突的内容。

想了解项目做到哪里、下一步做什么，请读 **[进度、最小验证目标与分工](docs/roadmap.zh.md)**；相关论文和可借鉴项目见 **[参考成果与选型](docs/related-work.zh.md)**。

已完成合成演示、CREMA-D追溯及两条真实WAV技术检查，并接入JiWER配对转写评分；尚无真实模型性能结果。情绪配对保留为旧数据流程示例，不自动扩展32对。

研究问题：同一批语音受到不同类型和强度的声学扰动后，模型性能如何变化？安全评估、博弈、自适应搜索、自动缩减不属于当前必做内容。稳定性能也是有效结果。

## Status

**Research scaffold, not a completed benchmark.** 当前可运行：CPU 合成音调实验、任务条件化标签映射、增益/噪声/顺序变化、随机与 UCB 搜索、近似有限零和博弈、逐例 JSONL 日志和单元测试。ToyModel 是人为编写的信号分类器，不是音频语言模型；结果不能用于论文中的模型性能或漏洞结论。

主实验仍缺真实模型适配器、五类真实扰动、人工输入审核和完整评估台账。`models`依赖尚未验证或锁定。音调反转仅用于旧演示，不是语音语义保持算子。

## 标准评分检查（无需模型）

```bash
python -m pip install -e ".[evaluation]"
python -m unittest discover -s tests -v
python -m aurel.score_asr --input examples/asr-scoring-fixture.jsonl --output runs/scoring-check.json
```

示例是手写测试文本，非模型输出。预期干净WER=0、扰动WER=0.5、增量=0.5。WER/CER越低越好；WER按整批参考词计数，可以超过1。输入及限制见校准报告。

## 旧合成演示 Run

推荐 Python 3.11。核心实验只需 NumPy，无 GPU、无 API、无下载费用。

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m aurel.cli --seed 42 --budget 80 --output runs/demo
```

输出 `report.json` 和 `records.jsonl`。两个搜索器各消耗 budget 次变换后预测；矩阵测量另行计数。训练与测试按音源组隔离。游戏矩阵是在测试集上进行的描述性分析；若用其选择防御策略，必须另留最终测试集。

## Research design

当前以[校准报告](docs/proposal-calibration.zh.md)为准。[旧评审](docs/proposal-review.zh.md)仅保留历史设计。

## Repository publication

仓库：[pouil/AuRel](https://github.com/pouil/AuRel)，当前公开。不要把 API key、用户录音、权重或私有数据加入 Git。尚未选择代码许可证；数据遵守各自许可。
