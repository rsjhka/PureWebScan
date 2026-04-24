<template>
  <div class="rules-page">
    <div class="page-header">
      <h1>规则管理</h1>
      <p>查看和管理 Web 指纹识别规则库</p>
    </div>

    <RuleList />
  </div>
</template>

<script setup lang="ts">
import RuleList from '@/components/RuleList.vue'
</script>

<style lang="scss" scoped>
.rules-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
