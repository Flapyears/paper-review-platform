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
      <div class="hero-seal">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
      </div>
      <span class="hero-kicker">ACADEMIC REVIEW SYSTEM</span>
      <h1>毕业论文评审平台</h1>
      <p>为您提供专业、透明、高效的论文评阅全流程管理服务。</p>
      <ul class="hero-list">
        <li>实时追踪论文提交与审核状态</li>
        <li>智能分配评阅任务与进度提醒</li>
        <li>在线填写评阅意见与结果反馈</li>
      </ul>
      <div class="hero-foot">
        <span>全流程数字化</span>
        <span>学术诚信保障</span>
        <span>高效协同办公</span>
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
