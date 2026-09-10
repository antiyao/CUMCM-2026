# C题材料归类记录（2026-09-10）

接管分支 main，原有未提交的 CURRENT_STATE/DECISIONS/TODO 和 paper 工作区均保留；原始差异快照在 results/audit/intake/。只发现总指令 v2，按实际版本执行。有界扫描只找到根 AGENTS.md，没有相关子目录追加规则。

```text
C题/C题.pdf                     -> docs/problem/2026C/C题.pdf
C题/附件/附件1.xlsx 至附件4.xlsx   -> data/raw/2026C/（原名）
C题/附件/附件5/五个result*.xlsx   -> data/templates/2026C/（原名）
format2026.doc                  -> docs/rules/format2026.doc
configs/2026c.json               统一相对路径与主参数
data/processed/2026C/            派生数据
results/q1/                     实算明细和验证
results/submission/             模板导出副本
```

五个 result 工作簿全单元格检查仅含表头、日期、时间标签、示例省略号，无已填结果、无公式，确认为空模板。未发现压缩包。全部11个原件先保存迁移映射再执行，SHA-256与大小见 FILE_RELOCATION_MANIFEST.csv，迁移前后字节一致。没有目标冲突或未归类C题原件。空旧目录可能保留，不删除隐藏内容。

总指令、AGENTS.md、.git、历史技能/知识库、已有 paper 资料保持原位置。未发现活跃代码或 README 引用旧C题材料路径；总指令原位置描述保留，README新增入口，不做全库替换。

复核命令：`python src/organize_intake.py` 对已存在清单只做哈希验证。

恢复方法：逐条读取清单，仅当新路径哈希与sha256_before相同且旧路径不存在，创建旧父目录并移动回去；旧路径已存在则停止该条，禁止覆盖。恢复需同步 configs 和新增脚本读取路径。本轮未执行逆向迁移。原件只有路径变化，新配置/审计/结果为独立内容变化；模板标签错误不通过重新保存原模板修复。
