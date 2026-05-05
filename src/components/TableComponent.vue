<!-- Per-table column list with drag/drop bridging for MappingTool.vue -->
<template>
  <div
    class="table-component"
    :class="{ 'drag-over': isDragOver }"
    @drop="dropField"
    @dragover="allowDrop"
    @dragleave="dragLeave"
  >
    <ul v-if="!collapsed">
      <li
        v-for="field in filteredFields"
        :key="field.name"
        class="field-item"
        :class="fieldItemClass(field)"
        draggable="true"
        @dragstart="dragField($event, field)"
        @drag="emitDragging"
        @dblclick="fieldDoubleClicked(field)"
        @mouseenter="activeHoverField = field.name"
        @mouseleave="activeHoverField = null"
        :data-field="field.name"
        :data-table="table.name"
      >
        <span class="cell-name">{{ field.name }}</span>
        <span v-if="field.comment" class="cell-comment">{{ field.comment }}</span>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  props: {
    table: { type: Object, required: true },
    search: { type: String, default: '' },
    fieldMappings: { type: Array, default: () => [] },
    /** Mirrors sidebar row hover so connector emphasis stays in sync with field chips. */
    mappingHoverIndex: { default: null },
  },
  data() {
    return {
      isDragOver: false,
      collapsed: false,
      /** Local hover for subtle affordance feedback. */
      activeHoverField: null,
    };
  },
  computed: {
    filteredFields() {
      if (!this.search) return this.table.fields;

      const term = this.search.toLowerCase();
      return this.table.fields.filter(field =>
          field.name.toLowerCase().includes(term) ||
          (field.comment || '').toLowerCase().includes(term));
    },
  },
  methods: {
    dragField(event, field) {
      event.dataTransfer.setData('field', JSON.stringify({ field: field.name, table: this.table }));
      event.dataTransfer.effectAllowed = 'link';
      this.$emit('fieldDragged', field.name, this.table);
      this.$emit('dragging');
    },
    dropField(event) {
      event.preventDefault();
      this.isDragOver = false;
      const targetFieldElement = event.target.closest('.field-item');
      if (!targetFieldElement) return;

      const targetField = targetFieldElement.getAttribute('data-field');
      const targetTableName = targetFieldElement.getAttribute('data-table');

      if (targetField) {
        this.$emit('fieldDropped', targetField, { name: targetTableName });
      }
      this.$emit('dragging');
    },
    allowDrop(event) {
      event.preventDefault();
      this.isDragOver = true;
    },
    dragLeave() {
      this.isDragOver = false;
    },
    emitDragging() {
      this.$emit('dragging');
    },

    participatesInHoveredWire(field) {
      if (
        this.mappingHoverIndex === null ||
            this.mappingHoverIndex === undefined
      ) return false;
      const row = this.fieldMappings[this.mappingHoverIndex];
      if (!row) return false;

      return (
        row.source.field === field.name &&
            row.source.table.name === this.table.name
      ) || (
        row.target.field === field.name &&
            row.target.table.name === this.table.name
      );
    },

    fieldItemClass(field) {
      return {
        highlighted: this.isFieldMapped(field),
        'mapping-hot': this.participatesInHoveredWire(field),
        'mapping-local-hover': field.name === this.activeHoverField && this.isFieldMapped(field),
      };
    },

    isFieldMapped(field) {
      return this.fieldMappings.some(mapping =>
          (mapping.source.field === field.name && mapping.source.table.name === this.table.name) ||
          (mapping.target.field === field.name && mapping.target.table.name === this.table.name),
      );
    },

    fieldDoubleClicked(field) {
      this.$emit('fieldDoubleClicked', field.name, this.table);
    },
  },

  watch: {
    collapsed(val) {
      if (!val) {
        this.$emit('expanded', this.table);
      }
    },
  },
};
</script>

<style scoped>
.table-component {
  border: 1px solid #e7edf6;
  border-radius: 8px;
  padding: 4px;
  margin: 8px 4px;
  background: rgb(252 253 255);
  transition:
    border-color 0.14s ease,
    box-shadow 0.14s ease;
}

.table-component.drag-over {
  border-color: #2c6dcf;
  box-shadow: inset 0 0 0 1px rgb(44 109 207 / 0.25);
}

ul {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.field-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin: 3px 0;
  padding: 6px 8px;
  border-radius: 6px;
  background-color: #f6f8fc;
  border: 1px solid rgb(229 237 247 / 0.9);
  cursor: grab;
  transition:
    transform 0.12s ease,
    background-color 0.12s ease;
}

.field-item:active {
  cursor: grabbing;
}

.field-item:hover {
  transform: translateX(3px);
  background-color: #eef3fb;
}

.field-item.highlighted {
  background-color: rgb(229 239 229);
}

.field-item.mapping-hot {
  box-shadow:
    inset 4px 0 0 hsl(217 94% 60%),
    0 0 0 1px rgb(44 109 207 / 0.18);
  background-color: #f0f5ff;
}

.field-item.mapping-local-hover.highlighted {
  background-color: #e4ecff;
}

.cell-name {
  font-weight: 600;
  font-size: 0.85rem;
  color: #1c2f4a;
  word-break: break-word;
}

.cell-comment {
  font-size: 0.71rem;
  color: #5f6f85;
  line-height: 1.25;
  white-space: pre-wrap;
}

@media (min-width: 520px) {
  .field-item {
    flex-direction: row;
    justify-content: space-between;
    align-items: baseline;
    gap: 16px;
  }

  .cell-comment {
    text-align: right;
    flex: 0 1 45%;
  }
}

</style>
