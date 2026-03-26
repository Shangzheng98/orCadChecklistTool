<template>
  <el-card>
    <div slot="header" style="display: flex; justify-content: space-between; align-items: center;">
      <span>AI TCL Assistant</span>
      <el-button size="small" @click="clearSession">New Session</el-button>
    </div>

    <!-- Chat Messages -->
    <div ref="chatBox" class="chat-box">
      <div v-for="(msg, idx) in messages" :key="idx"
           :class="['chat-msg', msg.role === 'user' ? 'chat-user' : 'chat-assistant']">
        <div class="chat-role">{{ msg.role === 'user' ? 'You' : 'AI' }}</div>
        <div class="chat-content" v-html="formatMessage(msg.content)"></div>
      </div>
      <div v-if="loading" class="chat-msg chat-assistant">
        <div class="chat-role">AI</div>
        <div class="chat-content"><i class="el-icon-loading"></i> Thinking...</div>
      </div>
    </div>

    <!-- Input -->
    <div style="margin-top: 12px; display: flex; gap: 8px;">
      <el-input
        v-model="input"
        placeholder="Describe what TCL script you need..."
        @keyup.enter.native="send"
        :disabled="loading"
      />
      <el-button type="primary" @click="send" :loading="loading">Send</el-button>
    </div>

    <!-- Save extracted code -->
    <div v-if="extractedCode" style="margin-top: 16px;">
      <el-divider>Generated TCL Code</el-divider>
      <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px; max-height: 300px; overflow: auto;">{{ extractedCode }}</pre>
      <div style="margin-top: 8px; display: flex; gap: 8px;">
        <el-input v-model="saveName" placeholder="Script name" size="small" style="width: 200px;" />
        <el-button type="success" size="small" @click="saveScript">Save to Script Market</el-button>
        <el-button size="small" @click="copyCode">Copy Code</el-button>
      </div>
    </div>
  </el-card>
</template>

<script>
import { agentChat, saveGeneratedScript } from '../api/scripts';

export default {
  name: 'AiChat',
  data() {
    return {
      sessionId: '',
      messages: [],
      input: '',
      loading: false,
      extractedCode: '',
      saveName: '',
    };
  },
  methods: {
    async send() {
      if (!this.input.trim()) return;

      const userMsg = this.input.trim();
      this.messages.push({ role: 'user', content: userMsg });
      this.input = '';
      this.loading = true;

      try {
        const res = await agentChat(this.sessionId, userMsg);
        const data = res.data;
        this.sessionId = data.session_id;
        this.messages.push({ role: 'assistant', content: data.reply });
        if (data.extracted_code) {
          this.extractedCode = data.extracted_code;
        }
      } catch (e) {
        this.messages.push({ role: 'assistant', content: 'Error: ' + e.message });
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          const box = this.$refs.chatBox;
          if (box) box.scrollTop = box.scrollHeight;
        });
      }
    },
    async saveScript() {
      if (!this.saveName.trim()) {
        this.$message.warning('Please enter a script name');
        return;
      }
      try {
        await saveGeneratedScript({
          session_id: this.sessionId,
          name: this.saveName,
          code: this.extractedCode,
          category: 'custom',
        });
        this.$message.success('Script saved to market');
        this.saveName = '';
      } catch (e) {
        this.$message.error('Failed to save script');
      }
    },
    copyCode() {
      navigator.clipboard.writeText(this.extractedCode).then(() => {
        this.$message.success('Copied to clipboard');
      });
    },
    clearSession() {
      this.sessionId = '';
      this.messages = [];
      this.extractedCode = '';
    },
    formatMessage(content) {
      // Simple code block highlighting
      return content
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/```tcl\n([\s\S]*?)```/g, '<pre style="background:#2d2d2d;color:#f8f8f2;padding:12px;border-radius:4px;overflow-x:auto;">$1</pre>')
        .replace(/```\n?([\s\S]*?)```/g, '<pre style="background:#f5f7fa;padding:12px;border-radius:4px;">$1</pre>')
        .replace(/`([^`]+)`/g, '<code style="background:#f0f0f0;padding:2px 4px;border-radius:2px;">$1</code>')
        .replace(/\n/g, '<br>');
    },
  },
};
</script>

<style scoped>
.chat-box {
  height: 400px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}
.chat-msg {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 85%;
}
.chat-user {
  background: #ecf5ff;
  margin-left: auto;
  text-align: right;
}
.chat-assistant {
  background: #fff;
  border: 1px solid #e4e7ed;
}
.chat-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.chat-content {
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
}
</style>
