<template>
  <div class="app">
    <header class="app-header">
      <h1>简历 JD 评估器</h1>
      <nav class="app-nav">
        <router-link to="/evaluate" active-class="active">评估</router-link>
        <router-link to="/jds" active-class="active">JD 管理</router-link>
        <router-link to="/resumes" active-class="active">简历管理</router-link>
      </nav>
    </header>
    <main class="app-body">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #333;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  height: 56px;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-header h1 {
  margin: 0;
  font-size: 18px;
}

.app-nav {
  display: flex;
  gap: 8px;
}

.app-nav a {
  padding: 6px 14px;
  color: #333;
  text-decoration: none;
  border-radius: 4px;
  font-size: 14px;
}

.app-nav a:hover {
  background: #f5f5f5;
}

.app-nav a.active {
  background: #1890ff;
  color: white;
}

.app-body {
  flex: 1;
  overflow: hidden;
}

.btn {
  padding: 6px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:disabled {
  background: #91caff;
}

.btn-success {
  background: #52c41a;
  color: white;
}

.btn-danger {
  background: #ff4d4f;
  color: white;
}

.btn-secondary {
  background: #fafafa;
  border: 1px solid #d9d9d9;
  color: #333;
}
</style>
