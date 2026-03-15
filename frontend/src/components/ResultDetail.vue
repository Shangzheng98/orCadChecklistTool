<template>
  <div>
    <ul style="margin: 0; padding-left: 20px;">
      <li v-for="(finding, idx) in findings" :key="idx" style="margin-bottom: 4px;">
        <span>{{ finding.message }}</span>
        <el-tag v-if="finding.refdes" size="mini" style="margin-left: 4px;">{{ finding.refdes }}</el-tag>
        <el-tag v-if="finding.page" size="mini" type="info" style="margin-left: 4px;">{{ finding.page }}</el-tag>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'ResultDetail',
  props: {
    findings: { type: Array, default: () => [] },
  },
};
</script>
