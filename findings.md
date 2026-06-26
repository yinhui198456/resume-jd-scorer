# 发现与决策

## 需求
- 修复 skill 的 3 个 P0 阻塞性问题
- 保持轻量，不引入复杂架构

## 研究发现

### 环境能力确认
| 工具 | 状态 | 版本 |
|------|------|------|
| tesseract | ✅ 已安装 | 5.3.4 |
| python-magic | ✅ 已安装 | available |
| pytesseract | ✅ 已安装 | available |
| Pillow | ✅ 已安装 | available |
| poppler | ✅ 已安装 | 24.02.0 |
| easyocr | ❌ 未安装 | - |

### P0-1: .bin 文件解析
- 使用 `python-magic` 检测 MIME type：`application/pdf` → PDF, `application/zip` → DOCX
- 不依赖文件扩展名

### P0-2: 上传文件搜索
- 搜索路径：`.codepilot-uploads/`
- 按 mtime 排序，列出最近 5 个非图片文件
- 对每个候选文件运行 magic 检测，排除非文档类文件

### P0-3: OCR 图片简历
- 方案：`pytesseract` + `Pillow`，使用 `--lang chi_sim+eng` 识别中英文
- 环境已有 Tesseract，无需额外安装

## 技术决策
| 决策 | 理由 |
|------|------|
| P0-1 用 python-magic | 已安装，API 简洁 |
| P0-2 用 os.listdir + sorted(mtime) | 简单，无需额外依赖 |
| P0-3 用 pytesseract + chi_sim | 本地运行，已有 Tesseract |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| | |

## 资源
- python-magic: `magic.from_file(path, mime=True)`
- pytesseract: `pytesseract.image_to_string(Image.open(path), lang='chi_sim+eng')`

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
