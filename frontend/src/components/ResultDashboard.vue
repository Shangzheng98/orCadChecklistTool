<template>
  <el-card header="Check Results">
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="6">
        <el-statistic title="Total Checks" :value="report.summary.total_checks" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Passed" :value="report.summary.passed" style="color: #67C23A;" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Errors" :value="report.summary.errors" style="color: #F56C6C;" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Warnings" :value="report.summary.warnings" style="color: #E6A23C;" />
      </el-col>
    </el-row>

    <el-collapse>
      <el-collapse-item
        v-for="result in report.results"
        :key="result.rule_id"
        :name="result.rule_id"
      >
        <template slot="title">
          <el-tag :type="statusType(result)" size="small" style="margin-right: 8px;">
            {{ result.status }}
          </el-tag>
          <el-tag :type="severityType(result.severity)" size="mini" style="margin-right: 8px;">
            {{ result.severity }}
          </el-tag>
          <span>{{ result.rule_name || result.rule_id }}</span>
          <el-badge
            v-if="result.findings.length"
            :value="result.findings.length"
            style="margin-left: 8px;"
          />
        </template>
        <div v-if="result.findings.length === 0" style="color: #67C23A;">
          No issues found.
        </div>
        <ul v-else style="margin: 0; padding-left: 20px;">
          <li v-for="(finding, idx) in result.findings" :key="idx" style="margin-bottom: 4px;">
            {{ finding.message }}
            <span v-if="finding.page" style="color: #909399;"> ({{ finding.page }})</span>
          </li>
        </ul>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script>
export default {
  name: 'ResultDashboard',
  props: {
    report: { type: Object, required: true },
  },
  methods: {
    statusType(result) {
      return result.status === 'PASS' ? 'success' : 'danger';
    },
    severityType(severity) {
      const map = { ERROR: 'danger', WARNING: 'warning', INFO: 'info' };
      return map[severity] || 'info';
    },
  },
};
</script>
