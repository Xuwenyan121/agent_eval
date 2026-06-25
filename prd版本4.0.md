Agent智能体企业级可视化评测平台 - 产品需求文档（PRD V4.0）
版本：V4.0（MLflow + DeepEval 混合架构）
日期：2026-06-18
状态：详细设计版

文档变更记录
版本	日期	变更说明
V2.0	2026-06-18	基于 EvalScope 的初版设计
V3.0	2026-06-18	重构评测引擎为 DeepEval，新增自研 SSE 采集层
V3.1	2026-06-18	恢复业务 7 维度评分体系，新增传统 ML 指标，深色主题
V4.0	2026-06-18	架构升级为 MLflow + DeepEval 混合方案：MLflow 作为平台底座（实验追踪/UI/Trace/人工反馈），DeepEval 指标作为可插拔 Scorer 注入
一、文档概述
1.1 架构升级背景
V3.0 方案采用纯自研 Django 后端 + Vue 3 前端，存在两个核心问题：

重复造轮子：实验追踪、版本对比、Trace 可视化、人工反馈等能力需要从零建设

开发周期长：全栈自研 MVP 预估 6-10 周，前端工作量尤其沉重

V4.0 采用 MLflow + DeepEval 混合架构，核心思路：

层级	V3.0 方案	V4.0 混合方案
评测引擎	DeepEval 原生	✅ DeepEval（通过 MLflow Scorer 导入）
平台底座	自研 Django + Vue	✅ MLflow 开源平台（追踪/UI/Trace/对比/人工反馈）
Agent 采集层	自研 SSEAgentCollector	✅ 保留自研，作为数据采集前置步骤
自定义指标	自研 BaseMetric 子类	✅ MLflow 自定义 Scorer（内部调用 DeepEval GEval）
前端界面	全自研 Vue 3	✅ MLflow UI 为主 + 轻量 Vue 插件（业务特有功能）
开发周期	6-10 周 MVP	3-4 周 MVP
1.2 混合方案核心价值
价值点	说明
🚀 开箱即用的平台能力	实验追踪、版本对比、Trace 回放、人工反馈标注，无需从零开发
🧩 DeepEval 指标全覆盖	50+ DeepEval 指标通过 mlflow.genai.scorers.deepeval 原生导入
🔌 多框架混用	单次评测可混合 DeepEval、RAGAS、Guardrails 等框架的评分器
🎯 PRD 核心设计可复用	SSE 采集层、业务 7 维度定义、数据集管理逻辑均可保留
📉 降低长期维护成本	MLflow 由社区 + Databricks 持续迭代，非自研"轮子"
🔒 企业级就绪	支持私有化部署、SSO 集成、RBAC 权限控制
1.3 产品目标（不变）
目标	说明	优先级
业务导向评测	聚焦真实业务场景，不依赖通用 Benchmark	P0
端到端闭环	从数据集构建到报告生成的全流程自动化	P0
可视化运营	提供直观的评测看板和 Trace 回放能力	P0
多维度评估	支持自定义评测维度和评估器模板	P1
批量执行与 CI/CD 集成	支持定时任务和流水线触发	P1
BadCase 自动回流	低分样本自动回流入数据集，形成迭代闭环	P0
1.4 目标用户（不变）
用户角色	核心诉求	使用场景
AI 算法工程师	验证 Agent 能力、调试 BadCase	跑评测、看 Trace、迭代优化
产品/业务负责人	了解 Agent 整体表现和业务指标	查看报告、关注趋势
质量保障（QA）团队	构建和维护黄金数据集	标注数据、执行回归测试
DevOps 工程师	集成到 CI/CD 流水线	触发自动化评测
1.5 技术约束（V4.0 更新）
约束项	V4.0 选型	变更说明
平台底座	MLflow 3.x（开源版）	新增，替代自研 Django 平台层
评测引擎	DeepEval 3.x（作为 MLflow Scorer）	指标通过 mlflow.genai.scorers.deepeval 导入
Agent 采集层	自研 SSE Client（httpx + SSE 解析）	保留，V3.0 设计复用
任务调度	Celery + Redis 或 MLflow 自带调度	可保留 Celery 或迁移至 MLflow
数据库	PostgreSQL 15（含 Trace 存储）	MLflow 支持 PG 作为 Tracking 后端
前端界面	MLflow UI（主） + Vue 3 插件（业务扩展）	替代纯自研 Vue 3
Trace 协议	MLflow Tracing（原生支持 OpenTelemetry）	替代自研 Trace 存储
裁判模型	OpenAI 兼容（GPT-4o / Qwen / DeepSeek）	DeepEval + MLflow 均支持
认证方式	企业 SSO（LDAP/OIDC）	MLflow 支持，可集成
二、产品架构（V4.0 重构）
2.1 整体架构图
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    业务扩展层（自研 Vue 3 插件）                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Agent管理 │ │ 数据集管理│ │BadCase回流│ │ 报告定制 │ │ 权限管理 │         │
│  │ (SSE配置) │ │ (上传/标注)│ │ (闭环工作流)│ │ (业务看板)│ │ (RBAC)  │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────────────────────────────────┤
│                    MLflow 平台层（开箱即用）                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │  MLflow      │ │  MLflow      │ │  MLflow      │ │  MLflow      │     │
│  │  Tracking    │ │  UI (原生)   │ │  Tracing     │ │  Model       │     │
│  │  (实验管理)  │ │  (可视化)    │ │  (OTel集成)  │ │  Registry    │     │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                       │
│  │  MLflow      │ │  MLflow      │ │  MLflow      │                       │
│  │  Evaluate    │ │  (Scorer)    │ │  (Human      │                       │
│  │  (评测执行)  │ │  DeepEval    │ │  Feedback)   │                       │
│  └──────────────┘ └──────────────┘ └──────────────┘                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                    自研采集层（保留）                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SSEAgentCollector（httpx + SSE 解析 + 流式聚合）                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        基础设施层 Infrastructure                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │PostgreSQL│ │  S3/OSS  │ │  Redis   │ │ DeepEval │ │ MLflow   │         │
│  │ (追踪存储)│ │ (数据集) │ │ (缓存)   │ │ 指标库   │ │ 服务     │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
2.2 核心数据流向（V4.0）
text
        ┌──────────┐
        │ 黄金数据集 │
        │ (MLflow   │
        │  Dataset) │
        └────┬─────┘
             │ samples: {input, expected_output, context, ...}
             ▼
   ┌───────────────────┐   HTTP POST + SSE
   │ ① 采集层（自研）  │ ──────────────────►  被测 Agent
   │ SSEAgentCollector │ ◄──────────────────  https://.../chat/simple
   │ (httpx + SSE)     │   SSE chunks → 聚合文本
   └─────────┬─────────┘
             │ eval_dataset = [{input, actual_output, expected_output, ...}]
             ▼
   ┌──────────────────────────────────────────────┐
   │ ② 评测层（MLflow + DeepEval）                │
   │ mlflow.genai.evaluate(                       │
   │   data=eval_dataset,                         │
   │   scorers=[                                  │
   │     AnswerRelevancy(),   # DeepEval 指标    │
   │     Faithfulness(),      # DeepEval 指标    │
   │     CustomScorer(),      # 业务7维度 自研   │
   │   ]                                          │
   │ )                                            │
   └─────────┬────────────────────────────────────┘
             │ results + traces
             ▼
   ┌──────────────────────────────────────────────┐
   │ ③ 展示层（MLflow UI + Vue 插件）            │
   │ - MLflow UI: 实验对比 / Trace回放 / 评分详情 │
   │ - Vue 插件: Agent配置 / 数据集管理 / BadCase │
   └──────────────────────────────────────────────┘
