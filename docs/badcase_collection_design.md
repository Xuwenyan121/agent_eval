# BadCase 收集与回流模块 - 详细设计方案

> 版本：V1.0  
> 日期：2026-06-25  
> 状态：方案设计阶段（未实施代码）

---

## 一、方案概述

### 1.1 当前现状与差距分析

| 维度 | 当前已有能力 | 缺失能力 |
|------|-------------|---------|
| BadCase 判定 | `EvaluationResult.is_badcase` 基于 `overall_score < badcase_threshold` 单一规则 | 多维度收集规则（高分段抽查、随机抽样、分指标筛选） |
| BadCase 存储 | `BadCaseFeedback` 表关联 result → dataset | 收集规则配置存储、收集历史记录、批量操作审计 |
| BadCase 查看 | 无专门界面 | 任务结果中查看具体执行链路（Trace 回放）、过滤和排序 |
| BadCase 回流 | `BadCaseFeedback` 记录了 dataset 关联 | 一键/批量回流入数据集、作为新样本触发评测、版本追踪 |
| 数据集集成 | `Dataset` / `DatasetSample` 标准表结构 | BadCase 来源标记、回流后的样本溯源、与原数据集的关系 |
| Trace 关联 | `Trace` 表通过 task_id + sample_id 关联 | BadCase 详情页一键跳转 Trace 回放 |

### 1.2 设计目标

1. **灵活收集**：支持分数阈值、分指标阈值、高分抽查、随机抽样、错误样本收集等多种维度
2. **链路可见**：每个 BadCase 可查看完整的 Agent 交互 Trace（请求/SSE 流/响应/评分理由）
3. **无缝回流**：BadCase 可一键回流到数据集，作为新样本重新触发评测，形成迭代闭环
4. **生命周期管理**：BadCase 有完整的状态流转（待审核 → 已确认 → 已回流 → 已关闭）
5. **与现有架构兼容**：复用 `EvaluationResult`、`BadCaseFeedback`、`Dataset`、`DatasetSample` 模型，扩展而非重写

---

## 二、核心概念模型

### 2.1 实体关系图

```
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
│ EvaluationTask  │──1:N──│  EvaluationResult     │──1:N──│  BadCaseFeedback    │
│                 │       │  - overall_score      │       │  - status           │
│  - badcase_     │       │  - is_badcase         │       │  - collection_rule  │
│    threshold    │       │  - metric_results     │       │  - review_comment   │
│                 │       │  - trace_id           │       │  - source_task      │
└─────────────────┘       └───────────────────────┘       └─────────┬───────────┘
                                                                     │
                            ┌──────────────────────┐                 │
                            │  BadCaseCollection   │◄────────────────┘
                            │  Rule                │
                            │  - rule_type         │        ┌─────────────────────┐
                            │  - parameters        │──1:N──▶│  BadCaseCollection   │
                            │  - enabled           │        │  Record              │
                            └──────────────────────┘        │  - rules_applied     │
                                                            │  - sample_count      │
                                                            └─────────────────────┘
                                                                     │
                            ┌──────────────────────┐                 │
                            │  Dataset (target)    │◄────────────────┘
                            │  - is_badcase_set    │  回流后样本记录
                            │  - source_task_ids   │
                            └──────────────────────┘
                                    │
                            ┌───────┴───────────┐
                            │  DatasetSample    │
                            │  - source_type    │  ("golden" | "badcase")
                            │  - source_task_id │
                            │  - source_result_id│
                            │  - badcase_reason │
                            └───────────────────┘
```

### 2.2 核心流程

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ 评测任务  │───▶│ 生成评测结果  │───▶│ 收集规则匹配  │───▶│ BadCase 入库  │───▶│ 人工审核  │
│ 执行完成  │    │ EvaluationResult│   │ 多规则评估    │    │ BadCaseFeedback│   │ 确认/驳回  │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └────┬─────┘
                                                                                 │
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│ 迭代评测  │◄───│ 创建/更新     │◄───│ 回流到数据集  │◄───│ 批量确认回流  │◄────────┘
│ 新任务    │    │ 评测数据集    │    │ DatasetSample │    │              │
└──────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 三、收集规则引擎设计（核心）

### 3.1 收集维度定义

参考业界成熟实践（LangSmith Annotation Queues、MLflow Human Feedback、Arize AI Performance Tracing），定义以下收集维度：

