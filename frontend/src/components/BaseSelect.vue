<template>
  <select class="base-select">
    <slot></slot>
  </select>
</template>

<script setup lang="ts">
</script>

<style scoped>
.base-select {
  /* Add some basic styling */
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
}
</style>