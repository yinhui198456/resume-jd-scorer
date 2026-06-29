# Graphify 移动端可读版

## 1. 有什么用

这不是给人从头读的长报告，而是项目地图。改代码前先查入口、影响面、相关测试和文档配置关系。

## 2. 图谱概况

- 247 nodes · 488 edges · 31 communities (13 shown, 18 thin omitted)

## 3. 核心入口

- `run_daily()`
- `PipelineDependencies`
- `FakeDelivery`
- `FakeCollector`
- `FakeGenerator`

## 4. 主要模块

- Digest Pipeline Stages
- Application Configuration
- Content Collection
- Pipeline Components
- Pipeline State Management
- Feishu Delivery System

## 5. 修改前怎么用

- 改飞书排版：查 `render_feishu_post()`
- 改资讯数量：查 `filters.yml`、`run_daily()`
- 改来源：查 `sources.yml`、collector
- 改分类：查 `topics.yml`、quality/filter
- 改定时：查 `schedule.yml`、deploy/service

## 6. 当前建议

保留 full graph 和本摘要。后续每次大改前先刷新图谱，再用 `graphify query` 或 `graphify affected` 查影响面。
