<template>
  <div class="mapping-tool">
    <h1>Database Mapping Tool</h1>
    <div class="main-content">
      <div
        ref="tablesCanvas"
        class="tables-canvas"
        role="presentation"
      >
        <svg ref="linesSvg" class="connection-layer" aria-hidden="true"></svg>

        <div class="tables">
          <div class="source-tables pane" ref="sourceTablesContainer" @scroll="onScroll">
            <div class="pane-header">Source schema</div>
            <SourceTableUpload ref="sourceUpload" @tableAdded="addSourceTable" :targetTable="selectedTargetTable"/>
            <input
              type="search"
              v-model.trim="sourceSearch"
              placeholder="Search source fields…"
              class="field-search"
              autocomplete="off"
            />
            <div
              v-for="(table, index) in sourceTables"
              :key="'src-' + table.name"
              class="table-chunk card"
              :ref="'sourceTable' + index"
            >
              <h3 class="table-title" @click="toggleTable(index, 'source')">
                {{ table.name }}
                <button type="button" class="btn-mini danger" @click.stop="removeSourceTable(index)">Remove</button>
              </h3>
              <div v-show="!collapsedSourceTables[index]" class="field-list">
                <TableComponent
                  :table="table"
                  :search="sourceSearch"
                  :fieldMappings="fieldMappings"
                  :mappingHoverIndex="hoverMappingIndex"
                  @fieldDragged="onFieldDragged"
                  @fieldDropped="onFieldDropped"
                  @dragging="scheduleLineUpdate"
                  @fieldDoubleClicked="onFieldDoubleClicked"
                />
              </div>
            </div>
          </div>

          <div class="connector-gutter">
            <div class="guide-line"></div>
          </div>

          <div class="target-tables pane" ref="targetTablesContainer" @scroll="onScroll">
            <div class="pane-header">Target schema</div>
            <TargetTableUpload
              ref="targetUpload"
              @tableAdded="addTargetTable"
              @targetTableSelected="setSelectedTargetTable"
            />
            <input
              type="search"
              v-model.trim="targetSearch"
              placeholder="Search target fields…"
              class="field-search"
              autocomplete="off"
            />
            <div
              v-for="(block, blockIndex) in targetTableBlocks"
              :key="'tgt-' + block.name"
              class="table-block card"
              :ref="'targetTable' + blockIndex"
            >
              <h3 class="table-title" @click="toggleTable(blockIndex, 'target')">
                {{ block.name }}
                <button type="button" class="btn-mini danger" @click.stop="removeTargetTable(blockIndex)">Remove</button>
              </h3>
              <div v-show="!collapsedBlocks[blockIndex]" class="field-list">
                <TableComponent
                  :table="block"
                  :search="targetSearch"
                  :fieldMappings="fieldMappings"
                  :mappingHoverIndex="hoverMappingIndex"
                  @fieldDragged="onFieldDragged"
                  @fieldDropped="onFieldDropped"
                  @dragging="scheduleLineUpdate"
                  @fieldDoubleClicked="onFieldDoubleClicked"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mappings sidebar">
        <h2>Mappings</h2>
        <div class="mappings-actions">
          <button type="button" class="btn-secondary" @click="exportMappings">Export</button>
          <button type="button" class="btn-secondary" @click="triggerFileInput">Import</button>
          <input type="file" accept="application/json,.json" @change="importMappings" class="hidden-file" ref="fileInput"/>
          <button type="button" class="btn-primary" @click="recommendFieldMappings">AI map fields</button>
          <button type="button" class="btn-primary" @click="generateSQL">Generate SQL</button>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Src field</th>
                <th>Src table</th>
                <th>Tgt field</th>
                <th>Tgt table</th>
                <th>Rule</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(mapping, index) in fieldMappings"
                :key="'map-' + index"
                class="mapping-row"
                :class="{
                  'row-highlight': isFieldHighlighted(mapping),
                  'row-hover': hoverMappingIndex === index,
                }"
                @mouseenter="hoverMappingIndex = index"
                @mouseleave="hoverMappingIndex = null"
              >
                <td>{{ mapping.source.field }}</td>
                <td>{{ mapping.source.table.name }}</td>
                <td>{{ mapping.target.field }}</td>
                <td>{{ mapping.target.table.name }}</td>
                <td>
                  <input
                    v-model="mapping.transformationRule"
                    placeholder="Transform / rule notes"
                    class="rule-input"
                  />
                </td>
                <td>
                  <button type="button" class="btn-mini danger" @click="removeMapping(index)">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="generatedSQL" class="sql-result">
          <h3>Generated SQL</h3>
          <pre>{{ generatedSQL }}</pre>
        </div>

        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>
        <div v-if="message" class="message-banner">
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
import { fetchJson, postForm } from '@/api/client';
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
      hoverMappingIndex: null,
      sourceSearch: '',
      targetSearch: '',
      draggedField: null,
      isScrolling: false,
      resizeObserver: null,
      imported: false,
      selectedTargetTable: null,
      generatedSQL: '',
      loading: false,
      message: '',
      /** @type {number | undefined} */
      lineRafHandle: undefined,
    };
  },
  watch: {
    fieldMappings: {
      handler() {
        this.scheduleLineUpdate();
      },
      deep: true
    },
    hoverMappingIndex() {
      this.scheduleLineUpdate();
    }
  },
  methods: {
    /** Coalesce repaint work so scroll + watchers do not swamp the frame budget. */
    scheduleLineUpdate() {
      cancelAnimationFrame(this.lineRafHandle);
      this.lineRafHandle = requestAnimationFrame(() => {
        this.$nextTick(() => this.updateLines());
      });
    },
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
      this.$nextTick(this.scheduleLineUpdate);
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
      this.$nextTick(this.scheduleLineUpdate);
    },
    toggleTable(index, type) {
      if (type === 'source') {
        this.collapsedSourceTables.splice(index, 1, !this.collapsedSourceTables[index]);
      } else {
        this.collapsedBlocks.splice(index, 1, !this.collapsedBlocks[index]);
      }
      this.$nextTick(this.scheduleLineUpdate);
    },
    onFieldDragged(field, table) {
      this.draggedField = { field, table };
    },
    resolveTableByRole(name, role) {
      if (role === 'source') {
        return this.sourceTables.find(table => table.name === name);
      }
      return this.targetTableBlocks.find(table => table.name === name);
    },
    mappingExists(payload) {
      return this.fieldMappings.some(mapping =>
          mapping.source.field === payload.sourceField &&
          mapping.source.table.name === payload.sourceTableName &&
          mapping.target.field === payload.targetField &&
          mapping.target.table.name === payload.targetTableName);
    },
    onFieldDropped(targetField, targetTableStub) {
      if (!this.draggedField || !targetField || !targetTableStub) return;
      const targetName = typeof targetTableStub.name === 'string' ? targetTableStub.name : String(targetTableStub);

      /** @type {{ sourceField:string, sourceTableName:string, targetField:string, targetTableName:string, source:any, target:any } | null} */
      let link = null;

      if (
        this.isSourceTable(this.draggedField.table.name) &&
          this.isTargetTable(targetName)
      ) {
        const srcTbl = this.resolveTableByRole(this.draggedField.table.name, 'source');
        const tgtTbl = this.resolveTableByRole(targetName, 'target');
        if (!srcTbl || !tgtTbl) return;
        link = {
          sourceField: this.draggedField.field,
          sourceTableName: srcTbl.name,
          targetField,
          targetTableName: tgtTbl.name,
          source: srcTbl,
          target: tgtTbl,
        };
      } else if (
        this.isTargetTable(this.draggedField.table.name) &&
          this.isSourceTable(targetName)
      ) {
        const tgtTbl = this.resolveTableByRole(this.draggedField.table.name, 'target');
        const srcTbl = this.resolveTableByRole(targetName, 'source');
        if (!srcTbl || !tgtTbl) return;
        link = {
          sourceField: targetField,
          sourceTableName: srcTbl.name,
          targetField: this.draggedField.field,
          targetTableName: tgtTbl.name,
          source: srcTbl,
          target: tgtTbl,
        };
      }

      if (link && !this.mappingExists(link)) {
        this.fieldMappings.push({
          source: { field: link.sourceField, table: link.source },
          target: { field: link.targetField, table: link.target },
          transformationRule: '',
        });
        this.draggedField = null;
        this.scheduleLineUpdate();
      }
    },
    removeMapping(index) {
      if (this.hoverMappingIndex === index) this.hoverMappingIndex = null;
      this.fieldMappings.splice(index, 1);
      this.scheduleLineUpdate();
    },
    exportMappings() {
      const mappings = this.fieldMappings.map(mapping => ({
        sourceField: mapping.source.field,
        sourceTable: mapping.source.table.name,
        targetField: mapping.target.field,
        targetTable: mapping.target.table.name,
        transformationRule: mapping.transformationRule || ''
      }));
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(mappings, null, 2));
      const anchor = document.createElement('a');
      anchor.href = dataUri;
      anchor.download = 'mappings.json';
      anchor.click();
    },
    collectSourceTables() {
      const payload = this.sourceTables.map(table => ({ name: table.name, fields: table.fields }));
      return new Blob([JSON.stringify(payload)], { type: 'application/json' });
    },

    async recommendFieldMappings() {
      this.loading = true;
      this.message = '';
      try {
        if (this.sourceTables.length === 0 || !this.selectedTargetTable) {
          this.message = 'Import source tables and select a target table first.';
          return;
        }
        const formData = new FormData();
        formData.append('source_file', this.collectSourceTables());
        formData.append(
          'target_file',
          new Blob([JSON.stringify(this.selectedTargetTable)], { type: 'application/json' })
        );

        const data = await postForm('/api/recommend_fields', formData);

        this.loadFieldMappings(data);
        this.message = 'Field mappings generated successfully.';
        this.setAutoHideMessage();
      } catch (error) {
        this.message = `API error: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    async generateSQL() {
      this.loading = true;
      this.message = '';
      try {
        const data = await fetchJson('/api/generate_sql', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.fieldMappings),
        });
        this.generatedSQL = data.sql;
        this.message = 'SQL generated.';
        this.setAutoHideMessage();
      } catch (error) {
        this.message = `API error: ${error.message}`;
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
        formData.append(
          'target_file',
          new Blob([JSON.stringify(targetTable)], { type: 'application/json' })
        );

        const data = await postForm('/api/recommend', formData);

        this.loadSourceTables(data);
        this.message = 'Source tables recommended.';
        this.setAutoHideMessage();
      } catch (error) {
        this.message = `API error: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    loadFieldMappings(mappings) {
      mappings.forEach(mapping => {
        const sourceTable = this.sourceTables.find(table => table.name === mapping.sourceTable);
        const targetTable = this.targetTableBlocks.find(block => block.name === mapping.targetTable);

        if (sourceTable && targetTable && !this.mappingExists({
          sourceField: mapping.sourceField,
          sourceTableName: sourceTable.name,
          targetField: mapping.targetField,
          targetTableName: targetTable.name,
        })) {
          this.fieldMappings.push({
            source: { field: mapping.sourceField, table: sourceTable },
            target: { field: mapping.targetField, table: targetTable },
            transformationRule: mapping.transformationRule || '',
          });
        }
      });
      this.scheduleLineUpdate();
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
      if (!file) return;
      const reader = new FileReader();
      reader.onload = e => {
        try {
          const mappings = JSON.parse(e.target.result);
          this.loadMappings(mappings);
          this.imported = true;
          this.$nextTick(this.scheduleLineUpdate);
        } catch (err) {
          console.error('Mappings import parse error:', err);
          this.message = 'Invalid mappings JSON.';
        }
      };
      reader.readAsText(file);
      event.target.value = '';
    },
    loadMappings(mappings) {
      const newSourceTables = [];
      const newTargetTables = [];

      mappings.forEach(mapping => {
        if (!newSourceTables.some(table => table.name === mapping.sourceTable)) {
          newSourceTables.push({ name: mapping.sourceTable, fields: [] });
        }

        if (!newTargetTables.some(table => table.name === mapping.targetTable)) {
          newTargetTables.push({ name: mapping.targetTable, fields: [] });
        }

        const sourceTbl = newSourceTables.find(table => table.name === mapping.sourceTable);
        const targetTbl = newTargetTables.find(table => table.name === mapping.targetTable);
        if (!sourceTbl.fields.some(f => f.name === mapping.sourceField)) {
          sourceTbl.fields.push({ name: mapping.sourceField });
        }
        if (!targetTbl.fields.some(f => f.name === mapping.targetField)) {
          targetTbl.fields.push({ name: mapping.targetField });
        }
      });

      this.sourceTables = newSourceTables;
      this.targetTableBlocks = newTargetTables;
      this.collapsedSourceTables = newSourceTables.map(() => false);
      this.collapsedBlocks = newTargetTables.map(() => false);

      this.fieldMappings = mappings.map(mapping => ({
        source: { field: mapping.sourceField, table: { name: mapping.sourceTable } },
        target: { field: mapping.targetField, table: { name: mapping.targetTable } },
        transformationRule: mapping.transformationRule || '',
      }));
      this.hoverMappingIndex = null;
      this.generatedSQL = '';
    },
    /**
     * Redraw Bézier connectors in the tables canvas viewport (no scrollX mixing).
     */
    updateLines() {
      const svgNode = this.$refs.linesSvg;
      const canvas = this.$refs.tablesCanvas;

      const svgSel = svgNode ? d3.select(svgNode) : null;
      if (!svgSel || !canvas) return;

      const rect = canvas.getBoundingClientRect();
      if (rect.width < 16 || rect.height < 16) return;

      svgSel.selectAll('*').remove();
      svgSel
        .attr('width', Math.ceil(rect.width))
        .attr('height', Math.ceil(rect.height))
        .attr('viewBox', `0 0 ${rect.width} ${rect.height}`);

      this.fieldMappings.forEach((mapping, index) => {
        const sourceEl = this.findFieldElement(mapping.source.field, mapping.source.table.name, '.source-tables');
        const targetEl = this.findFieldElement(mapping.target.field, mapping.target.table.name, '.target-tables');

        if (!sourceEl || !targetEl) return;

        const sr = sourceEl.getBoundingClientRect();
        const tr = targetEl.getBoundingClientRect();

        let x1 = sr.right - rect.left;
        let y1 = sr.top + sr.height / 2 - rect.top;
        let x2 = tr.left - rect.left;
        let y2 = tr.top + tr.height / 2 - rect.top;

        if (sr.width <= 2 || tr.width <= 2) return;

        const dx = x2 - x1;
        const tension = Math.min(160, Math.max(48, Math.abs(dx) * 0.45));
        const c1x = x1 + tension;
        const c1y = y1;
        const c2x = x2 - tension;
        const c2y = y2;

        const hue = (index * 47) % 360;
        const baseColor = `hsl(${hue} 72% 48%)`;

        const isHover = index === this.hoverMappingIndex ||
          this.mappingTouchesHighlight(mapping);

        svgSel.append('path')
          .attr('d', `M${x1},${y1} C${c1x},${c1y} ${c2x},${c2y} ${x2},${y2}`)
          .attr('stroke', baseColor)
          .attr('fill', 'none')
          .attr('stroke-width', isHover ? 3.2 : 2)
          .attr('stroke-linecap', 'round')
          .attr('opacity', isHover ? '0.95' : '0.78');
      });
    },
    mappingTouchesHighlight(mapping) {
      const h = this.highlightedField;
      if (!h) return false;

      const tname = h.table?.name ?? h.table;
      const hitSource =
        mapping.source.field === h.field &&
        mapping.source.table.name === tname;
      const hitTarget =
        mapping.target.field === h.field &&
        mapping.target.table.name === tname;

      return hitSource || hitTarget;
    },

    /** Locate a `<li.field-item>` belonging to either schema pane by dataset keys. */
    findFieldElement(field, tableName, containerSelector) {
      const container = document.querySelector(containerSelector);
      if (!container) return null;

      const elements = Array.from(container.querySelectorAll('li.field-item'));
      return elements.find(li =>
          li.dataset.field === field && li.dataset.table === tableName) || null;
    },
    isSourceTable(name) {
      return this.sourceTables.some(table => table.name === name);
    },
    isTargetTable(name) {
      return this.targetTableBlocks.some(block => block.name === name);
    },
    onFieldDoubleClicked(field, table) {
      const duplicate =
        this.highlightedField &&
        this.highlightedField.field === field &&
        this.highlightedField.table?.name === table?.name;

      this.highlightedField = duplicate ? null : { field, table };
      this.scheduleLineUpdate();
    },
    setAutoHideMessage() {
      setTimeout(() => {
        this.message = '';
      }, 5200);
    },

    /**
     * Hydrate the worksheet with checked-in demo assets from /public/fixtures.
     */
    async loadDemoFixtures() {
      const baseUrl = process.env.BASE_URL || '/';
      const jsonUrl = `${baseUrl}fixtures/std_patient_clinical_hub.json`;
      const xlsxUrl = `${baseUrl}fixtures/demo_hospital_ehr_messy_multi_sheet.xlsx`;
      try {
        const [jsonRes, binRes] = await Promise.all([
          fetch(jsonUrl),
          fetch(xlsxUrl),
        ]);
        if (!jsonRes.ok || !binRes.ok) {
          console.warn('[demo] fixture fetch failed', jsonRes.status, binRes.status);
          return;
        }
        const catalog = await jsonRes.json();
        await this.$nextTick();
        this.$refs.targetUpload?.bootstrapFromCatalog(catalog);

        const buf = await binRes.arrayBuffer();
        const blob = new Blob([buf], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
        const demoFile = new File([blob], 'demo_hospital_ehr_messy_multi_sheet.xlsx', { type: blob.type });
        await this.$refs.sourceUpload?.bootstrapFromFile(demoFile);

        const tables = this.$refs.sourceUpload?.tables ?? [];
        tables.forEach(tbl => {
          this.addSourceTable({ name: tbl.name, fields: tbl.fields });
        });

        this.selectedTargetTable = catalog[0];
        this.message = 'Demo catalog + hospital workbook loaded (all sheets).';
        this.setAutoHideMessage();
      } catch (error) {
        console.warn('[demo] auto-load skipped', error);
      }
    },
    isFieldHighlighted(mapping) {
      if (!this.highlightedField) return false;

      const highlightTableName =
        typeof this.highlightedField.table === 'object'
          ? this.highlightedField.table?.name
          : this.highlightedField.table;

      return (
        mapping.source.field === this.highlightedField.field &&
              mapping.source.table.name === highlightTableName
      ) || (
        mapping.target.field === this.highlightedField.field &&
              mapping.target.table.name === highlightTableName
      );
    },
    debounce(func, wait) {
      let timeout;
      return (...args) => {
        window.clearTimeout(timeout);
        timeout = window.setTimeout(() => func.apply(this, args), wait);
      };
    },
    onScroll() {
      if (!this.isScrolling) {
        this.isScrolling = true;
        requestAnimationFrame(() => {
          this.scheduleLineUpdate();
          this.isScrolling = false;
        });
      }
    },
  },

  mounted() {
    this.collapsedBlocks = this.targetTableBlocks.map(() => false);
    this.collapsedSourceTables = this.sourceTables.map(() => false);

    this.debouncedResize = this.debounce(this.scheduleLineUpdate, 80);

    window.addEventListener('resize', this.debouncedResize);
    window.addEventListener('scroll', this.debouncedResize, true);

    this.$refs.sourceTablesContainer?.addEventListener('scroll', this.onScroll);
    this.$refs.targetTablesContainer?.addEventListener('scroll', this.onScroll);

    const canvas = this.$refs.tablesCanvas;
    if ('ResizeObserver' in window && canvas) {
      this.resizeObserver = new ResizeObserver(() => this.scheduleLineUpdate());
      this.resizeObserver.observe(canvas);
    }

    this.$nextTick(async () => {
      await this.loadDemoFixtures();
      this.scheduleLineUpdate();
    });
  },
  beforeUnmount() {
    cancelAnimationFrame(this.lineRafHandle);
    window.removeEventListener('resize', this.debouncedResize);
    window.removeEventListener('scroll', this.debouncedResize, true);

    const sourceScroller = this.$refs.sourceTablesContainer;
    const targetScroller = this.$refs.targetTablesContainer;

    if (sourceScroller) sourceScroller.removeEventListener('scroll', this.onScroll);
    if (targetScroller) targetScroller.removeEventListener('scroll', this.onScroll);

    this.resizeObserver?.disconnect();
  },
};
</script>

<style scoped>
.mapping-tool {
  --surface: #f7f9fc;
  --card-bg: #ffffff;
  --border: #dfe6f1;
  --accent-src: #1e6bb8;
  --accent-tgt: #22756a;

  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  position: relative;
  margin: 16px 20px;
  max-width: 1800px;
  margin-inline: auto;
}

.main-content {
  display: flex;
  gap: 20px;
  width: 100%;
  align-items: flex-start;
}

.tables-canvas {
  flex: 1 1 auto;
  min-width: 0;
  position: relative;
}

.connection-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.tables {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px minmax(0, 1fr);
  gap: 0;
  width: 100%;
  align-items: stretch;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  overflow: visible;
}

.pane-header {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 6px 8px;
  margin-bottom: 6px;
  border-radius: 6px;
  color: white;
}

.source-tables > .pane-header {
  background: linear-gradient(90deg, var(--accent-src), #3f8fd9);
}

.target-tables > .pane-header {
  background: linear-gradient(90deg, var(--accent-tgt), #3abf9c);
}

.pane.source-tables,
.pane.target-tables {
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: calc(100vh - 176px);
  padding: 10px;
}

.connector-gutter {
  position: relative;
  pointer-events: none;
  align-self: stretch;
  background: linear-gradient(to bottom, transparent, rgba(30,107,184,0.06), transparent);
}

.connector-gutter .guide-line {
  position: absolute;
  left: 50%;
  top: 48px;
  bottom: 12px;
  width: 1px;
  transform: translateX(-50%);
  background: repeating-linear-gradient(
    to bottom,
    var(--border) 0px,
    var(--border) 6px,
    transparent 6px,
    transparent 14px
  );
  opacity: 0.85;
}

.field-search {
  width: calc(100% - 16px);
  margin: 6px 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 2px;
  margin: 12px 0;
  box-shadow: 0 1px 2px rgb(22 52 103 / 0.05);
}

.table-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0;
  padding: 8px 10px;
  font-size: 0.92rem;
  cursor: pointer;
  user-select: none;
}

.btn-mini {
  margin: 0;
  padding: 4px 10px;
  font-size: 0.74rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}

.btn-mini.danger {
  background-color: #c94b4b;
}

.btn-mini.danger:hover {
  background-color: #a53b3b;
}

.field-list {
  max-height: 420px;
  overflow-y: auto;
}

.sidebar {
  width: min(32%, 400px);
  flex: 0 0 auto;
}

.sidebar h2 {
  margin-top: 0;
  font-size: 1rem;
}

.mappings-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.sidebar button {
  margin: 0;
  padding: 8px 12px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
}

.btn-secondary {
  background-color: #6c7a94;
}

.btn-secondary:hover {
  background-color: #5a677d;
}

.btn-primary {
  background-color: #2d8848;
}

.btn-primary:hover {
  background-color: #24703b;
}

.hidden-file {
  display: none;
}

table {
  width: 100%;
  margin: 0 auto;
  border-collapse: collapse;
  font-size: 0.8rem;
}

th,
td {
  border: 1px solid #e2e9f5;
  padding: 8px;
  vertical-align: top;
}

.mapping-row:nth-child(even) {
  background-color: rgba(246,249,253, 0.7);
}

.row-hover td {
  background-color: rgb(229 239 253);
}

.mapping-row.row-highlight td {
  background-color: rgba(229, 173, 173, 0.45);
}

.rule-input {
  width: 120px;
  max-width: 100%;
}

.table-container {
  overflow-x: auto;
  max-height: 66vh;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.sql-result {
  margin-top: 16px;
  padding: 10px;
  background: rgba(246,249,253, 0.8);
  border: 1px solid var(--border);
  border-radius: 10px;
  text-align: left;
}

.loading {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: rgb(255 255 255 / 0.25);
  z-index: 1000;
}

.spinner {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 14px solid #edf1f9;
  border-top: 14px solid #2c6dcf;
  border-radius: 50%;
  width: 72px;
  height: 72px;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.message-banner {
  position: sticky;
  bottom: 12px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgb(239 246 255);
  border: 1px solid #cfe0fb;
}

@media (max-width: 1024px) {
  .main-content {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .tables {
    grid-template-columns: minmax(0, 1fr);
  }

  .connector-gutter {
    display: none;
  }
}</style>