| 规则类型 | rule_type | 说明 | 典型场景 |
|---------|-----------|------|---------|
| **分数阈值（低于）** | `score_below` | 综合分低于阈值 | 最常用：`overall_score < 0.6` |
| **分数阈值（高于）** | `score_above` | 综合分高于阈值 | 抽查高分样本是否真的优秀（防评分膨胀） |
| **分指标阈值** | `metric_below` | 某个指标低于阈值 | 专项收集：`truthfulness < 0.5` 的样本 |
| **分指标高于** | `metric_above` | 某个指标异常高 | 抽查某指标满分样本是否合理 |
| **边界样本** | `boundary` | 分数在阈值附近的样本 | `0.55 <= score <= 0.65`，关注临界样本 |
| **随机抽样** | `random` | 从结果中随机抽样 | 质量抽查，避免系统偏差 |
| **分层抽样** | `stratified` | 按分数段/标签分层抽样 | 按 difficulty 标签：easy/medium/hard 各抽 10% |
| **错误样本** | `error` | 采集/评测过程出错 | `error != ""` 的样本 |
| **高延迟样本** | `high_latency` | Agent 响应时间过长 | `latency_ms > 5000` |
| **低延迟样本** | `low_latency` | Agent 响应极快 | 疑似缓存命中或短接回答 |
| **评分分歧** | `score_variance` | 多个指标间评分差异大 | `max(metric_scores) - min(metric_scores) > 0.5` |
| **自定义条件** | `custom` | 组合条件表达式 | `faithfulness < 0.5 AND latency_ms > 3000` |

### 3.2 收集规则配置模型

```
BadCaseCollectionRule:
  id: UUID
  name: str                    # 规则名称，如"低分样本收集"
  description: str
  rule_type: str               # score_below | metric_below | random | stratified | ...
  parameters: JSONB            # 规则参数（详见下方）
  target_dataset_id: UUID?     # 目标数据集（可选，指定回流目标）
  auto_collect: bool           # 是否在任务完成后自动触发收集
  enabled: bool
  priority: int                # 多个规则命中时的优先级
  created_at / updated_at
```

#### 各 rule_type 的 parameters 定义：

```json
// score_below - 综合分低于阈值
{
  "threshold": 0.6,
  "inclusive": true            // true: <= threshold, false: < threshold
}

// score_above - 综合分高于阈值（抽查高分样本）
{
  "threshold": 0.9,
  "sample_rate": 0.2           // 在高分样本中随机抽取 20%
}

// metric_below - 分指标低于阈值
{
  "metric_name": "truthfulness",
  "threshold": 0.5,
  "inclusive": true
}

// boundary - 边界样本
{
  "lower": 0.55,
  "upper": 0.65
}

// random - 随机抽样
{
  "sample_rate": 0.1,          // 抽样比例 10%
  "max_count": 50              // 最多抽取 50 条
}

// stratified - 分层抽样
{
  "strategy": "by_score_band", // by_score_band | by_tag | by_metric
  "config": {
    "bands": [
      {"label": "low", "range": [0.0, 0.4], "sample_rate": 0.5},
      {"label": "mid", "range": [0.4, 0.7], "sample_rate": 0.2},
      {"label": "high", "range": [0.7, 1.0], "sample_rate": 0.05}
    ]
  }
}

// error - 错误样本
{
  "error_contains": null,      // null = 任意错误; "timeout" = 仅超时错误
  "max_count": 100
}

// high_latency
{
  "threshold_ms": 5000
}

// score_variance - 评分分歧
{
  "min_variance": 0.5          // 指标间评分差异超过 0.5
}

// custom - 自定义组合条件
{
  "expression": "faithfulness < 0.5 AND latency_ms > 3000",
  "max_count": 20
}
```

### 3.3 规则执行引擎

```python
# 伪代码：规则匹配器
class BadCaseCollector:
    """
    BadCase 收集器：从 EvaluationTask 的结果中按多规则筛选样本。
    """
    
    def __init__(self, task: EvaluationTask, rules: list[BadCaseCollectionRule]):
        self.task = task
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.results = task.evaluation_results.all()
    
    def collect(self) -> dict[str, list[EvaluationResult]]:
        """
        返回: {rule_name: [matched_results]}
        同一个样本可能被多个规则命中，保留所有命中记录。
        """
        collected = {}
        for rule in self.rules:
            matcher = self._get_matcher(rule)
            matched = [r for r in self.results if matcher.matches(r)]
            if matched:
                collected[rule.name] = matched
        return collected
    
    def _get_matcher(self, rule: BadCaseCollectionRule):
        """根据 rule_type 返回对应的 Matcher 实例"""
        matchers = {
            "score_below": ScoreBelowMatcher,
            "score_above": ScoreAboveMatcher,
            "metric_below": MetricBelowMatcher,
            "metric_above": MetricAboveMatcher,
            "boundary": BoundaryMatcher,
            "random": RandomSamplingMatcher,
            "stratified": StratifiedSamplingMatcher,
            "error": ErrorMatcher,
            "high_latency": HighLatencyMatcher,
            "low_latency": LowLatencyMatcher,
            "score_variance": ScoreVarianceMatcher,
            "custom": CustomExpressionMatcher,
        }
        matcher_cls = matchers.get(rule.rule_type)
        if not matcher_cls:
            raise ValueError(f"Unknown rule type: {rule.rule_type}")
        return matcher_cls(rule.parameters)
```

