<template>
  <div id="app">
    <el-container>
      <el-header style="background: #409EFF; color: #fff; line-height: 60px; font-size: 20px; display: flex; align-items: center; justify-content: space-between;">
        <span>OrCAD Checklist Tool</span>
        <el-menu mode="horizontal" :default-active="activeTab" @select="activeTab = $event"
                 background-color="#409EFF" text-color="#fff" active-text-color="#ffd04b"
                 style="border: none;">
          <el-menu-item index="checker">Design Check</el-menu-item>
          <el-menu-item index="scripts">Script Market</el-menu-item>
          <el-menu-item index="ai">AI Assistant</el-menu-item>
          <el-menu-item index="knowledge">Knowledge Base</el-menu-item>
        </el-menu>
      </el-header>
      <el-main>

        <!-- Tab: Design Check -->
        <div v-show="activeTab === 'checker'">
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
        </div>

        <!-- Tab: Script Market -->
        <div v-show="activeTab === 'scripts'">
          <ScriptMarket />
        </div>

        <!-- Tab: AI Assistant -->
        <div v-show="activeTab === 'ai'">
          <AiChat />
        </div>

        <!-- Tab: Knowledge Base -->
        <div v-show="activeTab === 'knowledge'">
          <KnowledgeBase />
        </div>

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
import ScriptMarket from './components/ScriptMarket.vue';
import AiChat from './components/AiChat.vue';
import KnowledgeBase from './components/KnowledgeBase.vue';

export default {
  name: 'App',
  components: {
    FileUpload, CheckerSelector, ResultDashboard, AiSummary,
    ScriptMarket, AiChat, KnowledgeBase,
  },
  data() {
    return {
      activeTab: 'checker',
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
  padding: 0 20px;
}
.el-menu--horizontal > .el-menu-item {
  height: 60px;
  line-height: 60px;
}
</style>
