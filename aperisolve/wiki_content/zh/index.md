Title: Aperi'Solve 维基 - 隐写工具与指南
Description: Aperi'Solve 文档：分析的工作原理、各隐写工具（zsteg、steghide、binwalk、exiftool...）的指南，以及 CTF 速查表。
Order: 1

# Aperi'Solve 维基

欢迎来到 Aperi'Solve 维基。Aperi'Solve 是一个免费的在线平台，可对图片进行图层分析和隐写检测：在[首页](/zh/)上传一张图片，所有分析器就会自动运行。

本维基介绍如何解读分析结果，以及每个底层工具的工作原理，方便你在自己的机器上复现并扩展这些分析。

## 从这里开始

- [快速入门](/zh/wiki/getting-started) —— 如何使用 Aperi'Solve 并解读其结果。
- [隐写 CTF 速查表](/zh/wiki/cheatsheet) —— 针对图片、音频和文件格式类题目的实用检查清单。

## 工具指南

在你上传的图片上运行的每个分析器都有自己的页面：工具的作用、Aperi'Solve 执行的确切命令、如何解读输出，以及如何在本地安装。

- [位平面分解器](/zh/wiki/tools/decomposer) —— 可视化每个颜色通道的每一位。
- [颜色重映射](/zh/wiki/tools/color_remapping) —— 通过调色板变换揭示隐藏数据。
- [zsteg](/zh/wiki/tools/zsteg) —— 针对 PNG 和 BMP 的 LSB（最低有效位）隐写检测。
- [steghide](/zh/wiki/tools/steghide) —— 使用口令提取隐藏在 JPEG/BMP 中的数据。
- [binwalk](/zh/wiki/tools/binwalk) —— 查找并提取嵌入在图片内部的文件。
- [foremost](/zh/wiki/tools/foremost) —— 从图片中雕复（carve）出嵌入的文件。
- [exiftool](/zh/wiki/tools/exiftool) —— 读取元数据（EXIF、XMP、IPTC...）。
- [pngcheck](/zh/wiki/tools/pngcheck) —— 校验 PNG 结构并找出损坏的块（chunk）。
- [PCRT](/zh/wiki/tools/pcrt) —— 检测并修复损坏的 PNG 文件。
- [OutGuess](/zh/wiki/tools/outguess) —— 从 JPEG 图片中提取隐藏数据。
- [jsteg](/zh/wiki/tools/jsteg) —— 从 JPEG 的 DCT 系数中提取 LSB 数据。
- [JPHide/JPSeek](/zh/wiki/tools/jpseek) —— 从 JPEG 中提取 JPHide 载荷。
- [OpenStego](/zh/wiki/tools/openstego) —— 提取随机化的 LSB 隐写数据。
- [identify](/zh/wiki/tools/identify) —— 使用 ImageMagick 查看图片属性。
- [file](/zh/wiki/tools/file) —— 识别上传文件的真实类型。
- [strings](/zh/wiki/tools/strings) —— 查找图片文件中的可读文本。

欢迎在 [GitHub](https://github.com/Zeecka/AperiSolve) 上参与贡献。

## 什么是隐写分析？

隐写术把数据隐藏在看似无害的载体文件中 —— 对图片而言，这意味着操纵像素位、调色板条目、元数据字段，或文件结构本身。隐写分析（steganalysis）就是检测这类隐藏数据的技术。没有任何单一工具能覆盖所有手法，因此 Aperi'Solve 会并排运行一整套分析器，让你一目了然地对比它们的输出。
