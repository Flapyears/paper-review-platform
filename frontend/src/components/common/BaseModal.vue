<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: "",
  },
  width: {
    type: String,
    default: "680px",
  },
  closable: {
    type: Boolean,
    default: true,
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

function close() {
  emit("update:modelValue", false);
}

function onBackdropClick(event) {
  if (props.closeOnBackdrop && event.target === event.currentTarget) {
    close();
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="props.modelValue" class="modal-overlay" @click="onBackdropClick">
      <section class="modal-panel" :style="{ width: props.width }">
        <header class="modal-head">
          <h4>{{ props.title }}</h4>
          <button v-if="props.closable" class="ghost modal-close" @click="close">关闭</button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal-foot">
          <slot name="footer" />
        </footer>
      </section>
    </div>
  </Teleport>
</template>
