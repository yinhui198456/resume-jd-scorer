# 简历 JD 评估打分服务

基于 LLM 的简历与职位描述（JD）匹配度评估系统。输入 JD 和简历，输出 100 分制评分、面试建议、评分依据和追问问题。

## 功能特性

- **两阶段评分**：基础匹配分（100分） × 可信度系数（0.5-1.0） = 最终得分
- **真实性验证**：自动识别培训痕迹、年限矛盾、职责夸张等红旗信号
- **JD 持久化**：首次上传的 JD 自动保存，后续评估默认复用
- **自动姓名提取**：从上传的简历中自动提取候选人姓名
- **面试题库生成**：10-20 道追问，区分验证类/技术类/场景类

## 评分维度

| 维度 | 满分 | 说明 |
|------|------|------|
| 硬性要求 | 40 | 学历、年限、语言能力等 |
| 技能匹配 | 30 | 硬技能/工具/框架覆盖度 |
| 经验匹配 | 20 | 过往业务场景与 JD 职责匹配度 |
| 潜力加分 | 10 | 开源贡献、大厂背景、跨领域能力 |

## 可信度系数

| 等级 | 系数 | 判定标准 |
|------|------|---------|
| 无 | 1.0 | 无明显疑点 |
| 轻微 | 0.9 | 1 个轻度红旗 |
| 中度 | 0.75 | 培训痕迹/项目存疑 |
| 严重 | 0.6 | 职责夸张 + 培训痕迹 |
| 极严重 | 0.5 | 时间线矛盾 + 多项造假嫌疑 |

## 输出格式

| 姓名 | 录入时间 | 联系方式 | 学历 | 工作年限 | 硬性 | 技能 | 经验 | 潜力 | 可信系数 | 合计 |
|------|---------|---------|------|---------|------|------|------|------|---------|------|
| 吕蜜 | 2026/6/25 | 189xxxxx | 大专+本科 | 10年+ | 38 | 28 | 18 | 7 | 0.6 | 55 |

## 项目结构

```text
.
├── .agents/skills/resume-jd-scorer/  # Skill 配置
│   ├── SKILL.md                      # Skill 使用说明
│   ├── scripts/
│   │   ├── evaluate.py               # LLM 评估核心逻辑
│   │   ├── parse_file.py             # PDF/DOCX/图片解析
│   │   ├── find_uploads.py           # 搜索上传文件
│   │   └── save_jd.py                # JD 持久化
│   └── data/
│       └── current_jd.json           # 已保存的 JD
└── resume-jd-scorer/                 # API 服务
    ├── main.py                       # FastAPI 入口
    ├── models.py                     # Pydantic 模型
    ├── scorer.py                     # 评分逻辑
    └── test_*.py                     # 单元测试
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://your-api-proxy.com/v1"
export ANTHROPIC_MODEL="qwen3.6-plus"

# 启动服务
uvicorn main:app --reload

# 访问 Swagger
open http://localhost:8000/docs
```

## API 接口

### POST /evaluate

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "jd_text": "职位：AI Infra 工程师\n要求：K8s 3年+",
    "resume_text": "张三 | 5年经验\nK8s..."
  }'
```

## 测试

```bash
cd resume-jd-scorer
pytest test_api.py test_parse.py test_save_jd.py -v
```

26 个单元测试全部通过。

## License

MIT
