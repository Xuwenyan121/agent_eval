<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container" :class="themeClass">
      <template v-if="isHomePage">
        <router-view />
      </template>
      <el-container v-else>
        <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="sidebar">
          <div class="logo">
            <span v-if="!sidebarCollapsed" class="logo-text">Agent Eval</span>
            <span v-else class="logo-icon">AE</span>
          </div>
          <el-menu
            :default-active="$route.path"
            :collapse="sidebarCollapsed"
            router
            class="sidebar-menu"
            background-color="transparent"
          >
            <el-menu-item index="/">
              <el-icon><HomeFilled /></el-icon>
              <template #title>首页</template>
            </el-menu-item>
            <el-menu-item index="/dashboard">
              <el-icon><DataAnalysis /></el-icon>
              <template #title>仪表盘</template>
            </el-menu-item>
            <el-menu-item index="/agents">
              <el-icon><Monitor /></el-icon>
              <template #title>智能体</template>
            </el-menu-item>
            <el-menu-item index="/datasets">
              <el-icon><FolderOpened /></el-icon>
              <template #title>数据集</template>
            </el-menu-item>
            <el-menu-item index="/tasks">
              <el-icon><VideoPlay /></el-icon>
              <template #title>评测任务</template>
            </el-menu-item>
            <el-menu-item index="/reports">
              <el-icon><TrendCharts /></el-icon>
              <template #title>评测报告</template>
            </el-menu-item>
            <el-menu-item index="/badcases">
              <el-icon><WarningFilled /></el-icon>
              <template #title>BadCase</template>
            </el-menu-item>
            <el-menu-item index="/settings">
              <el-icon><Setting /></el-icon>
              <template #title>配置模块</template>
            </el-menu-item>
          </el-menu>
          <div class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon>
              <component :is="sidebarCollapsed ? 'Expand' : 'Fold'" />
            </el-icon>
          </div>
        </el-aside>

        <el-container>
          <el-header class="header">
            <div class="header-left">
              <h2 class="page-title">{{ currentPageTitle }}</h2>
            </div>
            <div class="header-right">
              <el-switch
                v-model="isDark"
                :active-icon="Moon"
                :inactive-icon="Sunny"
                inline-prompt
                class="theme-switch"
                @change="toggleTheme"
              />
            </div>
          </el-header>
          <el-main class="main-content">
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { Moon, Sunny } from '@element-plus/icons-vue'

const route = useRoute()
const sidebarCollapsed = ref(false)
const isDark = ref(true)

const isHomePage = computed(() => route.name === 'Home')

const pageTitles = {
  '/': '首页',
  '/dashboard': '仪表盘',
  '/agents': '智能体管理',
  '/datasets': '数据集管理',
  '/tasks': '评测任务',
  '/reports': '报告中心',
  '/badcases': 'BadCase 管理',
  '/settings': '配置模块',
}

const currentPageTitle = computed(() => {
  const path = route.path
  return pageTitles[path] || pageTitles[path.split('/').slice(0, 2).join('/')] || 'Agent Eval'
})

const themeClass = computed(() => isDark.value ? '' : 'light-theme')

function toggleTheme(val) {
  localStorage.setItem('theme', val ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light') {
    isDark.value = false
  }
})
</script>