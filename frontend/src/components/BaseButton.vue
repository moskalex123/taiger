<template>
  <button class="base-button">
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
</script>

<style scoped>
.base-button {
  /* Add some basic styling */
  padding: 8px 16px;
  border-radius: 4px;
  border: 1px solid #ccc;
  background-color: #f0f0f0;
  cursor: pointer;
}
</style>