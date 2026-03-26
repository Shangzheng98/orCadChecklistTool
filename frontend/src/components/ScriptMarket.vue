<template>
  <el-card>
    <div slot="header" style="display: flex; justify-content: space-between; align-items: center;">
      <span>Script Market</span>
      <el-button type="primary" size="small" @click="showCreate = true">
        + New Script
      </el-button>
    </div>

    <!-- Filters -->
    <el-row :gutter="12" style="margin-bottom: 16px;">
      <el-col :span="6">
        <el-select v-model="filters.status" clearable placeholder="Status" size="small" @change="load">
          <el-option label="Draft" value="draft" />
          <el-option label="Published" value="published" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filters.category" clearable placeholder="Category" size="small" @change="load">
          <el-option label="Extraction" value="extraction" />
          <el-option label="Validation" value="validation" />
          <el-option label="Automation" value="automation" />
          <el-option label="Utility" value="utility" />
          <el-option label="Custom" value="custom" />
        </el-select>
      </el-col>
      <el-col :span="12">
        <el-input v-model="filters.search" placeholder="Search scripts..." size="small" clearable @clear="load">
          <el-button slot="append" icon="el-icon-search" @click="load" />
        </el-input>
      </el-col>
    </el-row>

    <!-- Script List -->
    <el-table :data="scripts" style="width: 100%;" @row-click="selectScript">
      <el-table-column prop="name" label="Name" width="200" />
      <el-table-column prop="version" label="Version" width="80" />
      <el-table-column prop="category" label="Category" width="120">
        <template slot-scope="scope">
          <el-tag size="mini">{{ scope.row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="100">
        <template slot-scope="scope">
          <el-tag :type="scope.row.status === 'published' ? 'success' : 'info'" size="mini">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="author" label="Author" width="120" />
      <el-table-column prop="description" label="Description" />
      <el-table-column label="Actions" width="180">
        <template slot-scope="scope">
          <el-button size="mini" @click.stop="viewScript(scope.row)">View</el-button>
          <el-button size="mini" type="success" @click.stop="publish(scope.row)"
                     v-if="scope.row.status === 'draft'">Publish</el-button>
          <el-button size="mini" type="danger" @click.stop="remove(scope.row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Dialog -->
    <el-dialog title="New Script" :visible.sync="showCreate" width="600px">
      <el-form :model="newScript" label-width="100px">
        <el-form-item label="Name">
          <el-input v-model="newScript.name" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="newScript.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Category">
          <el-select v-model="newScript.category">
            <el-option label="Extraction" value="extraction" />
            <el-option label="Validation" value="validation" />
            <el-option label="Automation" value="automation" />
            <el-option label="Utility" value="utility" />
            <el-option label="Custom" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="Author">
          <el-input v-model="newScript.author" />
        </el-form-item>
        <el-form-item label="TCL Code">
          <el-input v-model="newScript.code" type="textarea" :rows="12"
                    style="font-family: monospace;" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="showCreate = false">Cancel</el-button>
        <el-button type="primary" @click="create">Create</el-button>
      </div>
    </el-dialog>

    <!-- View Dialog -->
    <el-dialog :title="viewingScript ? viewingScript.meta.name : ''" :visible.sync="showView" width="700px">
      <div v-if="viewingScript">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="ID">{{ viewingScript.meta.id }}</el-descriptions-item>
          <el-descriptions-item label="Version">{{ viewingScript.meta.version }}</el-descriptions-item>
          <el-descriptions-item label="Category">{{ viewingScript.meta.category }}</el-descriptions-item>
          <el-descriptions-item label="Status">{{ viewingScript.meta.status }}</el-descriptions-item>
          <el-descriptions-item label="Author">{{ viewingScript.meta.author }}</el-descriptions-item>
          <el-descriptions-item label="Checksum">{{ viewingScript.meta.checksum }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 16px;">
          <strong>Code:</strong>
          <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px; overflow-x: auto; max-height: 400px;">{{ viewingScript.code }}</pre>
        </div>
      </div>
    </el-dialog>
  </el-card>
</template>

<script>
import { listScripts, createScript, deleteScript, publishScript, getScript } from '../api/scripts';

export default {
  name: 'ScriptMarket',
  data() {
    return {
      scripts: [],
      filters: { status: '', category: '', search: '' },
      showCreate: false,
      showView: false,
      viewingScript: null,
      newScript: {
        name: '', description: '', category: 'custom', author: '', code: '',
      },
    };
  },
  created() {
    this.load();
  },
  methods: {
    async load() {
      try {
        const params = {};
        if (this.filters.status) params.status = this.filters.status;
        if (this.filters.category) params.category = this.filters.category;
        if (this.filters.search) params.search = this.filters.search;
        const res = await listScripts(params);
        this.scripts = res.data;
      } catch (e) {
        this.$message.error('Failed to load scripts');
      }
    },
    async create() {
      try {
        await createScript(this.newScript);
        this.showCreate = false;
        this.newScript = { name: '', description: '', category: 'custom', author: '', code: '' };
        this.load();
        this.$message.success('Script created');
      } catch (e) {
        this.$message.error('Failed to create script');
      }
    },
    async viewScript(row) {
      try {
        const res = await getScript(row.id);
        this.viewingScript = res.data;
        this.showView = true;
      } catch (e) {
        this.$message.error('Failed to load script');
      }
    },
    selectScript() {},
    async publish(row) {
      try {
        await publishScript(row.id);
        this.load();
        this.$message.success('Script published');
      } catch (e) {
        this.$message.error('Failed to publish');
      }
    },
    async remove(row) {
      try {
        await this.$confirm('Delete this script?', 'Confirm');
        await deleteScript(row.id);
        this.load();
        this.$message.success('Deleted');
      } catch (e) {
        if (e !== 'cancel') this.$message.error('Failed to delete');
      }
    },
  },
};
</script>