### 3.4 与现有 is_badcase 的整合

现有系统中 `EvaluationResult.is_badcase` 是在 Celery 任务执行时，基于 `evaluator_config.badcase_threshold` 设置的单一阈值标记。新方案中：

- **保留现有逻辑**：`is_badcase = overall_score < badcase_threshold` 继续在 `tasks.py` 中计算
- **增强收集**：收集规则引擎在任务完成后运行，基于 `is_badcase=True` 的结果集（或其他条件）进行二次筛选
- **默认规则**：系统预设一条 `score_below` 规则，阈值使用 `evaluator_config.badcase_threshold`，与新任务创建时自动关联

```
tasks.py 现有流程:
  ① 采集 Agent 响应
  ② DeepEval 评分
  ③ 计算 overall_score
  ④ 标记 is_badcase = (overall_score < badcase_threshold)  ← 保留
  ⑤ 存储 EvaluationResult
  
BadCase 收集（任务完成后触发）:
  ⑥ 加载关联的 BadCaseCollectionRule 列表
  ⑦ 运行 BadCaseCollector.collect()
  ⑧ 去重后批量创建 BadCaseFeedback 记录
  ⑨ 记录收集历史 BadCaseCollectionRecord
```

---

## 四、数据模型扩展设计

### 4.1 新增模型

#### BadCaseCollectionRule（收集规则）

```python
class BadCaseCollectionRule(models.Model):
    """BadCase collection rule definition with flexible dimensions."""
    
    RULE_TYPES = [
        ("score_below", "Score Below Threshold"),
        ("score_above", "Score Above Threshold (Spot Check)"),
        ("metric_below", "Per-Metric Below Threshold"),
        ("metric_above", "Per-Metric Above Threshold"),
        ("boundary", "Boundary Samples"),
        ("random", "Random Sampling"),
        ("stratified", "Stratified Sampling"),
        ("error", "Error Samples"),
        ("high_latency", "High Latency"),
        ("low_latency", "Low Latency (Suspected Cache)"),
        ("score_variance", "Score Variance (Judge Disagreement)"),
        ("custom", "Custom Expression"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    parameters = models.JSONField(default=dict)  # 规则参数
    target_dataset = models.ForeignKey(
        Dataset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="collection_rules"
    )
    auto_collect = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "badcase_collection_rules"
        ordering = ["-priority", "-created_at"]
```

#### BadCaseCollectionRecord（收集历史）

```python
class BadCaseCollectionRecord(models.Model):
    """Audit log for each collection execution."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    task = models.ForeignKey(
        EvaluationTask, on_delete=models.CASCADE, related_name="collection_records"
    )
    rules_snapshot = models.JSONField()  # 执行时的规则快照
    total_results = models.IntegerField()  # 任务总结果数
    collected_count = models.IntegerField()  # 本次收集的 BadCase 数
    new_feedback_count = models.IntegerField(default=0)  # 新创建的 feedback 数
    status = models.CharField(
        max_length=20,
        choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")],
        default="running",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "badcase_collection_records"
        ordering = ["-started_at"]
```

### 4.2 扩展现有模型

#### BadCaseFeedback 扩展字段

```python
# 原模型位于 evaluation/models.py，新增以下字段：

class BadCaseFeedback(models.Model):
    # ... 现有字段保持不变 ...
    
    # ↓ 新增字段 ↓
    collection_rule = models.ForeignKey(
        BadCaseCollectionRule, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="feedbacks"
    )  # 被哪个规则收集的
    collection_record = models.ForeignKey(
        BadCaseCollectionRecord, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="feedbacks"
    )  # 属于哪次收集批次
    matched_rules = models.JSONField(default=list, blank=True)  
    # 可能命中多个规则: [{"rule_id": "...", "rule_name": "低分样本", "reason": "overall_score=0.45 < 0.6"}]
    
    # 回流追踪
    migrated_to_sample = models.ForeignKey(
        DatasetSample, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="source_feedbacks"
    )  # 回流后对应的 DatasetSample
    migrated_at = models.DateTimeField(null=True, blank=True)
```

#### DatasetSample 扩展字段

```python
# 原模型位于 evaluation/models.py，新增以下字段：

class DatasetSample(models.Model):
    # ... 现有字段保持不变 ...
    
    # ↓ 新增字段 ↓
    SOURCE_TYPES = [
        ("golden", "Golden Dataset"),
        ("badcase", "BadCase Feedback"),
        ("manual", "Manual Annotation"),
        ("imported", "External Import"),
    ]
    source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPES, default="golden"
    )
    source_task = models.ForeignKey(
        EvaluationTask, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="badcase_samples"
    )  # 如果是 badcase 回流，记录原始任务
    source_result = models.ForeignKey(
        EvaluationResult, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="migrated_samples"
    )  # 记录原始 EvaluationResult
    badcase_reason = models.JSONField(default=dict, blank=True)
    # {"rule_hits": ["score_below: 0.45 < 0.6"], "original_score": 0.45}
```

