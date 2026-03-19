<template>
  <el-card header="Rule Configuration">
    <el-input
      type="textarea"
      v-model="content"
      :rows="15"
      placeholder="YAML rules config..."
      style="font-family: monospace;"
    />
    <div style="margin-top: 12px;">
      <el-button type="primary" size="small" @click="save" :loading="saving">Save</el-button>
      <el-button size="small" @click="load">Reload</el-button>
    </div>
  </el-card>
</template>

<script>
import { getRules, updateRules } from '../api';

export default {
  name: 'RuleEditor',
  data() {
    return {
      content: '',
      saving: false,
    };
  },
  created() {
    this.load();
  },
  methods: {
    async load() {
      try {
        const res = await getRules();
        this.content = res.data.content;
      } catch (e) {
        this.$message.error('Failed to load rules');
      }
    },
    async save() {
      this.saving = true;
      try {
        const res = await updateRules(this.content);
        if (res.data.error) {
          this.$message.error(res.data.error);
        } else {
          this.$message.success('Rules saved');
        }
      } catch (e) {
        this.$message.error('Failed to save rules');
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>
