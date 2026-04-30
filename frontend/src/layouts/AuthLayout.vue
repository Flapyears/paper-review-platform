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
        <img src="../assets/logo.png" alt="Logo" class="logo-img" />
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