#### Dataset 扩展字段

```python
class Dataset(models.Model):
    # ... 现有字段保持不变 ...
    
    # ↓ 新增字段 ↓
    is_badcase_set = models.BooleanField(
        default=False, help_text="Whether this dataset is primarily composed of badcase samples"
    )
    source_task_ids = models.JSONField(
        default=list, blank=True,
        help_text="List of task IDs that contributed badcase samples"
    )
```

### 4.3 任务配置扩展

在 `EvaluationTask.evaluator_config` 中增加 BadCase 收集配置：

```json
// evaluator_config 扩展示例
{
  "metrics": [...],
  "badcase_threshold": 0.6,
  
  // ↓ 新增：BadCase 收集配置 ↓
  "badcase_collection": {
    "enabled": true,
    "auto_collect": true,                // 任务完成后自动触发收集
    "rule_ids": ["rule-uuid-1", "rule-uuid-2"],  // 关联的收集规则（空 = 使用默认规则）
    "default_rules": [                    // 如果没有指定 rule_ids，使用默认规则
      {"type": "score_below", "params": {"threshold": 0.6}},
      {"type": "random", "params": {"sample_rate": 0.05}}
    ]
  }
}
```

---

## 五、API 接口设计

### 5.1 收集规则管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/badcase-rules/` | 获取收集规则列表 |
| `POST` | `/api/v1/badcase-rules/` | 创建收集规则 |
| `GET` | `/api/v1/badcase-rules/{id}/` | 获取规则详情 |
| `PUT` | `/api/v1/badcase-rules/{id}/` | 更新规则 |
| `DELETE` | `/api/v1/badcase-rules/{id}/` | 删除规则 |
| `POST` | `/api/v1/badcase-rules/{id}/test/` | 规则试运行（传入 task_id，预览匹配结果） |

### 5.2 BadCase 收集与查询

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks/{id}/badcases/collect/` | 触发 BadCase 收集（按关联规则） |
| `GET` | `/api/v1/tasks/{id}/badcases/` | 获取任务的 BadCase 列表（支持筛选） |
| `GET` | `/api/v1/tasks/{id}/badcases/{feedback_id}/` | 获取单个 BadCase 详情（含 Trace） |
| `GET` | `/api/v1/tasks/{id}/badcases/{feedback_id}/trace/` | 获取 BadCase 的完整执行链路 |
| `PUT` | `/api/v1/tasks/{id}/badcases/{feedback_id}/review/` | 审核 BadCase（确认/驳回） |

#### 查询参数支持

```
GET /api/v1/tasks/{id}/badcases/?
  rule_id=uuid              # 按收集规则筛选
  status=pending|reviewing|resolved|dismissed
  score_min=0.0             # 综合分下限
  score_max=0.6             # 综合分上限
  metric_name=truthfulness  # 按指标筛选
  metric_score_max=0.5      # 指标分上限
  search=关键词              # 在 input/output 中搜索
  sort_by=overall_score     # 排序字段
  sort_order=asc|desc
  page=1&page_size=20       # 分页
```

### 5.3 BadCase 回流操作

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks/{id}/badcases/migrate/` | 批量回流到数据集 |
| `POST` | `/api/v1/tasks/{id}/badcases/{feedback_id}/migrate/` | 单条回流 |
| `POST` | `/api/v1/tasks/{id}/badcases/migrate-to-new/` | 回流并创建新数据集 |
| `GET` | `/api/v1/badcases/migration-history/` | 查看回流历史 |

#### 批量回流请求体

```json
{
  "feedback_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "target_dataset_id": "uuid-dataset-001",
  "merge_strategy": "append",           // append | create_new_version
  "include_original_score": true,       // 是否在 sample notes 中记录原始评分
  "include_trace_summary": true         // 是否记录 Trace 摘要
}
```

### 5.4 统计接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/badcases/stats/` | BadCase 全局统计 |
| `GET` | `/api/v1/tasks/{id}/badcases/stats/` | 单任务 BadCase 统计 |
| `GET` | `/api/v1/badcases/trend/` | BadCase 趋势（按时间/Agent/指标维度） |

#### 响应示例：

```json
{
  "total_badcases": 234,
  "by_status": {"pending": 45, "reviewing": 12, "resolved": 150, "dismissed": 27},
  "by_rule_type": {
    "score_below": 180,
    "metric_below": 30,
    "random": 24
  },
  "by_metric": {
    "truthfulness": 67,
    "faithfulness": 45,
    "answer_relevancy": 32,
    ...
  },
  "migration_rate": 0.64,   // 回流率 = resolved / total
  "avg_review_time_hours": 3.2
}
```

---

## 六、前端页面设计

### 6.1 页面结构