2.3 核心模块职责（V4.0 更新）
模块	职责	实现方式
Agent 管理	配置 Agent HTTP/SSE 端点，屏蔽接口差异	自研 Vue 插件 + Django API
数据集管理	数据集创建、上传、版本管理、人工标注	MLflow Dataset + 自研标注工作台
SSE 采集层	调用 Agent 接口，聚合 SSE 流式响应	自研 SSEAgentCollector（复用 V3.0）
评测执行	编排评测流程，调用 MLflow Evaluate API	mlflow.genai.evaluate()
指标引擎	DeepEval 50+ 指标 + 自定义 G-Eval	MLflow Scorer（DeepEval + 自定义）
实验追踪	记录每次评测的配置、参数、结果	MLflow Tracking（原生）
Trace 回放	录制 Agent 完整交互轨迹，步骤级回放	MLflow Tracing（原生）
可视化 UI	评测结果可视化、版本对比、趋势分析	MLflow UI（原生）+ Vue 插件扩展
人工反馈	标注员对评测结果进行人工评分/校准	MLflow Human Feedback（原生）
BadCase 回流	低分样本自动回流入数据集	自研 Vue 插件 + API
三、数据库设计（V4.0 更新）
3.1 关键变更说明
MLflow 管理自己的 Tracking 表：MLflow 自动创建 experiments、runs、metrics、params、tags 等表

Trace 由 MLflow Tracing 管理：无需自建 traces 表，MLflow 原生支持 OpenTelemetry

保留业务核心表：agent_endpoints、datasets、dataset_samples、badcase_feedbacks 仍由 Django 管理

关联方式：业务表通过 mlflow_run_id 字段关联 MLflow 的 Run

3.2 核心表结构
3.2.1 Agent 端点表 agent_endpoints（不变，复用 V3.0）
字段	类型	说明
id	UUID	主键
name	VARCHAR(100)	Agent 名称
endpoint_url	VARCHAR(500)	接口地址
protocol	VARCHAR(20)	协议类型（http_sse / http_json）
method	VARCHAR(10)	HTTP 方法
headers	JSONB	请求头模板
body_template	JSONB	请求体模板
stream	BOOLEAN	是否流式
sse_event_field	VARCHAR(50)	SSE 内容字段路径
sse_done_marker	VARCHAR(50)	SSE 结束标记
default_user_id	VARCHAR(100)	默认 userId
default_conv_id	VARCHAR(100)	默认 convId
timeout	INTEGER	超时（秒）
retry_times	INTEGER	重试次数
status	VARCHAR(20)	状态
created_at	DATETIME	创建时间
updated_at	DATETIME	更新时间
3.2.2 数据集表 datasets（保留，MLflow Dataset 作为补充）
字段	类型	说明
id	UUID	主键
name	VARCHAR(100)	数据集名称
data_type	VARCHAR(20)	数据类型（qa / e2e / regression）
version	VARCHAR(20)	版本号
file_path	VARCHAR(500)	存储路径（S3）
sample_count	INTEGER	样本总数
tags	JSONB	标签列表
mlflow_dataset_uri	VARCHAR(500)	MLflow Dataset URI（关联）
status	VARCHAR(20)	状态
created_at	DATETIME	创建时间
updated_at	DATETIME	更新时间
3.2.3 数据集样本表 dataset_samples（不变，复用 V3.0）
字段	类型	说明
id	UUID	主键
dataset_id	UUID FK	外键→datasets
sample_id	VARCHAR(50)	样本编号
input	TEXT	输入
expected_output	TEXT	期望输出
context	JSONB	上下文
retrieval_context	JSONB	检索上下文
tags	JSONB	场景/难度标签
notes	TEXT	标注备注
created_at	DATETIME	创建时间
3.2.4 评测任务表 evaluation_tasks（简化，关联 MLflow Run）
字段	类型	说明
id	UUID	主键
name	VARCHAR(100)	任务名称
agent_id	UUID FK	外键→agent_endpoints
dataset_id	UUID FK	外键→datasets
mlflow_experiment_id	VARCHAR(50)	MLflow 实验 ID
mlflow_run_id	VARCHAR(50)	MLflow Run ID（核心关联）
judge_model	JSONB	裁判模型配置
evaluator_config	JSONB	评估器配置（指标列表）
parallel	INTEGER	并发数
limit	INTEGER	样本限制
status	VARCHAR(20)	状态
started_at	DATETIME	开始时间
completed_at	DATETIME	完成时间
created_by	UUID	创建人 ID
created_at	DATETIME	创建时间
3.2.5 BadCase 回流表 badcase_feedbacks（不变，复用 V3.0）
字段	类型	说明
id	UUID	主键
result_id	UUID FK	外键→evaluation_results（或 MLflow Run 关联）
dataset_id	UUID	目标数据集
status	VARCHAR(20)	状态
reviewer_id	UUID	标注员 ID
review_comment	TEXT	复核意见
created_at	DATETIME	创建时间
resolved_at	DATETIME	解决时间
注意：V4.0 中 evaluation_results 表可由 MLflow Tracking 替代，业务表只需存储 mlflow_run_id 关联即可。若需快速查询，可保留冗余结果表。

