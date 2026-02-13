<template>
  <section class="panel-card">
    <h3>系统总览</h3>
    <p class="muted">
      当前前端基于 Vue 3 + Vue Router，已对接后端所有核心接口。建议流程：
      学生创建并提交论文 -> 管理员分配任务 -> 评阅教师保存并提交评阅。
    </p>
    <div class="summary-grid">
      <article>
        <h4>学生端</h4>
        <p>论文创建、终稿上传、送审提交。</p>
      </article>
      <article>
        <h4>管理员端</h4>
        <p>待分配列表、任务分配、替换取消、重评退回。</p>
      </article>
      <article>
        <h4>评阅端</h4>
        <p>任务查询、下载论文、评阅草稿与最终提交。</p>
      </article>
    </div>
  </section>
</template>
