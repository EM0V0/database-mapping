<template>
  <div class="mapping-tool">
    <h1>Database Mapping Tool</h1>
    <div class="main-content">
      <div class="tables">
        <div class="source-tables" ref="sourceTablesContainer" @scroll="onScroll">
          <SourceTableUpload @tableAdded="addSourceTable" :targetTable="selectedTargetTable"/>
          <input type="text" v-model="sourceSearch" placeholder="Search Source Fields"/>
          <div v-for="(table, index) in sourceTables" :key="table.name" class="table-chunk"
               :ref="'sourceTable' + index">
            <h3 @click="toggleTable(index, 'source')">
              {{ table.name }}
              <button @click="removeSourceTable(index)">Remove</button>
            </h3>
            <div v-show="!collapsedSourceTables[index]" class="field-list">
              <TableComponent :table="table" :search="sourceSearch" :fieldMappings="fieldMappings"
                              @fieldDragged="onFieldDragged" @fieldDropped="onFieldDropped"
                              @dragging="updateLines" @fieldDoubleClicked="onFieldDoubleClicked"/>
            </div>
          </div>
        </div>
        <div class="target-tables" ref="targetTablesContainer" @scroll="onScroll">
          <TargetTableUpload @tableAdded="addTargetTable" @targetTableSelected="setSelectedTargetTable"/>
          <div v-for="(block, blockIndex) in targetTableBlocks" :key="block.name" class="table-block"
               :ref="'targetTable' + blockIndex">
            <h3 @click="toggleTable(blockIndex, 'target')">
              {{ block.name }}
              <button @click="removeTargetTable(blockIndex)">Remove</button>
            </h3>
            <div v-show="!collapsedBlocks[blockIndex]" class="field-list">
              <TableComponent :table="block" :search="targetSearch" :fieldMappings="fieldMappings"
                              @fieldDragged="onFieldDragged" @fieldDropped="onFieldDropped"
                              @dragging="updateLines" @fieldDoubleClicked="onFieldDoubleClicked"/>
            </div>
          </div>
        </div>
      </div>
      <svg id="lines"></svg>
      <div class="mappings">
        <h2>Field Mappings</h2>
        <div class="mappings-table-wrapper">
          <button @click="exportMappings">Export Mappings</button>
          <input type="file" @change="importMappings" style="display:none" ref="fileInput">
          <button @click="triggerFileInput">Import Mappings</button>
          <button @click="recommendFieldMappings">Recommend Field Mappings</button>
          <button @click="generateSQL">Generate SQL</button>
          <div class="table-container">
            <table>
              <thead>
              <tr>
                <th>Source Field</th>
                <th>Source Table</th>
                <th>Target Field</th>
                <th>Target Table</th>
                <th>Transformation Rule</th>
                <th>Action</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="(mapping, index) in fieldMappings" :key="index"
                  :class="{'highlight': isFieldHighlighted(mapping)}">
                <td>{{ mapping.source.field }}</td>
                <td>{{ mapping.source.table.name }}</td>
                <td>{{ mapping.target.field }}</td>
                <td>{{ mapping.target.table.name }}</td>
                <td>
                  <input v-model="mapping.transformationRule" placeholder="Enter transformation rule"/>
                </td>
                <td>
                  <button @click="removeMapping(index)">Remove</button>
                </td>
              </tr>
              </tbody>
            </table>
          </div>
          <div v-if="generatedSQL" class="sql-result">
            <h3>Generated SQL:</h3>
            <pre>{{ generatedSQL }}</pre>
          </div>
        </div>
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>
        <div v-if="message" class="message">
          {{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import TableComponent from './TableComponent.vue';
import SourceTableUpload from './SourceTableUpload.vue';
import TargetTableUpload from './TargetTableUpload.vue';
import * as d3 from 'd3';

export default {
  components: {
    TableComponent,
    SourceTableUpload,
    TargetTableUpload
  },
  data() {
    return {
      sourceTables: [],
      targetTableBlocks: [],
      collapsedBlocks: [],
      collapsedSourceTables: [],
      fieldMappings: [],
      highlightedField: null,
      sourceSearch: '',
      targetSearch: '',
      draggedField: null,
      isScrolling: false,
      updateInterval: null,
      imported: false,
      selectedTargetTable: null,
      generatedSQL: '',
      loading: false,
      message: ''
    };
  },
  methods: {
    addSourceTable(tableData) {
      this.addTable(tableData, 'source');
    },
    addTargetTable(tableData) {
      this.addTable(tableData, 'target');
    },
    addTable(tableData, type) {
      const tables = type === 'source' ? this.sourceTables : this.targetTableBlocks;
      const collapsedTables = type === 'source' ? this.collapsedSourceTables : this.collapsedBlocks;
      const existingTableIndex = tables.findIndex(table => table.name === tableData.name);
      if (existingTableIndex === -1) {
        tables.push({
          name: tableData.name,
          fields: tableData.fields,
        });
        collapsedTables.push(false);
      } else {
        const existingFields = tables[existingTableIndex].fields.map(field => field.name);
        tableData.fields.forEach(field => {
          if (!existingFields.includes(field.name)) {
            tables[existingTableIndex].fields.push(field);
          }
        });
      }
      this.$nextTick(this.updateLines);
    },
    setSelectedTargetTable(table) {
      this.selectedTargetTable = table;
    },
    removeSourceTable(index) {
      this.removeTable(index, 'source');
    },
    removeTargetTable(index) {
      this.removeTable(index, 'target');
    },
    removeTable(index, type) {
      const tables = type === 'source' ? this.sourceTables : this.targetTableBlocks;
      const collapsedTables = type === 'source' ? this.collapsedSourceTables : this.collapsedBlocks;
      const removedTable = tables.splice(index, 1)[0];
      collapsedTables.splice(index, 1);
      if (type === 'target') {
        this.fieldMappings = this.fieldMappings.filter(mapping => mapping.target.table.name !== removedTable.name);
      }
      this.$nextTick(this.updateLines);
    },
    toggleTable(index, type) {
      if (type === 'source') {
        this.collapsedSourceTables.splice(index, 1, !this.collapsedSourceTables[index]);
      } else {
        this.collapsedBlocks.splice(index, 1, !this.collapsedBlocks[index]);
      }
      this.$nextTick(this.updateLines);
    },
    onFieldDragged(field, table) {
      this.draggedField = {field, table};
    },
    onFieldDropped(targetField, targetTable) {
      if (this.draggedField && targetField) {
        const mappingExists = this.fieldMappings.some(mapping =>
            mapping.source.field === this.draggedField.field &&
            mapping.source.table.name === this.draggedField.table.name &&
            mapping.target.field === targetField &&
            mapping.target.table.name === targetTable.name
        );

        if (!mappingExists) {
          if (this.isSourceTable(this.draggedField.table.name) && this.isTargetTable(targetTable.name)) {
            this.fieldMappings.push({
              source: {field: this.draggedField.field, table: this.draggedField.table},
              target: {field: targetField, table: targetTable},
              transformationRule: ''
            });
            this.draggedField = null;
            this.updateLines();
          }
        }
      }
    },
    removeMapping(index) {
      this.fieldMappings.splice(index, 1);
      this.updateLines();
    },
    exportMappings() {
      const mappings = this.fieldMappings.map(mapping => ({
        sourceField: mapping.source.field,
        sourceTable: mapping.source.table.name,
        targetField: mapping.target.field,
        targetTable: mapping.target.table.name,
        transformationRule: mapping.transformationRule || ''
      }));
      const dataStr = JSON.stringify(mappings, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
      const exportFileDefaultName = 'mappings.json';

      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    },
    collectSourceTables() {
      const sourceData = this.sourceTables.map(table => {
        return {
          name: table.name,
          fields: table.fields
        };
      });

      return new Blob([JSON.stringify(sourceData)], {type: 'application/json'});
    },

    async recommendFieldMappings() {
      this.loading = true;
      this.message = '';
      try {
        if (this.sourceTables.length === 0 || !this.selectedTargetTable) {
          this.message = 'Please make sure to import source tables and select a target table first.';
          this.loading = false;
          return;
        }

        const formData = new FormData();
        formData.append('source_file', this.collectSourceTables());
        formData.append('target_file', new Blob([JSON.stringify(this.selectedTargetTable)], {type: 'application/json'}));

        const response = await fetch('http://localhost:5000/api/recommend_fields', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        if (data.error) {
          this.message = data.error;
        } else {
          this.loadFieldMappings(data);
          this.message = 'Field mappings recommended successfully!';
          this.setAutoHideMessage();
        }
      } catch (error) {
        this.message = `API request failed: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    async generateSQL() {
      this.loading = true;
      this.message = '';
      try {
        const response = await fetch('http://localhost:5000/api/generate_sql', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.fieldMappings)
        });
        const data = await response.json();
        if (data.error) {
          this.message = data.error;
        } else {
          this.generatedSQL = data.sql;
          this.message = 'SQL generated successfully!';
          this.setAutoHideMessage();
        }
      } catch (error) {
        this.message = `API request failed: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    async recommendSourceTables(targetTable) {
      this.loading = true;
      this.message = '';
      try {
        const formData = new FormData();
        formData.append('source_file', this.collectSourceTables());
        formData.append('target_file', new Blob([JSON.stringify(targetTable)], {type: 'application/json'}));

        const response = await fetch('http://localhost:5000/api/recommend', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        if (data.error) {
          this.message = data.error;
        } else {
          this.loadSourceTables(data);
          this.message = 'Source tables recommended successfully!';
          this.setAutoHideMessage();
        }
      } catch (error) {
        this.message = `API request failed: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    loadFieldMappings(mappings) {
      mappings.forEach(mapping => {
        const sourceTable = this.sourceTables.find(table => table.name === mapping.sourceTable);
        const targetTable = this.targetTableBlocks.find(block => block.name === mapping.targetTable);

        if (sourceTable && targetTable) {
          this.fieldMappings.push({
            source: {field: mapping.sourceField, table: sourceTable},
            target: {field: mapping.targetField, table: targetTable},
            transformationRule: '',
            action: 'remove'
          });
        }
      });

      this.updateLines();
    },
    loadSourceTables(tables) {
      tables.forEach(table => {
        this.addSourceTable(table);
      });
    },
    triggerFileInput() {
      this.$refs.fileInput.click();
    },
    importMappings(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const mappings = JSON.parse(e.target.result);
            this.loadMappings(mappings);
            this.imported = true;
            this.$nextTick(this.updateLines);
          } catch (error) {
            console.error('Error loading mappings:', error);
          }
        };
        reader.readAsText(file);
      }
    },
    loadMappings(mappings) {
      const newSourceTables = [];
      const newTargetTables = [];

      mappings.forEach(mapping => {
        if (!newSourceTables.some(table => table.name === mapping.sourceTable)) {
          const sourceTable = {
            name: mapping.sourceTable,
            fields: []
          };
          newSourceTables.push(sourceTable);
        }

        if (!newTargetTables.some(table => table.name === mapping.targetTable)) {
          const targetTable = {
            name: mapping.targetTable,
            fields: []
          };
          newTargetTables.push(targetTable);
        }

        newSourceTables.find(table => table.name === mapping.sourceTable).fields.push({name: mapping.sourceField});
        newTargetTables.find(table => table.name === mapping.targetTable).fields.push({name: mapping.targetField});
      });

      this.sourceTables = newSourceTables;
      this.targetTableBlocks = newTargetTables;

      this.fieldMappings = mappings.map(mapping => ({
        source: {field: mapping.sourceField, table: {name: mapping.sourceTable}},
        target: {field: mapping.targetField, table: {name: mapping.targetTable}},
        transformationRule: mapping.transformationRule || ''
      }));
    },
    updateLines() {
      const svg = d3.select("#lines");
      svg.selectAll("*").remove();

      this.fieldMappings.forEach(mapping => {
        const sourceTableIndex = this.sourceTables.findIndex(table => table.name === mapping.source.table.name);
        const targetTableIndex = this.targetTableBlocks.findIndex(block => block.name === mapping.target.table.name);

        if (sourceTableIndex !== -1 && targetTableIndex !== -1) {
          const sourceElement = this.findFieldElement(mapping.source.field, mapping.source.table.name, '.source-tables');
          const targetElement = this.findFieldElement(mapping.target.field, mapping.target.table.name, '.target-tables');

          if (sourceElement && targetElement) {
            const sourceRect = sourceElement.getBoundingClientRect();
            const targetRect = targetElement.getBoundingClientRect();

            const sourceContainer = this.$refs['sourceTable' + sourceTableIndex][0]?.getBoundingClientRect();
            const targetContainer = this.$refs['targetTable' + targetTableIndex][0]?.getBoundingClientRect();

            if (sourceContainer && targetContainer) {
              const scrollX = window.scrollX || document.documentElement.scrollLeft;

              const containerRect = document.querySelector(".mapping-tool").getBoundingClientRect();
              const sourceX = sourceRect.right + scrollX;
              const sourceY = sourceRect.top + sourceRect.height / 2 - containerRect.top;
              const targetX = targetRect.left + scrollX;
              const targetY = targetRect.top + (targetRect.height / 2) - containerRect.top;

              const controlPointX1 = sourceX + (targetX - sourceX) / 3;
              const controlPointX2 = sourceX + 2 * (targetX - sourceX) / 3;

              if (this.isInVisibleRange(sourceRect, sourceContainer, '.source-tables') &&
                  this.isInVisibleRange(targetRect, targetContainer, '.target-tables')) {
                svg.append("path")
                    .attr("d", `M${sourceX},${sourceY} C${controlPointX1},${sourceY} ${controlPointX2},${targetY} ${targetX},${targetY}`)
                    .attr("stroke", "red")
                    .attr("fill", "none")
                    .attr("stroke-width", 2);
              }
            }
          }
        }
      });
    },

    isInVisibleRange(elementRect, containerRect, containerSelector) {
      const container = document.querySelector(containerSelector);
      if (!container) {
        return false;
      }

      const containerVisibleRect = container.getBoundingClientRect();
      return (
          elementRect &&
          containerRect &&
          elementRect.top >= containerVisibleRect.top &&
          elementRect.bottom <= containerVisibleRect.bottom &&
          elementRect.left >= containerVisibleRect.left &&
          elementRect.right <= containerVisibleRect.right &&
          elementRect.top >= containerRect.top &&
          elementRect.bottom <= containerRect.bottom &&
          elementRect.left >= containerRect.left &&
          elementRect.right <= containerRect.right
      );
    },
    findFieldElement(field, tableName, containerSelector) {
      const container = document.querySelector(containerSelector);
      if (!container) {
        return null;
      }
      const elements = Array.from(container.querySelectorAll('li.field-item'));
      return elements.find(li => li.getAttribute('data-field') === field && li.getAttribute('data-table') === tableName);
    },
    isSourceTable(name) {
      return this.sourceTables.some(table => table.name === name);
    },
    isTargetTable(name) {
      return this.targetTableBlocks.some(block => block.name === name);
    },
    onFieldDoubleClicked(field, table) {
      if (this.highlightedField && this.highlightedField.field === field && this.highlightedField.table === table) {
        this.highlightedField = null;
      } else {
        this.highlightedField = {field, table};
      }
    },
    setAutoHideMessage() {
        setTimeout(() => {
            this.message = '';
        }, 5000); // 5000 毫秒（5 秒）后隐藏消息
    },
    isFieldHighlighted(mapping) {
      if (!this.highlightedField) return false;
      return (mapping.source.field === this.highlightedField.field && mapping.source.table.name === this.highlightedField.table) ||
          (mapping.target.field === this.highlightedField.field && mapping.target.table.name === this.highlightedField.table);
    },
    debounce(func, wait) {
      let timeout;
      return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    },
    onScroll() {
      if (!this.isScrolling) {
        this.isScrolling = true;
        requestAnimationFrame(() => {
          this.updateLines();
          this.isScrolling = false;
        });
      }
    }
  },

  mounted() {
    this.collapsedBlocks = this.targetTableBlocks.map(() => true);
    this.debouncedUpdateLines = this.debounce(this.updateLines, 100);
    this.updateLines();
    window.addEventListener('resize', this.debouncedUpdateLines);
    this.$refs.sourceTablesContainer.addEventListener('scroll', this.onScroll);
    this.$refs.targetTablesContainer.addEventListener('scroll', this.onScroll);
    this.updateInterval = setInterval(this.updateLines, 100);
  },
  updated() {
    this.updateLines();
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.debouncedUpdateLines);
    this.$refs.sourceTablesContainer.removeEventListener('scroll', this.onScroll);
    this.$refs.targetTablesContainer.removeEventListener('scroll');
    clearInterval(this.updateInterval);
  }
};
</script>

<style scoped>
.mapping-tool {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  margin: 20px;  /* 增加外边距 */
}

.main-content {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 20px;  /* 增加间隔距离 */
}

.tables {
  display: flex;
  justify-content: space-around;
  width: 70%;
  position: relative;
  gap: 20px;  /* 增加表格之间的间隔 */
}

.source-tables, .target-tables {
  width: 45%;
  overflow-y: auto;
  height: calc(100vh - 200px);
}

.mappings {
  width: 25%;
  margin-top: 20px;
  overflow-y: auto;
  max-height: 80vh;
  padding-left: 10px;
}

.mappings h2 {
  margin-top: 0;
}

button {
  margin: 10px;  /* 调整按钮之间的间距 */
  padding: 10px 20px;  /* 调整按钮的内边距，使其更大更美观 */
  background-color: #4CAF50; /* 修改按钮背景颜色 */
  color: white;  /* 按钮文字颜色 */
  border: none;  /* 去除按钮边框 */
  border-radius: 5px;  /* 圆角边框 */
  cursor: pointer;  /* 鼠标悬停效果 */
}

button:hover {
  background-color: #45a049;  /* 悬停时按钮颜色变化 */
}

svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
}

table {
  width: 100%;
  margin: 20px auto;
  border-collapse: collapse;
}

th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

th {
  background-color: #f2f2f2;
}

.table-chunk, .table-block {
  cursor: pointer;
}

.mappings-table-wrapper {
  overflow-y: auto;
  overflow-x: auto;
}

td:nth-child(4) {
  width: 150px;
  white-space: nowrap;
}

.field-list {
  max-height: 550px;
  overflow-y: auto;
}

.highlight {
  background-color: lightcoral;
}

.table-container {
  overflow: auto;
  max-height: 70vh;
  position: relative;
}

.sql-result {
  margin-top: 20px;
  padding: 10px;
  background: #f9f9f9;
  border: 1px solid #ddd;
}

.loading {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
}

.spinner {
  border: 16px solid #f3f3f3; /* Light grey */
  border-top: 16px solid #3498db; /* Blue */
  border-radius: 50%;
  width: 120px;
  height: 120px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.message {
  position: fixed;
  top: 70%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1001;
  background: #f0f0f0;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
}
</style>
