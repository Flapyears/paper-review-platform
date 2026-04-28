<script setup>
import { RouterView } from "vue-router";
</script>

<template>
  <div class="auth-layout">
    <section class="auth-hero panel-card">
      <span class="hero-kicker">欢迎使用</span>
      <h1>毕业论文评审平台</h1>
      <p>登录后即可查看论文进展、待办事项和评阅结果。</p>
      <ul class="hero-list">
        <li>学生：填写论文信息，上传终稿</li>
        <li>管理员：查看进展，安排评阅</li>
        <li>评阅教师：处理任务，填写意见</li>
      </ul>
      <div class="hero-foot">
        <span>进度清楚</span>
        <span>操作顺手</span>
        <span>结果可查</span>
      </div>
    </section>

    <section class="auth-form-wrap">
      <RouterView />
    </section>
  </div>
</template>