```
📁 BadCase 管理（新增顶级导航）
  ├── 📊 BadCase 概览看板
  │   ├── 统计卡片（总数/待审核/已回流/趋势）
  │   ├── 按 Agent 分布图
  │   ├── 按指标分布图
  │   └── 近期 BadCase 趋势图
  │
  ├── 📋 BadCase 列表
  │   ├── 筛选栏（任务/规则/状态/分数段/指标/搜索）
  │   ├── 表格/卡片列表
  │   │   ├── 样本 ID | 输入摘要 | 综合分 | 命中规则 | 状态 | 操作
  │   │   └── 每行操作：[查看详情] [查看 Trace] [审核] [回流] [驳回]
  │   ├── 批量操作栏（多选后：批量审核/批量回流/批量驳回）
  │   └── 分页
  │
  ├── 🔍 BadCase 详情（弹窗/侧边栏）
  │   ├── 基本信息（任务名/Agent/数据集/时间）
  │   ├── 评分详情
  │   │   ├── 综合分环形图
  │   │   └── 各指标分卡片 + 评分理由
  │   ├── 输入/期望输出/实际输出 三栏对比
  │   ├── 执行链路 Trace（内嵌）
  │   │   ├── Agent 调用时间线（SSE 流式展示）
  │   │   ├── 各 Judge 评分耗时
  │   │   └── Token 消耗统计
  │   ├── 命中规则列表 + 匹配原因
  │   └── 操作区：
  │       [确认 BadCase] [驳回] [回流到数据集] [添加备注]
  │
  ├── ⚙️ 收集规则管理
  │   ├── 规则列表
  │   │   ├── 规则名称 | 类型 | 参数 | 状态 | 命中次数 | 操作
  │   │   └── [创建规则] [编辑] [启用/禁用] [试运行] [删除]
  │   ├── 规则创建/编辑表单
  │   │   ├── 规则类型选择（下拉）
  │   │   ├── 动态参数表单（根据 rule_type 动态渲染）
  │   │   ├── 目标数据集（可选）
  │   │   └── 试运行按钮（选择历史任务预览匹配结果）
  │   └── 试运行结果预览
  │
  └── 📈 回流历史
      ├── 回流记录列表
      └── 回流详情（源任务 → 目标数据集 → 新评测任务链路）
```

### 6.2 在现有页面中的集成

#### TaskDetail.vue 增强

在现有任务详情页的 BadCase 区域增加：