3.2.6 MLflow 自动创建的表（无需自研）
表名	说明
experiments	实验元数据（名称、标签、生命周期）
runs	每次评测执行（Run ID、状态、起止时间）
metrics	每个样本的指标分数（key=指标名，value=分数，step=样本索引）
params	评测参数（judge_model、evaluator_config 等）
tags	标签（agent_id、dataset_id、task_id 等，用于关联）
traces	OpenTelemetry Trace 数据（由 MLflow Tracing 管理）
四、API 接口设计（V4.0 更新）
4.1 接口规范（不变）
规范项	说明
基础路径	/api/v1/
认证方式	JWT Token（Bearer）
请求格式	application/json
响应格式	{"code": 0, "data": {...}, "message": "success"}
4.2 Agent 端点管理接口（不变，复用 V3.0）
方法	路径	说明
POST	/agents/	创建 Agent 端点配置
GET	/agents/	获取 Agent 列表
GET	/agents/{id}/	获取 Agent 详情
PUT	/agents/{id}/	更新 Agent
DELETE	/agents/{id}/	删除 Agent
POST	/agents/{id}/test/	连通性测试
4.3 数据集管理接口（简化）
方法	路径	说明
POST	/datasets/upload/	上传数据集
GET	/datasets/	获取数据集列表
GET	/datasets/{id}/samples/	获取样本列表
PUT	/datasets/{id}/samples/{sample_id}/	更新样本标注
POST	/datasets/{id}/to_mlflow/	将数据集同步为 MLflow Dataset
4.4 评测任务接口（V4.0 核心变更）
方法	路径	说明
POST	/tasks/	创建并触发评测任务（调用 MLflow Evaluate）
GET	/tasks/	获取任务列表
GET	/tasks/{id}/	获取任务详情（含 MLflow Run ID）
GET	/tasks/{id}/progress/	获取实时进度
POST	/tasks/{id}/stop/	停止任务
GET	/tasks/{id}/mlflow_url/	获取 MLflow UI 链接（直接跳转查看详情）
POST	/tasks/{id}/badcases/export/	导出 BadCase
POST	/tasks/{id}/badcases/feedback/	BadCase 回流入数据集
创建任务请求体示例（V4.0 更新）：

json
{
  "name": "2026Q2-知识助手回归测试",
  "agent_id": "uuid-agent-001",
  "dataset_id": "uuid-dataset-001",
  "judge_model": {
    "model": "gpt-4o",
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx"
  },
  "evaluator_config": {
    "metrics": [
      {"name": "answer_relevancy", "type": "deepeval", "threshold": 0.7},
      {"name": "faithfulness", "type": "deepeval", "threshold": 0.7},
      {"name": "consistency", "type": "custom_g_eval", "criteria": "回答是否保持上下文连贯", "threshold": 0.6},
      {"name": "truthfulness", "type": "custom_g_eval", "criteria": "回答事实是否正确", "threshold": 0.6},
      {"name": "f1", "type": "rule", "threshold": 0.6}
    ],
    "badcase_threshold": 0.6
  },
  "parallel": 10,
  "limit": 500
}
任务响应示例（V4.0 更新）：

json
{
  "code": 0,
  "data": {
    "task_id": "uuid",
    "name": "2026Q2-知识助手回归测试",
    "status": "running",
    "mlflow_run_id": "abc123def456",
    "mlflow_ui_url": "http://mlflow-server:5000/#/experiments/123/runs/abc123def456",
    "progress": 65,
    "processed": 325,
    "total": 500
  },
  "message": "success"
}
4.5 报告与对比接口（简化为 MLflow 对接）
方法	路径	说明
GET	/tasks/{id}/report/	获取业务报告数据（聚合 MLflow 指标 + 业务上下文）
GET	/tasks/{id}/mlflow/	重定向到 MLflow UI 对应页面
POST	/comparison/	多任务对比（调用 MLflow 对比能力）
4.6 Trace 查询接口（由 MLflow Tracing 原生提供）
V4.0 中 Trace 功能由 MLflow Tracing 原生支持，可直接使用 MLflow UI 查看，或通过 MLflow API 获取：

python
import mlflow

client = mlflow.tracing.MlflowClient()
trace = client.get_trace(run_id="abc123def456", sample_index=0)
业务层可封装为：

方法	路径	说明
GET	/tasks/{id}/trace/{sample_index}/	获取单条 Trace（代理 MLflow API）
五、前端页面设计（V4.0 重构）
5.1 设计策略：MLflow UI + Vue 3 插件
V4.0 采用混合 UI 策略，最大化复用 MLflow 开箱即用的能力，同时保留业务定制灵活性：

