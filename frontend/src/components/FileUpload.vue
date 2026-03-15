<template>
  <el-card header="Upload Design JSON">
    <el-upload
      drag
      action=""
      :auto-upload="false"
      :on-change="handleChange"
      :limit="1"
      :on-exceed="handleExceed"
      accept=".json"
    >
      <i class="el-icon-upload"></i>
      <div class="el-upload__text">Drop JSON file here or <em>click to upload</em></div>
    </el-upload>
  </el-card>
</template>

<script>
export default {
  name: 'FileUpload',
  methods: {
    handleChange(file) {
      this.$emit('file-selected', file.raw);
    },
    handleExceed() {
      this.$message.warning('Only one file at a time');
    },
  },
};
</script>
