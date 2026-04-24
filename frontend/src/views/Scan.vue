<template>
  <div class="scan-page">
    <div class="page-header">
      <h1>Web 指纹扫描</h1>
      <p>输入目标 URL 开始识别 Web 技术栈</p>
    </div>

    <ScanForm />
  </div>
</template>

<script setup lang="ts">
import ScanForm from '@/components/ScanForm.vue'
</script>

<style lang="scss" scoped>
.scan-page {
  max-width: 900px;
  margin: 0 auto;
}
</style>