```
┌──────────────────────────────────────────────────────────┐
│ 📊 任务：2026Q2-知识助手回归测试                          │
├──────────────────────────────────────────────────────────┤
│ 综合得分: 0.84  BadCase: 23  样本: 500/500               │
│                                                          │
│ 📋 BadCase 概览（新增）                                   │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 规则                 命中数   状态                    │ │
│ │ ✅ 低分阈值(<0.6)      18     待审核                  │ │
│ │ ✅ 真实性低分(<0.5)     3     待审核                  │ │
│ │ ✅ 随机抽样(5%)         2     待审核                  │ │
│ │                                                        │ │
│ │ [查看全部 BadCase] [一键收集] [批量回流]               │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ 📋 BadCase 列表（可折叠）                                  │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ ☐  #001  输入: "公司A的核心业务..."  得分: 0.45       │ │
│ │    命中: 低分阈值  真实性=0.32  [详情] [Trace] [回流] │ │
│ │ ☐  #023  输入: "请解释量子计算..."  得分: 0.52       │ │
│ │    命中: 低分阈值  忠实性=0.41  [详情] [Trace] [回流] │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

#### ReportDetail.vue 增强

在报告页增加 BadCase 分布分析和回流建议：

- BadCase 按指标维度分布的柱状图
- BadCase 分数分布直方图（红色高亮 BadCase 区域）
- 与历史版本对比的 BadCase 率变化趋势
- 一键导出 BadCase 报告（供团队评审）

### 6.3 关键交互设计

#### 6.3.1 创建任务时的 BadCase 配置

在 TaskCreate.vue 三步向导的"配置评估器"步骤中增加 BadCase 区域：

```
┌──────────────────────────────────────────────────────────────┐
│ Step 3 - 配置评估器                                          │
├──────────────────────────────────────────────────────────────┤
│ ... 指标配置区域 ...                                          │
├──────────────────────────────────────────────────────────────┤
│ 📋 BadCase 收集配置（新增）                                   │
│                                                              │
│ ☑ 启用自动收集         任务完成后自动收集 BadCase            │
│                                                              │
│ 收集规则:                                                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ☑ 低分收集    综合分 < [0.6  ▼]                          │ │
│ │ ☐ 分指标收集  [真实性 ▼] < [0.5  ▼]                      │ │
│ │ ☐ 随机抽样    比例 [5%  ▼]  上限 [20  ]                  │ │
│ │ ☐ 错误样本    收集所有异常结果                            │ │
│ │ ☐ 高延迟      响应时间 > [5000ms ▼]                      │ │
│ │ [+ 添加规则]                                              │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ 目标数据集: [选择已有数据集 ▼]  [或创建新数据集]              │
│                                                              │
│                              [上一步]  [开始评测]              │
└──────────────────────────────────────────────────────────────┘
```

#### 6.3.2 BadCase 详情弹窗中的 Trace 回放

```
┌──────────────────────────────────────────────────────────────┐
│ BadCase 详情 - 样本 #001                          [✕ 关闭]  │
├──────────────────────────────────────────────────────────────┤
│ 综合得分: 0.45  │  命中规则: 低分阈值(<0.6)                  │
│                                                              │
│ ┌─ 输入 ───────────────────────────────────────────────────┐ │
│ │ 请详细说明公司A在2025年的核心业务布局和战略方向...         │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ 期望输出 ───────────────────────┐ ┌─ 实际输出 ──────────┐│
│ │ 公司A在2025年聚焦三大战略...      │ │ 公司A是一家科技公司..││
│ │ (完整黄金答案)                    │ │ (不完整/错误回答)    ││
│ └──────────────────────────────────┘ └─────────────────────┘│
│                                                              │
│ 评分详情:                                                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 答案相关性: 0.72 ✅   忠实性: 0.38 ❌                    │ │
│ │ 一致性: 0.65 ✅       真实性: 0.32 ❌                    │ │
│ │ 稳定性: 0.55 ❌       F1: 0.41 ❌                        │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ 📡 执行链路 Trace:                                           │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ⏱ 总耗时 6.9s  Tokens 757                               │ │
│ │ ├─ [1.8s] Agent 调用 (HTTP/SSE)                          │ │
│ │ │   ├─ POST https://agent-api/chat/simple               │ │
│ │ │   ├─ SSE chunk #1: "公司A"    0.2s                    │ │
│ │ │   ├─ SSE chunk #2: "是一家"   0.3s                    │ │
│ │ │   ├─ SSE chunk #3: "科技公司" 0.2s                    │ │
│ │ │   └─ ... (展开查看完整 SSE 流)                         │ │
│ │ ├─ [0.8s] Judge: AnswerRelevancy → 0.72                 │ │
│ │ │   理由: "回答部分涉及了公司A的业务方向..."              │ │
│ │ ├─ [0.9s] Judge: Faithfulness → 0.38 ❌                 │ │
│ │ │   理由: "回答未提供具体的业务数据，与上下文不符..."     │ │
│ │ └─ [1.2s] Judge: Truthfulness → 0.32 ❌                 │ │
│ │     理由: "回答中关于2025年业务布局的信息不准确..."      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ 操作区:                                                      │
│ [✅ 确认 BadCase]  [❌ 驳回]  [📥 回流到数据集]  [💬 备注]  │
└──────────────────────────────────────────────────────────────┘
```

---

## 七、后端实现方案

### 7.1 模块结构

```
backend/
├── evaluation/
│   ├── models.py                    # 新增 BadCaseCollectionRule, BadCaseCollectionRecord
│   ├── badcase/
│   │   ├── __init__.py
│   │   ├── collector.py             # BadCaseCollector 收集器（规则引擎）
│   │   ├── matchers.py              # 各类 Matcher 实现
│   │   ├── migrator.py              # BadCase 回流逻辑
│   │   └── stats.py                 # BadCase 统计分析
│   └── tasks.py                     # 在 run_evaluation_task 末尾集成收集调用
├── api/
│   ├── views/
│   │   ├── badcase_rule_views.py    # 收集规则 CRUD API
│   │   ├── badcase_views.py         # BadCase 查询/审核/回流 API
│   │   └── badcase_stats_views.py   # BadCase 统计 API
│   └── serializers/
│       └── serializers.py           # 新增 BadCase 相关 Serializer
```

### 7.2 核心实现要点

#### 7.2.1 收集器与 Celery 集成

```python
# evaluation/tasks.py 中的扩展

@shared_task(bind=True)
def run_evaluation_task(self, task_id: str):
    # ... 现有评测流程 ...
    
    # === 新增：BadCase 自动收集 ===
    badcase_config = task.evaluator_config.get("badcase_collection", {})
    if badcase_config.get("enabled") and badcase_config.get("auto_collect"):
        collect_badcases_for_task.delay(str(task.id))

@shared_task
def collect_badcases_for_task(task_id: str):
    """异步执行 BadCase 收集"""
    from evaluation.badcase.collector import BadCaseCollector
    
    task = EvaluationTask.objects.get(id=task_id)
    rules = _load_collection_rules(task)
    
    collector = BadCaseCollector(task, rules)
    collected = collector.collect()
    
    # 去重 + 批量创建 BadCaseFeedback
    _upsert_feedbacks(task, collected)
    
    # 记录收集历史
    BadCaseCollectionRecord.objects.create(
        task=task,
        rules_snapshot=[r.to_dict() for r in rules],
        total_results=task.result_count,
        collected_count=sum(len(v) for v in collected.values()),
        status="completed",
        completed_at=timezone.now(),
    )
