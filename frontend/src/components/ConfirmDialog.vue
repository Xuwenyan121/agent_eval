<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="420px"
    class="confirm-dialog"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="confirm-body">
      <el-icon class="confirm-icon" :size="32" :color="iconColor">
        <component :is="icon" />
      </el-icon>
      <p class="confirm-message">{{ message }}</p>
      <p class="confirm-detail" v-if="detail">{{ detail }}</p>
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">Cancel</el-button>
      <el-button :type="confirmType" @click="$emit('confirm')">
        {{ confirmLabel }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: 'Confirm' },
  message: { type: String, required: true },
  detail: { type: String, default: '' },
  icon: { type: String, default: 'WarningFilled' },
  iconColor: { type: String, default: '#FFAA00' },
  confirmLabel: { type: String, default: 'Confirm' },
  confirmType: { type: String, default: 'danger' },
})

defineEmits(['update:visible', 'confirm'])
</script>

<style scoped>
.confirm-body {
  text-align: center;
  padding: 16px 0;
}
.confirm-icon { margin-bottom: 12px; }
.confirm-message { font-size: 15px; color: var(--text-primary); margin-bottom: 8px; }
.confirm-detail { font-size: 13px; color: var(--text-secondary); }
</style>
