<template>
  <el-card header="Select Checkers">
    <div style="margin-bottom: 12px;">
      <el-button size="small" @click="selectAll">Select All</el-button>
      <el-button size="small" @click="selectNone">Deselect All</el-button>
    </div>
    <el-checkbox-group :value="selected" @input="$emit('update:selected', $event)">
      <el-checkbox
        v-for="checker in checkers"
        :key="checker.id"
        :label="checker.id"
        style="display: block; margin-bottom: 8px;"
      >
        <el-tag :type="severityType(checker.default_severity)" size="mini">
          {{ checker.default_severity }}
        </el-tag>
        <strong>{{ checker.name }}</strong>
        <span style="color: #909399; margin-left: 8px;">{{ checker.description }}</span>
      </el-checkbox>
    </el-checkbox-group>
    <div style="margin-top: 16px;">
      <el-button type="primary" @click="$emit('run')" :loading="loading">
        Run Checks
      </el-button>
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'CheckerSelector',
  props: {
    checkers: { type: Array, default: () => [] },
    selected: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
  methods: {
    selectAll() {
      this.$emit('update:selected', this.checkers.map(c => c.id));
    },
    selectNone() {
      this.$emit('update:selected', []);
    },
    severityType(severity) {
      const map = { ERROR: 'danger', WARNING: 'warning', INFO: 'info' };
      return map[severity] || 'info';
    },
  },
};
</script>
