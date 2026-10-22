# 人工审核模板（真实语音阶段使用，当前尚无待审核音频）

目的：确认测试输入和预期答案是否可信。无需懂机器学习。不需要新录音。先独立听音，再看模型结果，避免被模型回答影响判断。

## 每对音频怎么审核

1. 戴耳机听 A 和 B，各最多三次；不先看预设情绪标签。
2. 从给出的台词选项中选择听到的句子，听不清就填 unclear。
3. 分别选 neutral / happy / other / unclear；不要因为被告知“演员演的是开心”就照填。
4. 听加噪声的 C 和 D，再判断台词与情绪是否仍能辨认。
5. 四条判断填完以后，再查看参考标签和模型输出，记录异议。

复制下面一段，为每对录音填写一次：

```text
pair_id:
reviewer_id: 例如 R01，不用真实姓名
date:
A_听到的台词选项:
A_情绪: neutral / happy / other / unclear
B_听到的台词选项:
B_情绪: neutral / happy / other / unclear
C_听到的台词选项:
C_情绪: neutral / happy / other / unclear
D_听到的台词选项:
D_情绪: neutral / happy / other / unclear
A与B台词是否相同: yes / no / uncertain
是否有截断或异常: yes / no / uncertain
音频有效性: valid / invalid / uncertain
原因或备注:
查看模型输出后，是否同意失败判定: yes / no / uncertain / 尚未查看
模型输出判定理由:
```

uncertain 不是错误，也不是失败，是需要保留的不确定性。另一位审核者独立填写；两人有分歧时保留原记录，再讨论或由第三人裁决。没有第二位审核者时标为单人核查。

只审核失败会高估测试质量，所以程序还应预先随机抽取通过样本让你审核。具体文件清单、播放链接与任务选项将在真实数据加载器完成后提供；现在不需要自己找 64 条录音。
