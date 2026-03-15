<template>
  <div id="app">
    <el-container>
      <el-header style="background: #409EFF; color: #fff; line-height: 60px; font-size: 20px;">
        OrCAD Checklist Tool
      </el-header>
      <el-main>
        <el-row :gutter="20">
          <el-col :span="24">
            <FileUpload @file-selected="onFileSelected" />
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;" v-if="file">
          <el-col :span="24">
            <CheckerSelector
              :checkers="checkers"
              :selected="selectedCheckers"
              @update:selected="selectedCheckers = $event"
              @run="runChecks"
              :loading="loading"
            />
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;" v-if="report">
          <el-col :span="24">
            <ResultDashboard :report="report" />
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px;" v-if="report">
          <el-col :span="24">
            <AiSummary :report="report" />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { getCheckers, runCheck } from './api';
import FileUpload from './components/FileUpload.vue';
import CheckerSelector from './components/CheckerSelector.vue';
import ResultDashboard from './components/ResultDashboard.vue';
import AiSummary from './components/AiSummary.vue';

export default {
  name: 'App',
  components: { FileUpload, CheckerSelector, ResultDashboard, AiSummary },
  data() {
    return {
      file: null,
      checkers: [],
      selectedCheckers: [],
      report: null,
      loading: false,
    };
  },
  async created() {
    try {
      const res = await getCheckers();
      this.checkers = res.data;
      this.selectedCheckers = this.checkers.map(c => c.id);
    } catch (e) {
      this.$message.error('Failed to load checkers');
    }
  },
  methods: {
    onFileSelected(file) {
      this.file = file;
      this.report = null;
    },
    async runChecks() {
      if (!this.file) {
        this.$message.warning('Please upload a design JSON file first');
        return;
      }
      this.loading = true;
      try {
        const res = await runCheck(this.file, this.selectedCheckers);
        this.report = res.data;
      } catch (e) {
        this.$message.error('Check failed: ' + (e.response?.data?.detail || e.message));
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style>
#app {
  font-family: Helvetica, Arial, sans-serif;
}
.el-header {
  border-bottom: 2px solid #337ecc;
}
</style>
