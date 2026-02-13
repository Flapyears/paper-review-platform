<script setup>
import { RouterView } from "vue-router";
</script>

<template>
  <div class="auth-layout">
    <section class="auth-hero panel-card">
      <span class="hero-kicker">Paper Review Platform</span>
      <h1>毕业论文评审平台</h1>
      <p>请使用账号密码登录，系统将根据角色进入对应工作台。</p>
      <ul class="hero-list">
        <li>学生：论文上传与送审</li>
        <li>管理员：评阅分配与过程控制</li>
        <li>评阅教师：任务执行与评阅提交</li>
      </ul>
      <div class="hero-foot">
        <span>流程可追溯</span>
        <span>权限隔离</span>
        <span>状态联动</span>
      </div>
    </section>

    <section class="auth-form-wrap">
      <RouterView />
    </section>
  </div>
</template>
