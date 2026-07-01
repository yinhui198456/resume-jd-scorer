# 简历 JD 评估打分服务

基于 LLM 的简历与职位描述（JD）匹配度评估 MVP。输入 JD 和简历文本，输出 100 分制评分、面试建议、评分依据和追问问题。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量（已有 LLM API 通道则无需修改）
export ANTHROPIC_AUTH_TOKEN="your-api-key"
export ANTHROPIC_BASE_URL="https://your-api-proxy.com/v1"
export ANTHROPIC_MODEL="qwen3.6-plus"

# 启动服务
uvicorn main:app --reload

# 访问 Swagger 文档
open http://localhost:8000/docs
```

## API 接口

### POST /evaluate

评估简历与 JD 的匹配度。

**请求体：**
```json
{
  "jd_text": "职位：高级 Java 后端工程师\n要求：\n- 5 年+ Java 开发经验\n- 熟练掌握 Spring Boot、MySQL、Redis",
  "resume_text": "张三 | 5 年 Java 后端开发\n学历：本科 计算机科学与技术\n经历：..."
}
```

**响应体：**
```json
{
  "success": true,
  "result": {
    "total_score": 88,
    "recommendation": "INTERVIEW",
    "dimensions": {
      "hard_requirement": { "score": 38, "max_score": 40, "weight": 0.4, "evidence": "..." },
      "skill_match": { "score": 27, "max_score": 30, "weight": 0.3, "evidence": "..." },
      "experience_match": { "score": 15, "max_score": 20, "weight": 0.2, "evidence": "..." },
      "bonus_potential": { "score": 8, "max_score": 10, "weight": 0.1, "evidence": "..." }
    },
    "strengths": ["5年Java经验", "有大厂背景"],
    "weaknesses": ["Kafka实战不足"],
    "follow_up_questions": [
      { "question": "如何处理高并发库存扣减？", "dimension": "experience_match", "intent": "验证实战深度" }
    ],
    "summary": "候选人匹配度高，建议面试。"
  }
}
```

### GET /health

健康检查。

**响应：**
```json
{ "status": "ok" }
```

## 评分规则

| 维度 | 满分 | 说明 |
|------|------|------|
| 硬性要求匹配度 | 40 | 学历、年限、语言能力等 |
| 技能匹配度 | 30 | 硬技能/工具/框架覆盖度 |
| 经验匹配度 | 20 | 过往业务场景与 JD 职责匹配度 |
| 潜力/加分项 | 10 | 开源贡献、大厂背景、跨领域能力 |

### 建议阈值

| 总分 | 建议 | 含义 |
|------|------|------|
| ≥ 75 | `INTERVIEW` | 建议面试 |
| 50 - 74 | `BACKUP` | 备选 |
| < 50 | `REJECT` | 不建议 |

### 缺失信息处理

简历中未提及的维度，该项得分 = 0，evidence 标记为 **"未体现"**。

## 项目结构

```
resume-jd-scorer/
├── main.py              # FastAPI 入口（路由 + 健康检查）
├── models.py            # Pydantic 请求/响应模型 + 校验
├── scorer.py            # LLM 调用 + 评分逻辑 + 结果修正
├── requirements.txt     # Python 依赖
└── test_api.py          # 单元测试（9 个）
```

## 运行测试

```bash
pytest test_api.py -v
```

| 测试 | 覆盖点 |
|------|--------|
| `test_schema_model_validate` | Pydantic 模型校验 |
| `test_schema_total_score_auto_fix` | 总分与维度之和不一致时自动修正 |
| `test_evaluate_high_match` | LLM 评估高分候选人 → INTERVIEW |
| `test_evaluate_low_match` | LLM 评估低分候选人 → BACKUP/REJECT |
| `test_empty_input_rejected` | 空输入返回 422 |
| `test_missing_field_rejected` | 缺必填字段返回 422 |
| `test_llm_failure_returns_error` | LLM 异常返回通用错误消息，不泄露内部细节 |
| `test_boundary_score_75_is_interview` | 恰好 75 分 → INTERVIEW |
| `test_boundary_score_49_is_reject` | 恰好 49 分 → REJECT |

## 架构说明

```
┌──────────┐    POST /evaluate    ┌───────────┐    Anthropic API    ┌─────────────┐
│  Client   │ ──────────────────► │  FastAPI  │ ──────────────────► │  qwen3.6+   │
│  (curl)   │ ◄────────────────── │  (main)   │ ◄────────────────── │  (LLM)      │
└──────────┘   EvaluationResult   └───────────┘   JSON response     └─────────────┘
                                         │
                                         ▼
                                  scorer.py
                                  - 构建 prompt
                                  - 调用 LLM
                                  - 校验 + 修正结果
```

- **无数据库**：MVP 阶段所有评估结果仅在本次请求中返回，不做持久化
- **LLM 客户端单例**：模块级复用，避免每次请求重建连接
- **双重校验**：Pydantic Field 约束 + model_validator 自动修正

## 注意事项

- 日志中不会输出候选人 PII 信息（debug 级别仅记录响应长度）
- 错误响应不暴露内部堆栈或实现细节
- 评分规则权重和阈值集中在 `scorer.py` 的 `DIMENSION_CONFIG` 常量中，修改时只需改一处

## 前端使用

### 开发模式

```bash
# 终端 1：启动后端
cd /opt/personal-agent-workspace/resume-jd-scorer
uvicorn main:app --reload --port 8000

# 终端 2：启动前端
cd /opt/personal-agent-workspace/resume-jd-scorer/frontend
npm run dev
```

访问 `http://localhost:5173`。

### 生产模式

```bash
cd /opt/personal-agent-workspace/resume-jd-scorer/frontend
npm run build
cd ..
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000`。
