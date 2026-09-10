# 2026-09-10 SJTU LaTeX 同步

这是上传时的历史快照；其后已续写模型假设，并删除本地根目录失效main.pdf。ZIP和本地PDF快照不提交Git，当前文稿以paper/overleaf/main.tex和SJTU编译结果为准。

- 目标项目：https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15
- 上传前备份：https://latex.sjtu.edu.cn/project/6aa2f413bd92933f73a7e404
- `CUMCM-current-source.zip`：本次23个实际工程文件，ZIP根目录直接对应线上项目根目录。
- `upload-manifest.json`：每个文件的路径、大小、SHA-256，以及线上核验结果。
- `local-compiled-preview.pdf`：上传时保存的本地编译预览，不是下载的线上PDF。

排除build/及编译辅助文件；根目录已有main.pdf按用户要求原样保留，是旧快照，最新正文应查看线上Recompile生成的预览。原线上项目中的无关模板图片和example.pdf保留，未删除。

已通过UI核验全部文件路径，在线main.tex + XeLaTeX + TeX Live 2025生成4页；背景、四条中国来源、图示版流程图均出现在预览中。日志有7条hyperref书签和未使用子图设置警告，无编译错误。线上中文正文采用服务端Fandol宋体，源文件未作字体替换，因此不声明与macOS本地PDF逐像素相同。

上传前后本地23个文件哈希全部一致。未进行线上ZIP下载回读哈希认证；本次以实际上传完成、目录树、编译日志和页面检查为验证证据。
