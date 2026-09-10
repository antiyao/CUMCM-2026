# 神秘卷3风格图示版

已在Canva创建并保存： https://www.canva.com/design/DAHU0aqVVig/mjgvOiLyeP096QiViStfFg/edit

## 文件

- `Canva导出_图示版.pdf`：从Canva正式保存的第4版设计导出，已关闭扁平化，全部为矢量对象，嵌入思源宋体常规体；论文当前使用此文件的独立副本。
- `Canva导出_图示版.png`：上述实际Canva导出文件的预览。
- `微网研究流程图_图示版.svg`：本地原生SVG绘图源，文字、边框、箭头和小图均可编辑，采用STSong；不是从Canva下载的SVG。Canva SVG下载当前显示为高级版功能，未购买升级。
- `微网研究流程图_图示版.html`：导入Canva的布局源。导入时缺失的部分图形已在Canva内用原生SVG补齐，并通过页面和导出PDF核验。
- `微网研究流程图_图示版.pdf`：本地STSong版导出，供再编辑参考；论文采用上面的实际Canva导出。
- `icons/`：8个主题原生SVG图标及计划表行线。
- `交付核验.json`：Canva设计ID、提交记录、字体和文件哈希。

## 编辑与复现

后续直接在Canva编辑设计；字体已在编辑器中使用“全部更改”统一为思源宋体。需要逐个选取文字时可通过“调整图层→图层”面板选择。

本地图形由`src/draw_workflow_canva.py`及`icons/`生成，使用Codex工作区附带的Python/reportlab。STSong字形缓存由`src/draw_workflow.py`从本机Songti字体集合提取，不向Canva上传本机字体文件。HTML再导入后需重新核对字体与SVG显示，不能假定直接复现Canva的已修正版本。

图参考神秘卷3第3页的四栏小图示结构，内容重新绘制为微网模型。预测曲线明确标为“示意”，不对应任何数值试验；Q3不宣称更新预报必然省费，Q4保留未来电价未知的暂定边界。

AI辅助用于内容组织、SVG源图制作、Canva创建与编辑、导出和检查，队员人工审阅仍待进行。此前Canva AI候选任务仅启动，最终交付以本设计的实际保存与导出为准。
