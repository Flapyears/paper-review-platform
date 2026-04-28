<script setup>
import { computed, ref } from "vue";
import { requestJson } from "../../services/api";
import { setMustChangePassword } from "../../stores/auth";
import { notifyError, notifySuccess } from "../../stores/notice";

const props = defineProps({
  forceMode: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["success"]);

const loading = ref(false);
const form = ref({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const buttonLabel = computed(() => (loading.value ? "提交中..." : "更新密码"));

function resetForm() {
  form.value.oldPassword = "";
  form.value.newPassword = "";
  form.value.confirmPassword = "";
}

async function submit() {
  if (loading.value) return;
  if (!form.value.oldPassword.trim()) {
    notifyError("请输入当前密码");
    return;
  }
  if (form.value.newPassword.length < 6) {
    notifyError("新密码至少 6 位");
    return;
  }
  if (form.value.newPassword !== form.value.confirmPassword) {
    notifyError("两次输入的新密码不一致");
    return;
  }

  loading.value = true;
  try {
    await requestJson("/api/auth/change-password", "POST", {
      old_password: form.value.oldPassword,
      new_password: form.value.newPassword,
    });
    setMustChangePassword(false);
    notifySuccess(props.forceMode ? "密码已更新，请继续使用系统" : "密码已更新");
    resetForm();
    emit("success");
  } catch (err) {
    notifyError(err.message || String(err));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="modal-stack">
    <div v-if="props.forceMode" class="state-note warning">
      <strong>请先修改默认密码</strong>
      <p>当前账号使用的是初始密码。修改完成后，才能继续使用系统。</p>
    </div>

    <div class="form-grid single">
      <label>
        当前密码
        <input v-model="form.oldPassword" type="password" placeholder="请输入当前密码" />
      </label>
      <label>
        新密码
        <input v-model="form.newPassword" type="password" placeholder="至少 6 位" />
      </label>
      <label>
        确认新密码
        <input v-model="form.confirmPassword" type="password" placeholder="请再次输入新密码" />
      </label>
    </div>

    <div class="row-actions">
      <button class="accent" :disabled="loading" @click="submit">{{ buttonLabel }}</button>
    </div>
  </div>
</template>