text
┌─────────────────────────────────────────────────────────────────┐
│  主导航                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │ 🤖 Agent │ 📁 数据集 │ 🚀 评测  │ 📈 MLflow│ ⚙️ 设置 │      │
│  │   管理    │   管理    │   任务    │   UI    │         │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  业务核心功能（Vue 3 插件）     │  MLflow UI（iframe / 新窗口） │
│  ┌─────────────────────────┐   │  ┌─────────────────────────┐  │
│  │ Agent 管理（SSE配置）    │   │  │ 实验对比面板            │  │
│  │ 数据集管理（上传/标注）  │   │  │ Trace 时间线回放        │  │
│  │ 评测任务创建与进度监控   │   │  │ 指标详情与分布图        │  │
│  │ BadCase 回流工作流       │   │  │ 人工反馈标注界面        │  │
│  │ 业务定制看板（7维度）    │   │  │ 参数/指标/标签筛选      │  │
│  └─────────────────────────┘   │  └─────────────────────────┘  │
│                                                                 │
│  点击任务 → 一键跳转 MLflow UI 查看完整 Trace 和评测详情        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
5.2 页面导航结构（V4.0 更新）
text
📊 总览看板（Vue 插件）
    ├── 近期评测任务列表（状态 + MLflow UI 跳转链接）
    ├── Agent 健康度概览
    └── BadCase 趋势统计

🤖 Agent 管理（Vue 插件，不变）
    ├── Agent 卡片列表
    ├── 创建 Agent（SSE 端点配置表单）
    └── 连通性测试

📁 数据集管理（Vue 插件 + MLflow Dataset 同步）
    ├── 数据集列表
    ├── 上传数据集（拖拽上传 JSONL）
    ├── 数据集详情 → 样本预览
    ├── 标注工作台
    └── 同步到 MLflow Dataset

🚀 评测任务（Vue 插件 + MLflow API）
    ├── 创建任务（三步向导：选 Agent → 选数据集 → 配置评估器）
    ├── 任务列表（卡片视图 + 状态 + MLflow 链接）
    └── 任务详情（业务摘要 + "查看完整报告" → 跳转 MLflow UI）

📈 MLflow UI（原生，新窗口/iframe 嵌入）
    ├── 实验管理（所有评测任务自动记录为 Experiments）
    ├── Run 详情（指标分布、参数、标签）
    ├── 版本对比（多 Run 并排对比）
    ├── Trace 回放（OpenTelemetry 时间线）
    ├── 人工反馈（Human Feedback 标注界面）
    └── 模型注册（可选）

⚙️ 系统设置（Vue 插件）
    ├── 裁判模型配置
    ├── 评估指标库（DeepEval 指标 + 自定义 G-Eval）
    ├── 用户权限管理
    └── MLflow 连接配置
5.3 关键页面设计
5.3.1 评测任务创建（Vue 插件，三步向导）
与 V3.0 基本一致，第三步"配置评估器"的指标来源扩展为：

text
┌──────────────────────────────────────────────────────────────┐
│ Step 3 - 配置评估器                                          │
├──────────────────────────────────────────────────────────────┤
│ 📦 DeepEval 内置指标（通过 MLflow Scorer 导入，50+）        │
│   ☑ 答案相关性 AnswerRelevancy    阈值 [0.7]               │
│   ☑ 忠实性     Faithfulness       阈值 [0.7]               │
│   ☐ 上下文精确率 ContextualPrecision                        │
│   ... 展开更多 ▼                                            │
├──────────────────────────────────────────────────────────────┤
│ 🎯 自定义 G-Eval 指标（业务 7 维度 + 自定义）              │
│   ☑ 一致性   ☑ 真实性   ☑ 稳定性   ☑ 有效性               │
│   ☑ 对抗性   ☑ 安全性   ☑ 鲁棒性                          │
│   [+ 添加自定义维度]                                        │
├──────────────────────────────────────────────────────────────┤
│ 📊 传统 ML 指标（规则类，零裁判成本）                       │
│   ☑ F1 Score   ☑ Exact Match   ☑ ROUGE-L                  │
├──────────────────────────────────────────────────────────────┤
│ ⚖️ 裁判模型: [GPT-4o ▼]  并发: [10]  BadCase阈值: [0.6]    │
│                              [上一步]  [开始评测]            │
└──────────────────────────────────────────────────────────────┘
5.3.2 任务列表（Vue 插件）
text
┌──────────────────────────────────────────────────────────────────────┐
│  🚀 评测任务                            [+ 创建任务]                │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 2026Q2-知识助手回归测试                    状态: 已完成 ✅     │ │
│  │ Agent: 企业知识助手-v2  数据集: 黄金集-v3  样本: 500/500      │ │
│  │ 综合得分: 0.84  BadCase: 23  耗时: 12min                      │ │
│  │ [查看报告] [MLflow详情 ↗] [导出BadCase]                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 2026Q2-对抗性专项测试                       状态: 执行中 🔵    │ │
│  │ Agent: 企业知识助手-v2  数据集: 对抗集-v1  样本: 187/300      │ │
│  │ 进度: ████████████████░░░░░░░░  62%                          │ │
│  │ [查看实时] [MLflow详情 ↗]                                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
5.3.3 MLflow UI 嵌入（原生能力）
点击任务卡片上的 [MLflow详情 ↗]，将打开 MLflow UI 的对应页面：

MLflow UI 提供的能力（无需自研）：

功能	MLflow UI 页面	说明
实验列表	/experiments	所有评测任务自动记录
Run 详情	/experiments/{id}/runs/{run_id}	指标曲线、参数、标签、模型
指标对比	多 Run 对比视图	并排对比多个评测任务
Trace 回放	Tracing UI	OpenTelemetry 时间线，完整步骤回放
人工反馈	Human Feedback UI	标注员对样本进行人工评分
图表可视化	Metrics Plot	指标分布、散点图、趋势图
MLflow Run 详情页示例（原生 UI）：

