<template>
  <div class="results-page">
    <div class="page-header">
      <h1>扫描结果</h1>
      <p>查看历史扫描结果和技术检测报告</p>
    </div>

    <ResultTable />
  </div>
</template>

<script setup lang="ts">
import ResultTable from '@/components/ResultTable.vue'
</script>

<style lang="scss" scoped>
.results-page {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
