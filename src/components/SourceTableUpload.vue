<template>
  <div class="source-table-upload">
    <h2 @click="toggleFileList">Import Source Tables</h2>
    <input type="file" @change="onFileChange" ref="fileInput"/>
    <div v-if="selectedFileName" class="file-name">Selected File: {{ selectedFileName }}</div>
    <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
    <div v-if="storedFiles.length">
      <h3 @click="toggleFileList">Select a File</h3>
      <div class="file-list" v-show="fileListVisible">
        <ul>
          <li v-for="(file, index) in storedFiles" :key="index" @click="selectFile(file)">
            {{ file.name }}
            <button @click.stop="removeFile(index)" class="remove-button">Remove</button>
          </li>
        </ul>
      </div>
    </div>
    <div v-if="tables.length">
      <h3 @click="toggleTableList">Select a Table</h3>
      <div class="table-list" v-show="tableListVisible">
        <ul>
          <li v-for="(table, index) in tables" :key="index" @click="selectTable(index)">
            {{ table.name }}
          </li>
        </ul>
      </div>
      <div v-if="selectedTable">
        <h3>Selected Table: {{ selectedTable.name }}</h3>
        <button @click="addTable">Add Table</button>
      </div>
    </div>
    <button class="recommend-button" @click="recommendSourceTables">Recommend Source Tables</button>
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    <div v-if="message" class="message">
      {{ message }}
    </div>
  </div>
</template>

<script>
import * as XLSX from 'xlsx';

export default {
  props: ['targetTable'],
  data() {
    return {
      tables: [],
      selectedTable: null,
      selectedFile: null,
      selectedFileName: '',
      errorMessage: '',
      storedFiles: [],
      fileListVisible: true,
      tableListVisible: true,
      loading: false,
      message: ''
    };
  },
  methods: {
    onFileChange(event) {
      const file = event.target.files[0];
      if (file) {
        this.selectedFileName = file.name;
        this.selectedFile = file;
        this.storeFile(file);
        this.parseFile(file);
      }
    },
    storeFile(file) {
      const existingFileIndex = this.storedFiles.findIndex(f => f.name === file.name);
      if (existingFileIndex === -1) {
        this.storedFiles.push(file);
      } else {
        this.storedFiles[existingFileIndex] = file;
      }
    },
    selectFile(file) {
      this.selectedFileName = file.name;
      this.selectedFile = file;
      this.parseFile(file);
    },
    parseFile(file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const data = e.target.result;
        let workbook;
        try {
          if (file.name.endsWith('.xlsx')) {
            workbook = XLSX.read(data, {type: 'binary'});
          } else if (file.name.endsWith('.json')) {
            workbook = {SheetNames: ['Sheet1'], Sheets: {Sheet1: JSON.parse(data)}};
          } else {
            throw new Error('Unsupported file format');
          }
          const newTables = workbook.SheetNames.map((name) => {
            const worksheet = workbook.Sheets[name];
            const headers = XLSX.utils.sheet_to_json(worksheet, {header: 1})[0];
            const comments = XLSX.utils.sheet_to_json(worksheet, {header: 1})[1];
            const fields = headers.map((header, index) => ({
              name: header,
              comment: comments ? comments[index] : ''
            }));
            return {name, fields, file};
          });
          this.tables = newTables;
          this.errorMessage = '';
        } catch (error) {
          this.errorMessage = `Error parsing file: ${error.message}`;
        }
      };
      reader.readAsBinaryString(file);
    },
    removeFile(index) {
      this.storedFiles.splice(index, 1);
      if (this.storedFiles.length === 0) {
        this.selectedFileName = '';
        this.selectedFile = null;
        this.tables = [];
        this.$refs.fileInput.value = ''; // 重置文件输入框的值
      }
    },
    selectTable(index) {
      this.selectedTable = this.tables[index];
    },
    addTable() {
      if (this.selectedTable) {
        const eventData = {
          name: this.selectedTable.name,
          fields: this.selectedTable.fields,
          update: false,
        };
        this.$emit('tableAdded', eventData);
        this.selectedTable = null;
        this.fileListVisible = false;
        this.tableListVisible = false;
      }
    },
    async recommendSourceTables() {
      this.loading = true;
      this.message = '';
      try {
        if (!this.selectedFile) {
          this.errorMessage = 'Please select a source file.';
          this.loading = false;
          return;
        }
        if (!this.targetTable) {
          this.errorMessage = 'Please select a target table.';
          this.loading = false;
          return;
        }

        const formData = new FormData();
        formData.append('source_file', this.selectedFile);
        formData.append('target_file', new Blob([JSON.stringify(this.targetTable)], {type: 'application/json'}));

        const response = await fetch('http://localhost:5000/api/recommend', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        if (data.error) {
          this.message = data.error;
        } else {
          this.importRecommendedTables(data);
          this.message = 'Source tables recommended successfully!';
        }
      } catch (error) {
        this.message = `API request failed: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    importRecommendedTables(recommendedTables) {
      recommendedTables.forEach(tableName => {
        const table = this.tables.find(t => t.name === tableName);
        if (table) {
          this.$parent.addSourceTable(table);
        } else {
          console.warn(`Table ${tableName} not found in the selected file.`);
        }
      });
    },

    toggleFileList() {
      this.fileListVisible = !this.fileListVisible;
    },
    toggleTableList() {
      this.tableListVisible = !this.tableListVisible;
    }
  }
};
</script>

<style scoped>
.source-table-upload {
  padding: 20px;
  font-size: 1em;
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid #ddd;
  border-radius: 10px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin: 20px;
}

.file-name, .error, .message {
  margin-top: 10px;
  font-weight: normal;
  text-align: center;
}

ul {
  list-style-type: none;
  padding: 0;
  margin: 10px 0;
  width: 100%;
}

li {
  cursor: pointer;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin: 5px 0;
  text-align: center;
}

li:hover {
  background-color: #f0f0f0;
}

.file-list, .table-list {
  max-height: 200px;
  overflow-y: auto;
  width: 100%;
  margin-top: 10px;
}

button, .recommend-button {
  margin: 10px;
  padding: 10px 20px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.remove-button {
  margin-left: 10px;
  padding: 2px 5px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.remove-button:hover {
  background-color: darkred;
}

button:hover, .recommend-button:hover {
  background-color: #45a049;
}

.loading {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
}

.spinner {
  border: 16px solid #f3f3f3;
  border-top: 16px solid #3498db;
  border-radius: 50%;
  width: 120px;
  height: 120px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