text
┌──────────────────────────────────────────────────────────────────────┐
│  Run: 2026Q2-知识助手回归测试  [实验: 评测任务]  [状态: 已完成]    │
├──────────────────────────────────────────────────────────────────────┤
│  参数 (Params)                          │  指标 (Metrics)          │
│  ├─ agent_id: uuid-agent-001           │  ├─ answer_relevancy: 0.85│
│  ├─ dataset_id: uuid-dataset-001       │  ├─ faithfulness: 0.92   │
│  ├─ judge_model: gpt-4o                │  ├─ consistency: 0.94    │
│  ├─ badcase_threshold: 0.6             │  ├─ truthfulness: 0.90   │
│  └─ parallel: 10                       │  ├─ f1: 0.71             │
│                                         │  └─ overall: 0.84        │
├──────────────────────────────────────────────────────────────────────┤
│  指标趋势图 (Metrics Plot)                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  1.00 ──────────────────────⋯⋯                              │   │
│  │  0.80 ────────╱╲─────────╱╲─⋯                              │   │
│  │  0.60 ───────────╲╱─────╱───⋯                              │   │
│  │  0.40 ────────────────────────────────────                  │   │
│  │      0   50  100  150  200  250  300  350  400  450  500   │   │
│  └──────────────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│  Trace 回放 (Tracing)                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ⏱ 样本 #002  总耗时 6.9s  Tokens 757                       │   │
│  │  ├─ agent.collect (HTTP/SSE)              [1.8s]  ✅        │   │
│  │  ├─ judge.eval (AnswerRelevancy)          [0.8s]  0.85     │   │
│  │  ├─ judge.eval (Faithfulness)             [0.9s]  0.92     │   │
│  │  └─ judge.eval (Consistency)              [1.2s]  0.94     │   │
│  └──────────────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│  人工反馈 (Human Feedback)    [标注入口]                           │
│  待标注样本: 23  已标注: 0  [开始标注]                             │
└──────────────────────────────────────────────────────────────────────┘
5.4 Vue 插件 vs MLflow UI 分工矩阵
功能	Vue 插件（自研）	MLflow UI（原生）	说明
Agent 管理（SSE 配置）	✅	❌	业务特有，需自研
数据集管理（上传/标注）	✅	❌	业务特有，需自研
评测任务创建（三步向导）	✅	❌	业务编排，需自研
任务列表与进度监控	✅	❌	业务聚合，需自研
BadCase 回流工作流	✅	❌	业务闭环，需自研
业务 7 维度定制看板	✅	❌	业务指标，需自研
实验结果查看	❌	✅	MLflow UI 开箱即用
版本对比	❌	✅	MLflow 原生能力
Trace 回放	❌	✅	MLflow Tracing 原生
指标图表	❌	✅	MLflow 原生可视化
人工反馈标注	❌	✅	MLflow Human Feedback 原生
参数/标签筛选	❌	✅	MLflow UI 原生
模型注册	❌	✅	MLflow Model Registry 原生
5.5 视觉与配色规范（不变，复用 V3.1）
平台仍采用深色主题 + 紫粉渐变主色，MLflow UI 部分可通过 CSS 覆盖适配企业品牌色。

MLflow UI 品牌化建议：

MLflow 开源版支持自定义 CSS 和 Logo，可通过以下方式统一品牌视觉：

bash
# MLflow 启动时指定自定义 CSS
mlflow ui --static-prefix /mlflow --app-name "Agent评测平台" \
          --custom-css /path/to/custom.css
自定义 CSS 可覆盖 MLflow UI 的主色为紫粉渐变，与 Vue 插件保持一致。

六、后端关键实现（V4.0 更新）
6.1 技术选型（V4.0 更新）
组件	V4.0 选型	说明
平台底座	MLflow 3.x（开源版）	新增，提供追踪/UI/Trace/人工反馈
评测引擎	DeepEval 3.x（作为 MLflow Scorer）	50+ 指标通过 mlflow.genai.scorers.deepeval 导入
Agent 采集层	自研（httpx + SSE 解析）	保留，复用 V3.0 设计
Web 框架	Django 4.2 + DRF	业务 API，轻量化
任务调度	Celery 5.x + Redis	评测任务编排
数据库	PostgreSQL 15	业务表 + MLflow Tracking 后端
文件存储	阿里云 OSS / AWS S3	数据集和报告存储
裁判模型	OpenAI 兼容端点	DeepEval + MLflow 均支持
认证	Django OIDC / LDAP + MLflow 代理	统一 SSO
6.2 核心代码实现
6.2.1 SSE 采集层（保留，复用 V3.0）
SSEAgentCollector 代码与 V3.0 完全一致，无需变更。采集层输出格式：

python
# 采集结果示例
collect_result = {
    "output": "公司A的核心业务包括云计算、人工智能...",
    "chunks": [{"content": "公司A"}, {"content": "的核心业务"}],
    "latency_ms": 1834,
    "error": None
}
6.2.2 MLflow + DeepEval 评测执行（V4.0 核心）
python
# evaluation/mlflow_evaluator.py
import mlflow
from mlflow.genai.scorers.deepeval import AnswerRelevancy, Faithfulness
from mlflow.models import EvaluationDataset
from evaluation.collectors.sse_agent_collector import SSEAgentCollector
from evaluation.custom_scorers import ConsistencyScorer, TruthfulnessScorer, F1Scorer
from django.conf import settings


