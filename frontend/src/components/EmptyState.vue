<template>
  <div class="empty-state">
    <el-icon class="empty-icon" :size="48">
      <component :is="icon" />
    </el-icon>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc" v-if="description">{{ description }}</p>
    <el-button v-if="actionLabel" class="btn-gradient" @click="$emit('action')">
      {{ actionLabel }}
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: 'FolderOpened' },
  title: { type: String, default: 'No Data' },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})

defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-icon {
  color: var(--border-color);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 360px;
  margin-bottom: 20px;
}
</style>
