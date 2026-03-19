<template>
  <el-card header="AI Summary">
    <el-button
      type="primary"
      @click="generate"
      :loading="loading"
      :disabled="!!summary"
    >
      Generate AI Summary
    </el-button>
    <div v-if="error" style="color: #F56C6C; margin-top: 12px;">
      {{ error }}
    </div>
    <div v-if="summary" style="margin-top: 16px; white-space: pre-wrap; line-height: 1.8;">
      {{ summary }}
    </div>
  </el-card>
</template>

<script>
import { summarize } from '../api';

export default {
  name: 'AiSummary',
  props: {
    report: { type: Object, required: true },
  },
  data() {
    return {
      summary: '',
      error: '',
      loading: false,
    };
  },
  watch: {
    report() {
      this.summary = '';
      this.error = '';
    },
  },
  methods: {
    async generate() {
      this.loading = true;
      this.error = '';
      try {
        const reportJson = JSON.stringify(this.report);
        const res = await summarize(reportJson);
        if (res.data.error) {
          this.error = res.data.error;
        } else {
          this.summary = res.data.summary;
        }
      } catch (e) {
        this.error = 'Failed to generate summary: ' + e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