class MLflowEvaluator:
    """
    使用 MLflow + DeepEval 执行评测。
    采集层（SSEAgentCollector）负责调用 Agent，MLflow 负责打分和追踪。
    """

    def __init__(self, task, agent_config, dataset_samples, evaluator_config, judge_model):
        self.task = task
        self.agent_config = agent_config
        self.samples = dataset_samples
        self.evaluator_config = evaluator_config
        self.judge_model = judge_model
        self.collector = SSEAgentCollector(agent_config)

    def run(self):
        # ① 采集层：调用 Agent 获取实际输出
        eval_data = []
        for sample in self.samples:
            result = self.collector.collect(sample.input, sample.sample_vars())
            eval_data.append({
                "input": sample.input,
                "output": result["output"],           # actual_output
                "expected_output": sample.expected_output,
                "context": sample.context,
                "retrieval_context": sample.retrieval_context,
                "_latency_ms": result["latency_ms"],
                "_sample_id": sample.sample_id,
            })

        # ② 构建 MLflow 评估数据集
        dataset = EvaluationDataset(
            data=eval_data,
            predictions="output",  # 指定哪个字段为模型输出
            targets="expected_output",  # 指定哪个字段为期望输出
        )

        # ③ 构建 Scorer 列表（DeepEval 内置 + 自定义）
        scorers = self._build_scorers()

        # ④ 启动 MLflow Run 并执行评测
        with mlflow.start_run(
            experiment_id=self.task.mlflow_experiment_id,
            run_name=self.task.name,
            tags={
                "task_id": str(self.task.id),
                "agent_id": str(self.task.agent_id),
                "dataset_id": str(self.task.dataset_id),
                "type": "agent_evaluation"
            }
        ) as run:
            # 记录参数
            mlflow.log_params({
                "judge_model": self.judge_model["model"],
                "badcase_threshold": self.evaluator_config["badcase_threshold"],
                "parallel": self.task.parallel,
                "sample_count": len(eval_data),
            })

            # 执行评估（核心调用）
            results = mlflow.genai.evaluate(
                data=dataset,
                scorers=scorers,
                predictions="output",
                targets="expected_output",
                # 每个样本的额外上下文
                extra_metrics=[
                    mlflow.metrics.latency(),  # 自动记录延迟
                ]
            )

            # 记录 task_id 关联
            mlflow.log_param("task_id", str(self.task.id))
            mlflow.log_param("mlflow_run_id", run.info.run_id)

            # 存储 run_id 到业务表
            self.task.mlflow_run_id = run.info.run_id
            self.task.status = "completed"
            self.task.save()

            return {
                "run_id": run.info.run_id,
                "experiment_id": run.info.experiment_id,
                "results": results,
            }

    def _build_scorers(self):
        """构建 Scorer 列表：DeepEval 内置 + 自定义 G-Eval + 规则指标"""
        scorers = []

        for m_cfg in self.evaluator_config["metrics"]:
            name = m_cfg["name"]
            threshold = m_cfg.get("threshold", 0.6)

            if m_cfg["type"] == "deepeval":
                # DeepEval 内置指标，通过 mlflow.genai.scorers.deepeval 导入
                scorer_class = self._get_deepeval_scorer(name)
                scorers.append(
                    scorer_class(
                        threshold=threshold,
                        model=self.judge_model["model"],
                        # MLflow 自动传递 OpenAI 兼容配置
                    )
                )

            elif m_cfg["type"] == "custom_g_eval":
                # 自定义 G-Eval（业务 7 维度），封装为 MLflow Scorer
                scorers.append(
                    CustomGEvalScorer(
                        name=name,
                        criteria=m_cfg["criteria"],
                        threshold=threshold,
                        model=self.judge_model["model"],
                    )
                )

            elif m_cfg["type"] == "rule":
                # 传统 ML 指标（F1/ROUGE），封装为 MLflow Scorer
                scorers.append(
                    RuleMetricScorer(
                        name=name,
                        metric_type=m_cfg.get("rule_class", name),
                        threshold=threshold,
                    )
                )

        return scorers

    @staticmethod
    def _get_deepeval_scorer(name):
        """映射 DeepEval 指标名称到 MLflow Scorer 类"""
        from mlflow.genai.scorers.deepeval import (
            AnswerRelevancy, Faithfulness, ContextualPrecision,
            ContextualRecall, Hallucination, Bias, Toxicity,
            # ... 50+ 指标
        )
        mapping = {
            "answer_relevancy": AnswerRelevancy,
            "faithfulness": Faithfulness,
            "contextual_precision": ContextualPrecision,
            "contextual_recall": ContextualRecall,
            "hallucination": Hallucination,
            "bias": Bias,
            "toxicity": Toxicity,
            # ... 更多映射
        }
        return mapping.get(name)
6.2.3 自定义 MLflow Scorer（业务 7 维度）
python
# evaluation/custom_scorers.py
import mlflow
from mlflow.models import EvaluationMetric
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams


class CustomGEvalScorer:
    """
    自定义 G-Eval Scorer，封装 DeepEval 的 GEval 为 MLflow Scorer 格式。
    用于业务 7 维度：一致性/真实性/稳定性/有效性/对抗性/安全性/鲁棒性。
    """

    def __init__(self, name: str, criteria: str, threshold: float, model: str):
        self.name = name
        self.criteria = criteria
        self.threshold = threshold
        self.model = model

    def __call__(self, eval_df, builtin_metrics):
        """
        MLflow Scorer 接口：
        接收 eval_df（包含 predictions, targets, inputs 等列），返回评分结果。
        """
        from evaluation.judge_model import get_judge_endpoint

        judge = get_judge_endpoint({"model": self.model, "api_base": self.model_config["api_base"]})
        g_eval = GEval(
            name=self.name,
            criteria=self.criteria,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            threshold=self.threshold,
            model=judge,
            strict_mode=False,
        )

        scores = []
        for _, row in eval_df.iterrows():
            tc = LLMTestCase(
                input=row["input"],
                actual_output=row["output"],
                expected_output=row["expected_output"] if "expected_output" in row else None,
            )
            score = g_eval.measure(tc)
            scores.append(score)

        # 返回 MLflow EvaluationMetric 格式
        return EvaluationMetric(
            name=self.name,
            scores=scores,
            thresholds=[self.threshold] * len(scores),
        )


