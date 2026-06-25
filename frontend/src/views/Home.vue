<template>
  <div class="home-page">
    <!-- Hero Section -->
    <div class="hero">
      <div class="hero-content">
        <h1 class="hero-title">AI 应用平台</h1>
        <p class="hero-subtitle">选择一个应用开始使用</p>
      </div>
    </div>

    <!-- App Cards Grid -->
    <div class="apps-grid">
      <!-- Agent Eval Card -->
      <a href="/dashboard" class="app-card" @click.prevent="navigateTo('/dashboard')">
        <div class="app-icon app-icon--eval">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="app-info">
          <h2 class="app-name">Agent Eval</h2>
          <p class="app-desc">AI 智能体评测平台</p>
          <span class="app-badge">评测 · 分析 · 优化</span>
        </div>
        <div class="app-arrow">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 7L18 12M18 12L13 17M18 12H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </a>

      <!-- Hermes Card -->
      <a href="http://192.168.107.188:8649/#/hermes/chat" class="app-card" @click.prevent="navigateTo('http://192.168.107.188:8649/#/hermes/chat')">
        <div class="app-icon app-icon--chat">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M8 12H8.01M12 12H12.01M16 12H16.01M21 12C21 16.9706 16.9706 21 12 21C10.3113 21 8.72782 20.5406 7.35861 19.7364L3 21L4.26357 16.6414C3.45945 15.2722 3 13.6887 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="app-info">
          <h2 class="app-name">Hermes</h2>
          <p class="app-desc">AI 智能助手对话平台</p>
          <span class="app-badge">对话 · 问答 · 服务</span>
        </div>
        <div class="app-arrow">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 7L18 12M18 12L13 17M18 12H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </a>
    </div>

    <!-- Footer -->
    <div class="home-footer">
      <p>© 2026 AI 应用平台 · 企业级智能体解决方案</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function navigateTo(url) {
  if (url.startsWith('http')) {
    window.open(url, '_blank')
  } else {
    router.push(url)
  }
}
</script>

<style scoped>
.home-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
  overflow-y: auto;
}

/* Hero */
.hero {
  padding: 80px 24px 60px;
  text-align: center;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 12px;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  font-size: 18px;
  color: #64748b;
  margin: 0;
}

/* Apps Grid */
.apps-grid {
  display: flex;
  justify-content: center;
  gap: 32px;
  padding: 40px 24px;
  flex-wrap: wrap;
  max-width: 900px;
  margin: 0 auto;
}

.app-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  width: 380px;
  min-height: 140px;
}

.app-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
  border-color: rgba(0, 0, 0, 0.08);
}

.app-card:hover .app-arrow svg {
  transform: translateX(4px);
}

/* App Icon */
.app-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.app-icon svg {
  width: 32px;
  height: 32px;
}

.app-icon--eval {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.app-icon--chat {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
}

/* App Info */
.app-info {
  flex: 1;
  min-width: 0;
}

.app-name {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 6px;
}

.app-desc {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 10px;
}

.app-badge {
  display: inline-block;
  font-size: 11px;
  color: #94a3b8;
  padding: 4px 10px;
  background: #f1f5f9;
  border-radius: 20px;
  letter-spacing: 0.5px;
}

/* App Arrow */
.app-arrow {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.3s ease;
}

.app-arrow svg {
  width: 20px;
  height: 20px;
  color: #94a3b8;
  transition: transform 0.3s ease;
}

.app-card:hover .app-arrow {
  background: #e2e8f0;
}

.app-card:hover .app-arrow svg {
  color: #475569;
}

/* Footer */
.home-footer {
  margin-top: auto;
  padding: 24px;
  text-align: center;
}

.home-footer p {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

/* Responsive */
@media (max-width: 768px) {
  .hero {
    padding: 60px 20px 40px;
  }
  
  .hero-title {
    font-size: 32px;
  }
  
  .hero-subtitle {
    font-size: 16px;
  }
  
  .apps-grid {
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 24px;
  }
  
  .app-card {
    width: 100%;
    max-width: 400px;
  }
}
</style>
