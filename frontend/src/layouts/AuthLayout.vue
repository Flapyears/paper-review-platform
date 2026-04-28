<script setup>
import { RouterView } from "vue-router";
import { noticeState, clearNotice } from "../stores/notice";
import NoticeBanner from "../components/common/NoticeBanner.vue";
import DevToolsDrawer from "../components/devtools/DevToolsDrawer.vue";

const showDevTools =
  import.meta.env.DEV || String(import.meta.env.VITE_ENABLE_DEVTOOLS || "") === "true";
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
      <div v-if="noticeState.message" class="auth-notice-wrap">
        <NoticeBanner :message="noticeState.message" :type="noticeState.type" />
        <button class="ghost close-notice" @click="clearNotice">关闭提示</button>
      </div>
      <RouterView />
    </section>

    <DevToolsDrawer v-if="showDevTools" />
  </div>
</template>
