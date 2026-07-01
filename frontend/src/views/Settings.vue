<template>
  <div class="settings-page">
    <h2 class="page-title">配置模块</h2>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane label="指标配置" name="metrics">
        <MetricConfig />
      </el-tab-pane>

      <el-tab-pane label="指标调试" name="playground">
        <MetricPlayground />
      </el-tab-pane>

      <el-tab-pane label="模型配置" name="models">
        <ModelConfig />
      </el-tab-pane>

      <el-tab-pane label="Prompt配置" name="prompts">
        <PromptLibrary />
      </el-tab-pane>

      <el-tab-pane label="BadCase收集规则" name="badcase-rules">
        <BadCaseRules />
      </el-tab-pane>

      <el-tab-pane label="系统信息" name="system">
        <div class="card info-card">
          <h4 class="section-title">平台信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">平台</span>
              <span class="info-value">智能体评测平台</span>
            </div>
            <div class="info-item">
              <span class="info-label">版本</span>
              <span class="info-value accent">v3.2</span>
            </div>
            <div class="info-item">
              <span class="info-label">API 基础地址</span>
              <span class="info-value mono">{{ apiBaseUrl }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">前端框架</span>
              <span class="info-value">Vue 3 + Vite + Element Plus</span>
            </div>
            <div class="info-item">
              <span class="info-label">后端框架</span>
              <span class="info-value">Django 5 + DRF</span>
            </div>
            <div class="info-item">
              <span class="info-label">任务执行器</span>
              <span class="info-value">Celery + Redis</span>
            </div>
            <div class="info-item">
              <span class="info-label">数据库</span>
              <span class="info-value">PostgreSQL / SQLite（开发）</span>
            </div>
            <div class="info-item">
              <span class="info-label">追踪</span>
              <span class="info-value">MLflow</span>
            </div>
          </div>
        </div>

        <div class="card info-card">
          <h4 class="section-title">快捷链接</h4>
          <div class="links-grid">
            <a class="link-card" @click="$router.push('/dashboard')">
              <el-icon :size="20"><DataAnalysis /></el-icon>
              <span>仪表盘</span>
            </a>
            <a class="link-card" @click="$router.push('/agents')">
              <el-icon :size="20"><Monitor /></el-icon>
              <span>智能体</span>
            </a>
            <a class="link-card" @click="$router.push('/datasets')">
              <el-icon :size="20"><FolderOpened /></el-icon>
              <span>数据集</span>
            </a>
            <a class="link-card" @click="$router.push('/tasks')">
              <el-icon :size="20"><SetUp /></el-icon>
              <span>评测任务</span>
            </a>
            <a class="link-card" @click="$router.push('/reports')">
              <el-icon :size="20"><Document /></el-icon>
              <span>评测报告</span>
            </a>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MetricConfig from '@/views/MetricConfig.vue'
import MetricPlayground from '@/views/MetricPlayground.vue'
import ModelConfig from '@/views/ModelConfig.vue'
import PromptLibrary from '@/views/PromptLibrary.vue'
import BadCaseRules from '@/views/BadCaseRules.vue'

const activeTab = ref('metrics')
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 16px; }
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0; }

.settings-tabs :deep(.el-tabs__item) { color: var(--text-secondary); font-size: 13px; }
.settings-tabs :deep(.el-tabs__item.is-active) { color: var(--accent-start); }
.settings-tabs :deep(.el-tabs__active-bar) { background: var(--accent-start); }
.settings-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-color); }

/* System Info */
.info-card {
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-input) 100%);
  margin-top: 16px;
}
.section-title { color: var(--text-primary); font-size: 14px; margin: 0 0 12px; }
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.info-value { font-size: 13px; color: var(--text-primary); }
.info-value.accent { color: var(--accent-start); font-weight: 600; }
.info-value.mono { font-family: monospace; font-size: 12px; }

.links-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.link-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.link-card:hover { border-color: rgba(108, 92, 231, 0.4); }
.link-card .el-icon { color: var(--accent-start); }
</style>