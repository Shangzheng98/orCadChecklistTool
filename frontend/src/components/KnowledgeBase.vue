<template>
  <el-card>
    <div slot="header" style="display: flex; justify-content: space-between; align-items: center;">
      <span>Knowledge Base</span>
      <el-button type="primary" size="small" @click="showCreate = true">+ Add Document</el-button>
    </div>

    <!-- Filters -->
    <el-row :gutter="12" style="margin-bottom: 16px;">
      <el-col :span="8">
        <el-select v-model="categoryFilter" clearable placeholder="Category" size="small" @change="load">
          <el-option label="API Reference" value="api" />
          <el-option label="Example" value="example" />
          <el-option label="Guide" value="guide" />
        </el-select>
      </el-col>
      <el-col :span="16">
        <el-input v-model="searchQuery" placeholder="Search knowledge base..." size="small" clearable @clear="load">
          <el-button slot="append" icon="el-icon-search" @click="load" />
        </el-input>
      </el-col>
    </el-row>

    <!-- Doc List -->
    <el-collapse>
      <el-collapse-item v-for="doc in docs" :key="doc.id" :name="doc.id">
        <template slot="title">
          <el-tag :type="categoryType(doc.category)" size="mini" style="margin-right: 8px;">
            {{ doc.category }}
          </el-tag>
          <strong>{{ doc.title }}</strong>
          <span v-for="tag in doc.tags" :key="tag"
                style="margin-left: 6px; color: #909399; font-size: 12px;">#{{ tag }}</span>
        </template>
        <pre style="white-space: pre-wrap; font-size: 13px; line-height: 1.6;">{{ doc.content }}</pre>
        <div style="margin-top: 8px;">
          <el-button size="mini" @click="editDoc(doc)">Edit</el-button>
          <el-button size="mini" type="danger" @click="removeDoc(doc)">Delete</el-button>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- Create/Edit Dialog -->
    <el-dialog :title="editing ? 'Edit Document' : 'New Document'" :visible.sync="showCreate" width="700px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="Title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="Category">
          <el-select v-model="form.category">
            <el-option label="API Reference" value="api" />
            <el-option label="Example" value="example" />
            <el-option label="Guide" value="guide" />
          </el-select>
        </el-form-item>
        <el-form-item label="Tags">
          <el-input v-model="tagsInput" placeholder="Comma-separated tags" />
        </el-form-item>
        <el-form-item label="Content">
          <el-input v-model="form.content" type="textarea" :rows="15" style="font-family: monospace;" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="showCreate = false">Cancel</el-button>
        <el-button type="primary" @click="save">{{ editing ? 'Update' : 'Create' }}</el-button>
      </div>
    </el-dialog>
  </el-card>
</template>

<script>
import { listDocs, createDoc, updateDoc, deleteDoc } from '../api/scripts';

export default {
  name: 'KnowledgeBase',
  data() {
    return {
      docs: [],
      categoryFilter: '',
      searchQuery: '',
      showCreate: false,
      editing: null,
      form: { title: '', category: 'api', content: '', tags: [] },
      tagsInput: '',
    };
  },
  created() {
    this.load();
  },
  methods: {
    async load() {
      try {
        const params = {};
        if (this.categoryFilter) params.category = this.categoryFilter;
        if (this.searchQuery) params.search = this.searchQuery;
        const res = await listDocs(params);
        this.docs = res.data;
      } catch (e) {
        this.$message.error('Failed to load knowledge base');
      }
    },
    async save() {
      const data = {
        ...this.form,
        tags: this.tagsInput.split(',').map(t => t.trim()).filter(Boolean),
      };
      try {
        if (this.editing) {
          await updateDoc(this.editing, data);
          this.$message.success('Updated');
        } else {
          await createDoc(data);
          this.$message.success('Created');
        }
        this.showCreate = false;
        this.editing = null;
        this.load();
      } catch (e) {
        this.$message.error('Failed to save');
      }
    },
    editDoc(doc) {
      this.editing = doc.id;
      this.form = { title: doc.title, category: doc.category, content: doc.content };
      this.tagsInput = (doc.tags || []).join(', ');
      this.showCreate = true;
    },
    async removeDoc(doc) {
      try {
        await this.$confirm('Delete this document?', 'Confirm');
        await deleteDoc(doc.id);
        this.load();
      } catch (e) {
        if (e !== 'cancel') this.$message.error('Failed to delete');
      }
    },
    categoryType(cat) {
      return { api: '', example: 'success', guide: 'warning' }[cat] || 'info';
    },
  },
};
</script>