```

#### 7.2.2 回流逻辑

```python
# evaluation/badcase/migrator.py

class BadCaseMigrator:
    """将 BadCase 回流到数据集"""
    
    def migrate_to_dataset(
        self, 
        feedbacks: list[BadCaseFeedback], 
        target_dataset: Dataset,
        merge_strategy: str = "append"
    ):
        created_samples = []
        for fb in feedbacks:
            sample = DatasetSample.objects.create(
                dataset=target_dataset,
                sample_id=self._generate_sample_id(target_dataset),
                input=fb.result.input,
                expected_output=fb.result.expected_output,
                context=fb.result.context,
                retrieval_context=fb.result.retrieval_context,
                source_type="badcase",
                source_task=fb.result.task,
                source_result=fb.result,
                badcase_reason={
                    "original_score": fb.result.overall_score,
                    "metric_scores": fb.result.metric_results,
                    "matched_rules": fb.matched_rules,
                },
                notes=f"[BadCase回流] 原始任务: {fb.result.task.name}, "
                      f"原始分数: {fb.result.overall_score}, "
                      f"审核备注: {fb.review_comment}",
            )
            fb.migrated_to_sample = sample
            fb.migrated_at = timezone.now()
            fb.status = "resolved"
            fb.save()
            created_samples.append(sample)
        
        target_dataset.update_sample_count()
        target_dataset.source_task_ids = list(set(
            target_dataset.source_task_ids + [str(fb.result.task_id) for fb in feedbacks]
        ))
        target_dataset.is_badcase_set = True
        target_dataset.save()
        
        return created_samples
    
    def create_badcase_dataset(
        self, 
        feedbacks: list[BadCaseFeedback], 
        name: str
    ) -> Dataset:
        """创建专门的 BadCase 数据集"""
        dataset = Dataset.objects.create(
            name=name,
            data_type="regression",
            is_badcase_set=True,
            status="published",
        )
        return self.migrate_to_dataset(feedbacks, dataset)
```

#### 7.2.3 Trace 关联查询

```python
# 在 badcase_views.py 中

@action(detail=True, methods=["get"], url_path="trace")
def get_badcase_trace(self, request, id=None, feedback_id=None):
    """
    获取 BadCase 的完整执行链路。
    优先从 Trace 表查询，若无则从 EvaluationResult 构造简化版。
    """
    feedback = get_object_or_404(
        BadCaseFeedback, 
        id=feedback_id, 
        result__task_id=id
    )
    
    # 尝试获取完整 Trace
    trace = Trace.objects.filter(
        task_id=id, 
        sample_id=feedback.result.sample_id
    ).first()
    
    if trace:
        trace_data = {
            "trace_id": trace.trace_id,
            "spans": trace.spans,
            "total_duration_ms": trace.total_duration_ms,
            "total_tokens": trace.total_tokens,
            "raw_sse_chunks": trace.raw_sse_chunks,
            "final_output": trace.final_output,
        }
    else:
        # 构造简化 Trace（从 EvaluationResult）
        trace_data = {
            "type": "simplified",
            "input": feedback.result.input,
            "output": feedback.result.actual_output,
            "latency_ms": feedback.result.latency_ms,
            "metric_results": feedback.result.metric_results,
            "overall_score": feedback.result.overall_score,
        }
    
    return Response({
        "feedback": BadCaseFeedbackSerializer(feedback).data,
        "trace": trace_data,
    })
```

---

## 八、默认规则与最佳实践

### 8.1 系统预置规则

系统初始化时通过 migration 创建以下默认规则：

| 规则名称 | rule_type | 参数 | 说明 |
|---------|-----------|------|------|
| 默认低分收集 | `score_below` | `threshold: 0.6` | 与任务 badcase_threshold 对齐 |
| 真实性低分 | `metric_below` | `metric: truthfulness, threshold: 0.5` | 重点关注真实性指标 |
| 忠实性低分 | `metric_below` | `metric: faithfulness, threshold: 0.5` | 重点关注忠实性指标 |
| 随机质量抽查 | `random` | `sample_rate: 0.05, max: 20` | 5% 随机抽查防评分膨胀 |
| 评分分歧 | `score_variance` | `min_variance: 0.5` | 指标间分歧大的样本 |

### 8.2 业界参考实践

| 平台/工具 | 核心机制 | 可借鉴点 |
|----------|---------|---------|
| **LangSmith** | Annotation Queue + 自定义筛选条件 | 多维度筛选器组合，支持表达式 DSL |
| **MLflow Human Feedback** | 评分阈值 + 人工标注工作流 | 与现有 MLflow 架构天然兼容 |
| **Arize AI Phoenix** | 性能监控 + Drift 检测 + Trace 回放 | Trace 级别的 BadCase 定位 |
| **Ragas** | Score distribution analysis + 失败模式分析 | 按失败模式分类（忠实性失败/相关性失败等）|
| **Label Studio / Argilla** | 主动学习 + 相似度搜索 | 相似 BadCase 聚合，减少重复标注 |
| **DeepEval** | Confident score + 指标阈值配置 | 在指标定义层面内置阈值 |

### 8.3 工作流建议

```
标准 BadCase 处理流程:
  1. 评测任务完成 → 自动收集 BadCase（auto_collect=true）
  2. BadCase 进入"待审核"队列
  3. 算法工程师审核 BadCase：
     a. 查看详情 + Trace 回放
     b. 确认是真 BadCase → 标记"审核中" → 回流到数据集
     c. 确认是误判 → 标记"已驳回" → 记录驳回原因
  4. 回流后的样本 → 新版本数据集
  5. 下一轮评测任务使用新数据集 → 验证改进效果
  6. 若 BadCase 复现 → 标记为"顽固 BadCase" → 升级处理

