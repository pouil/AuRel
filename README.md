# AuRel

Metamorphic Testing of Task-Conditioned Acoustic Reliance in Audio Language Models.

## 从这里开始

第一次使用请读 **[中文入门：一步一步运行并读懂结果](docs/getting-started.zh.md)**。不需要先懂机器学习，也不需要 GPU 或录音。

想了解项目做到哪里、下一步做什么，请读 **[进度、最小验证目标与分工](docs/roadmap.zh.md)**；相关论文和可借鉴项目见 **[参考成果与选型](docs/related-work.zh.md)**。

当前阶段是合成音调演示。用户已选择：下一步优先最小化验证方法，先用公开数据，不自行录音。真实语音实验的命令尚未实现，不要把路线文档当作现成接口。

研究问题：同一声学变化，在词义任务中应被忽略、在副语言任务中应被利用时，模型能否正确切换依赖？进一步研究多因素交互是否造成可复现的安全策略违规，以及有预算的攻击搜索能否提高有效反例发现效率。

## Status

**Research scaffold, not a completed benchmark.** 当前可运行：CPU 合成音调实验、任务条件化标签映射、增益/噪声/顺序变化、随机与 UCB 搜索、近似有限零和博弈、逐例 JSONL 日志和单元测试。ToyModel 是人为编写的信号分类器，不是音频语言模型；结果不能用于论文中的模型性能或漏洞结论。

真实语音数据、人工有效性校验、真实模型适配器、组合覆盖生成、反例缩减、安全 oracle、成本约束博弈仍待实施。`models` 依赖只是候选技术栈，尚未完成兼容性验证或锁定。音调反转只用于测试条件化关系，禁止当作语音语义保持算子。

## Run

推荐 Python 3.11。核心实验只需 NumPy，无 GPU、无 API、无下载费用。

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m aurel.cli --seed 42 --budget 80 --output runs/demo
```

输出 `report.json` 和 `records.jsonl`。两个搜索器各消耗 budget 次变换后预测；矩阵测量另行计数。训练与测试按音源组隔离。游戏矩阵是在测试集上进行的描述性分析；若用其选择防御策略，必须另留最终测试集。

## Research design

见 [proposal-review.zh.md](docs/proposal-review.zh.md)，包含原 proposal 评审、安全红队路线、技术栈、指标与阶段验收条件。

## Repository publication

仓库：[pouil/AuRel](https://github.com/pouil/AuRel)，Private。不要把 API key、用户录音、权重或私有数据加入 Git。尚未选择开源许可证。
