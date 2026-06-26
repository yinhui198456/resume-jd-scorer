# 任务计划：resume-jd-scorer skill P0 问题修复

## 目标
修复 skill 的 3 个阻塞性问题，确保用户上传的文件（PDF/.bin/图片）能被正确解析并用于评估。

## 当前阶段
阶段 5

## 各阶段

### 阶段 1：问题诊断与技术方案确认
- [x] 确认 .bin 文件实际是 PDF
- [x] 确认上传文件存放位置（`.codepilot-uploads/`）
- [x] 确认图片简历格式
- [x] 确认 OCR 方案：Tesseract + pytesseract + chi_sim
- **状态：** complete

### 阶段 2：P0-1 — 支持 .bin 文件解析（magic bytes 检测）
- [x] 修改 `parse_file.py`：使用 python-magic 检测 MIME type
- [x] 测试：.bin 文件 → 正确解析为 PDF 文本 ✅
- [x] Code review 修复：import 移至顶部、增加 DOCX MIME type、numpy 替换为 Pillow
- **状态：** complete

### 阶段 3：P0-2 — 增加上传文件搜索逻辑
- [x] 新增 `find_uploads.py` 脚本
- [x] 搜索 `.codepilot-uploads/` 和 `/tmp/`（限定前缀）
- [x] Code review 修复：import 移至顶部、/tmp 限定前缀、删除未使用常量、增加文件大小过滤
- **状态：** complete

### 阶段 4：P0-3 — 集成 OCR 支持图片简历
- [x] `parse_image()` 函数：Pillow 灰度化 + 二值化 → pytesseract OCR
- [x] 测试：图片 → 文本提取成功 ✅
- [x] Code review 修复：numpy 替换为 Pillow `point()`
- **状态：** complete

### 阶段 5：测试与验证
- [x] P0-1 验证：.bin → PDF 文本 ✅
- [x] P0-2 验证：find_uploads.py 找到候选文件 ✅
- [x] P0-3 验证：图片 → OCR → 文本 ✅
- [x] 回归测试：4 个 unit test 全部通过 ✅
- [x] Code review：无 CRITICAL/HIGH 问题
- **状态：** complete

## 已做决策
| 决策 | 理由 |
|------|------|
| python-magic 检测 MIME type | 已安装，不依赖扩展名 |
| pytesseract + chi_sim | 本地运行，已有 Tesseract |
| Pillow point() 替代 numpy 二值化 | 减少依赖，code review 建议 |
| /tmp/ 搜索限定前缀 | 避免扫描全系统无关文件 |

## 备注
- P0-1/P0-2/P0-3 全部完成，code review 问题已修复
- 4 个回归测试通过 → 25 个测试通过（含 16 个姓名提取测试）
- P1 改进：候选人姓名自动提取已集成到 find_uploads.py