迭代节奏建议:
  - 每周：随机抽样 5% BadCase 进行人工审核
  - 每轮评测后：自动收集的 BadCase 48h 内完成审核
  - 每月：分析 BadCase 趋势，更新收集规则阈值
  - 每季度：清理已修复的 BadCase，归档历史数据
```

---

## 九、实施优先级建议

### Phase 1（核心功能，约 3-5 天）

- [ ] 数据模型扩展：`BadCaseCollectionRule`、`BadCaseCollectionRecord`、扩展现有模型字段
- [ ] 收集器核心：`BadCaseCollector` + `score_below`、`metric_below`、`random` 三种 Matcher
- [ ] Celery 集成：任务完成后自动触发收集
- [ ] 基本 API：规则 CRUD + BadCase 列表查询 + 单条详情（含 Trace）
- [ ] 数据库 migration

### Phase 2（回流闭环，约 2-3 天）

- [ ] 回流逻辑：`BadCaseMigrator` + 单条/批量回流 API
- [ ] 前端 BadCase 列表页 + 详情弹窗
- [ ] TaskDetail.vue 中的 BadCase 概览区域
- [ ] 回流历史记录

### Phase 3（完善体验，约 2-3 天）

- [ ] 剩余 Matcher 实现：`boundary`、`stratified`、`error`、`high_latency`、`score_variance`、`custom`
- [ ] 收集规则管理页面（前端）
- [ ] BadCase 统计看板 + 趋势图
- [ ] ReportDetail.vue 中的 BadCase 分析区域
- [ ] 规则试运行功能

### Phase 4（高级功能，按需）

- [ ] 自定义表达式引擎（支持 AND/OR 组合条件）
- [ ] 相似 BadCase 聚合（文本相似度聚类）
- [ ] BadCase 自动分类（失败模式识别）
- [ ] 回流效果追踪（回流前后的分数变化对比）
- [ ] Webhook 通知（新 BadCase 产生时通知相关人员）

---

## 十、风险与注意事项

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 收集规则配置不当导致误收集大量样本 | 审核负担 | 规则试运行功能 + 每规则 max_count 上限 |
| BadCase 回流造成数据集膨胀 | 评测效率下降 | 支持去重（相同 input 不重复回流）、定期清理 |
| Trace 数据量大，查询性能下降 | 详情页加载慢 | Trace 分页加载、SSE chunks 压缩存储 |
| 回流后的样本再次产生 BadCase | 无限循环 | 新增 `regression_count` 字段追踪重复 BadCase 次数 |
| 与 MLflow Human Feedback 功能重叠 | 用户困惑 | 明确职责：自研 BadCase 侧重自动化收集和数据集回流，MLflow 侧重人工标注 UI |

---

## 附录：与你原始想法的对照

| 你的想法 | 方案中的对应 | 补充/优化 |
|---------|-------------|----------|
| 收集 BadCase 样本 | 收集规则引擎 + BadCaseCollector | 增加了 12 种收集维度，不仅限于分数阈值 |
| 查看任务执行链路 | Trace 关联查询 API + 前端详情弹窗 | 复用现有 Trace 表，增加 SSE 流式展示 |
| 放入数据集再评测 | BadCaseMigrator + source_type 追踪 | 增加了样本溯源、回流历史、防重复机制 |
| 多个维度收集 | 收集规则模型 + Matcher 策略模式 | 增加了高分段抽查、分层抽样、评分分歧等维度 |
| （未提及） | BadCase 审核工作流 | 增加 pending→reviewing→resolved/dismissed 生命周期 |
| （未提及） | 收集规则管理界面 | 可视化配置规则，试运行预览 |
| （未提及） | 统计与趋势分析 | 按 Agent/指标/时间维度分析 BadCase 分布 |
| （未提及） | 与 MLflow 的整合 | BadCase 数据与 MLflow Run 双向关联 |