class RuleMetricScorer:
    """
    传统 ML 指标 Scorer：F1 / Exact Match / ROUGE-L，零裁判成本。
    封装为 MLflow Scorer 格式。
    """

    def __init__(self, name: str, metric_type: str, threshold: float):
        self.name = name
        self.metric_type = metric_type
        self.threshold = threshold

    def __call__(self, eval_df, builtin_metrics):
        from evaluation.metrics.rule_metrics import F1Metric, ExactMatchMetric, RougeLMetric

        metric_map = {
            "f1": F1Metric,
            "exact_match": ExactMatchMetric,
            "rouge_l": RougeLMetric,
        }
        metric_cls = metric_map.get(self.metric_type)
        metric = metric_cls(threshold=self.threshold)

        scores = []
        for _, row in eval_df.iterrows():
            tc = LLMTestCase(
                actual_output=row["output"],
                expected_output=row["expected_output"] if "expected_output" in row else "",
            )
            score = metric.measure(tc)
            scores.append(score)

        return EvaluationMetric(
            name=self.name,
            scores=scores,
            thresholds=[self.threshold] * len(scores),
        )
6.2.4 Celery 任务调度（调用 MLflow）
python
# evaluation/tasks.py
from celery import shared_task
from evaluation.mlflow_evaluator import MLflowEvaluator
from models import EvaluationTask


@shared_task(bind=True)
def run_evaluation_task(self, task_id: str):
    task = EvaluationTask.objects.get(id=task_id)
    task.status = "running"
    task.save()

    # ① 获取配置
    agent = task.agent
    samples = task.dataset.samples.all()[:task.limit] if task.limit else task.dataset.samples.all()
    agent_config = agent.to_dict()
    evaluator_config = task.evaluator_config
    judge_model = task.judge_model

    # ② 创建 MLflow 实验（如果不存在）
    import mlflow
    experiment = mlflow.get_experiment_by_name("agent_evaluation")
    if not experiment:
        experiment_id = mlflow.create_experiment(
            "agent_evaluation",
            tags={"type": "agent_evaluation", "team": "AI"}
        )
    else:
        experiment_id = experiment.experiment_id
    task.mlflow_experiment_id = experiment_id
    task.save()

    # ③ 执行评测
    evaluator = MLflowEvaluator(
        task=task,
        agent_config=agent_config,
        dataset_samples=samples,
        evaluator_config=evaluator_config,
        judge_model=judge_model,
    )

    try:
        result = evaluator.run()
        task.status = "completed"
        task.save()
        return result
    except Exception as e:
        task.status = "failed"
        task.save()
        raise
6.2.5 MLflow 服务部署
bash
# Docker Compose 部署 MLflow + PostgreSQL
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mlflow
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: mlflow
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mlflow:
    image: mlflow:3.0
    command: >
      mlflow server
      --backend-store-uri postgresql://mlflow:mlflow@postgres/mlflow
      --default-artifact-root s3://mlflow-artifacts/
      --host 0.0.0.0
      --port 5000
      --app-name "Agent评测平台"
    ports:
      - "5000:5000"
    depends_on:
      - postgres
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
6.3 安全措施（V4.0 新增）
安全项	V4.0 实现方式
API Key 加密	使用 Fernet 对称加密存储；MLflow 通过环境变量传递
权限控制	Django RBAC + MLflow 权限代理（MLflow 支持 Basic Auth）
数据隔离	被测 Agent 与 MLflow 服务网络隔离，仅 Django 可访问
审计日志	所有操作记录到 AuditLog 表
SSO 集成	Django OIDC 认证，MLflow 配置反向代理透传用户身份
MLflow 访问控制	部署 MLflow 网关层，限制仅内网/经过认证的访问
七、实施路径（V4.0 更新）
7.1 阶段 0：技术 Spike（1 周）
在动工前验证 MLflow + DeepEval 集成的可行性。

任务	验收标准
① 部署 MLflow 服务（本地 Docker）	mlflow ui 可访问
② 跑通 MLflow + DeepEval 集成示例	mlflow.genai.evaluate() + DeepEval Scorer 对 mock 数据出分
③ 采集层原型验证	SSEAgentCollector 对真实接口跑通
④ 端到端联调	用 5-10 条样本：采集→MLflow 评测→MLflow UI 查看结果
⑤ MLflow UI 品牌化验证	确认可覆盖自定义 CSS，统一紫粉主题
Spike 输出一份"混合方案集成可行性确认书"。

7.2 第一阶段（MVP）—— 跑通核心流程（3-4 周）
周次	前端（Vue 插件）	后端（Django + MLflow）	核心依赖
W1	Agent 管理（SSE 配置）+ 数据集管理（列表+上传）	Agent CRUD + 数据集 CRUD + MLflow 实验初始化	MLflow 部署
W2	创建评测任务（三步向导）+ 任务列表	评测任务 API + Celery 调度 + MLflow Evaluate 集成	DeepEval Scorer
W3	任务详情页 + MLflow UI 跳转集成	任务状态聚合 + MLflow Run 关联 + BadCase 导出	MLflow API
W4	BadCase 回流工作流 + 基础总览看板	BadCase 回流 API + 报告聚合 API	
MVP 交付标准：

✅ 接入被测 SSE Agent（SSEAgentCollector 跑通）

✅ 上传 JSONL 数据集并同步到 MLflow Dataset

✅ 创建评测任务（DeepEval 内置指标 + 自定义 G-Eval）

✅ 任务完成后自动跳转 MLflow UI 查看完整报告

✅ MLflow UI 查看 Trace 回放

✅ BadCase 手动回流入数据集

✅ 基础总览看板展示近期任务

7.3 第二阶段（进阶）—— 能力增强（3-4 周）
交付内容	说明
MLflow 对比分析	利用 MLflow UI 原生对比多 Run
人工反馈标注闭环	使用 MLflow Human Feedback，标注员对低分样本复核
报告高级导出	从 MLflow API 拉取数据生成 PDF 报告
定时任务	使用 MLflow Scheduled Runs 或 Celery Beat
CI/CD 集成	Webhook 触发评测，MLflow 自动记录
数据集标注工作台	Vue 插件，标注员协同
BadCase 自动回流	低分样本自动回流入数据集
7.4 第三阶段（完善）—— 企业级能力（3-4 周）
交付内容	说明
SSO 集成	Django OIDC + MLflow 反向代理认证
RBAC 权限管理	Django 权限 + MLflow 权限代理
MLflow UI 品牌化	自定义 CSS 统一紫粉深色主题
可观测性	集成 LangSmith / OpenTelemetry，MLflow Tracing 增强
开放 API	完整 RESTful API，对接企业工具链
性能压测	Agent 服务性能基准测试，MLflow 记录
多轮对话评测	MLflow 支持多轮对话数据集
八、核心收益总结
8.1 开发效率对比
维度	V3.0（纯自研）	V4.0（混合方案）	节约
前端开发量	6-8 周	2-3 周（仅插件）	~60%
后端开发量	6-8 周	3-4 周	~50%
Trace 实现	自建 PG JSONB	MLflow 原生	100%
版本对比实现	自建	MLflow 原生	100%
人工反馈实现	自建	MLflow 原生	100%
UI 图表开发	自建 ECharts	MLflow 原生	80%
总 MVP 周期	6-10 周	3-4 周	~50%
8.2 能力覆盖对比
能力	V3.0（自研）	V4.0（混合方案）
DeepEval 50+ 指标	✅	✅
业务 7 维度 G-Eval	✅	✅
传统 ML 指标（F1/ROUGE）	✅	✅
SSE 采集层	✅	✅
实验追踪与版本管理	自建	✅ MLflow 原生（更强）
Trace 时间线回放	自建	✅ MLflow 原生（更强）
多任务并排对比	自建	✅ MLflow 原生
人工反馈标注	❌（未规划）	✅ MLflow 原生
模型注册与版本管理	❌	✅ MLflow 原生
CI/CD 集成	自建	✅ MLflow 原生
开源社区迭代	❌	✅ MLflow + DeepEval 双社区
8.3 关键决策确认
决策项	V4.0 决策	理由
平台底座	MLflow 开源版	避免重复造轮子，企业级能力开箱即用
评测引擎	DeepEval（作为 MLflow Scorer）	保留 50+ 指标优势，原生集成
采集层	自研 SSEAgentCollector（复用 V3.0）	Agent 接入的唯一方式，必须自研
前端策略	MLflow UI 主体 + Vue 插件扩展	最大化复用，仅开发业务特有功能
部署方式	私有化部署（Django + MLflow）	企业数据安全，MLflow 开源版可私有化
九、风险与应对（V4.0 更新）
风险	影响	概率	应对措施
MLflow + DeepEval 版本兼容性	集成失败	中	Spike 阶段验证，锁定版本组合
MLflow UI 定制化不足	品牌体验不一致	中	通过自定义 CSS + 前端路由集成解决
团队 MLflow 学习曲线	开发进度延期	中	提前学习 + Spike 阶段实战
SSE 接口字段结构未知	采集层解析失败	高	Spike 第一步用 curl 抓真实响应确认
LLM-as-Judge 评分不稳定	评测结果不可信	中高	多裁判投票 + 人工反馈校准
MLflow 服务运维复杂度	增加运维负担	中	容器化部署 + 云原生监控
采集层并发会话污染	评测数据失真	中	每样本独立 convId
9.1 风险缓解措施（V4.0 特有）
MLflow 服务高可用：

yaml
# 生产部署建议
mlflow:
  replicas: 2
  resources:
    requests:
      memory: "2Gi"
      cpu: "1"
  # PostgreSQL 作为 Tracking 后端，S3 作为 Artifact 存储
  # 可扩展至 HA 配置
MLflow UI 与 Vue 插件的无缝集成：

python
# Django 代理 MLflow UI，统一域名和认证
urlpatterns = [
    path('api/v1/', include('api.urls')),
    path('mlflow/', include('mlflow_proxy.urls')),  # 代理 MLflow UI
]
十、术语表（V4.0 更新）
术语	说明
MLflow	开源 MLOps 平台，提供实验追踪、模型注册、评测 UI、Tracing 等能力
MLflow Run	一次评测执行的完整记录，包含参数、指标、标签、Trace
MLflow Scorer	MLflow 的评估指标接口，DeepEval 指标通过此接口注入
DeepEval	开源 LLM 应用评测框架，50+ 指标，通过 MLflow Scorer 集成
G-Eval	DeepEval 的链式思维（chain-of-thought）评分指标
SSE 采集层	自研模块，调用被测 Agent HTTP/SSE 接口并聚合流式响应
Trace	Agent 一次完整请求的生命周期记录，由 MLflow Tracing 管理
BadCase	评测中得分低于阈值的样本，触发回流闭环
十一、附录
附录 A：MLflow + DeepEval 官方集成参考
资源	链接
MLflow DeepEval 集成文档	mlflow.org/docs/latest/genai/scorers/deepeval
MLflow 3.x 发布说明	mlflow.org/docs/latest/release-notes
DeepEval 指标列表	docs.deepeval.ai/metrics
MLflow Tracing 文档	mlflow.org/docs/latest/tracing
附录 B：依赖版本锁定建议
text
# requirements.txt
mlflow>=3.8.0,<4.0.0
deepeval>=3.0.0,<4.0.0
openai>=1.0.0
httpx>=0.27.0
django>=4.2
celery>=5.3.0
psycopg2-binary>=2.9.0
文档审批
角色	姓名	签字	日期
产品负责人			
技术负责人			
业务方代表			
V3.0 → V4.0 核心变更总结
变更项	V3.0	V4.0	收益
平台底座	自研 Django + Vue	MLflow 开源平台	实验追踪/UI/Trace/人工反馈开箱即用
前端策略	全自研 Vue 3	MLflow UI 主 + Vue 插件	前端工作量降低 60%
Trace 存储	自建 PG JSONB	MLflow Tracing	原生 OpenTelemetry 支持，无需自研
版本对比	自建	MLflow 原生对比	多 Run 并排对比开箱即用
人工反馈	未规划	MLflow Human Feedback	标注闭环能力原生支持
开发周期	6-10 周	3-4 周	交付周期缩短 50%
长期维护	高（自研）	低（社区迭代）	MLflow 社区持续更新