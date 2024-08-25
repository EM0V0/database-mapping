<!--TableComponent.vue-->
<template>
  <div class="table-component" :class="{ 'drag-over': isDragOver }" @drop="dropField" @dragover="allowDrop" @dragleave="dragLeave">
    <ul v-if="!collapsed">
      <li v-for="field in filteredFields" :key="field.name" class="field-item"
          :class="{'highlighted': isFieldMapped(field)}"
          draggable="true" @dragstart="dragField($event, field)" @drag="emitDragging"
          @dblclick="fieldDoubleClicked(field)"
          :data-field="field.name" :data-table="table.name">
        <span>{{ field.name }}</span><span>{{ field.comment }}</span>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  props: ['table', 'search', 'fieldMappings'],
  data() {
    return {
      isDragOver: false,
      collapsed: false
    };
  },
  computed: {
    filteredFields() {
      if (!this.search) {
        return this.table.fields;
      }
      return this.table.fields.filter(field => field.name.toLowerCase().includes(this.search.toLowerCase()));
    }
  },
  methods: {
    dragField(event, field) {
      event.dataTransfer.setData('field', JSON.stringify({ field: field.name, table: this.table }));
      this.$emit('fieldDragged', field.name, this.table);
      this.$emit('dragging');
    },
    dropField(event) {
      event.preventDefault();
      this.isDragOver = false;
      const targetFieldElement = event.target.closest('.field-item');
      if (!targetFieldElement) return;
      const targetField = targetFieldElement.getAttribute('data-field');
      const targetTable = targetFieldElement.getAttribute('data-table');

      if (targetField) {
        this.$emit('fieldDropped', targetField, { name: targetTable });
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
    isFieldMapped(field) {
      return this.fieldMappings.some(mapping =>
        mapping.source.field === field.name && mapping.source.table.name === this.table.name ||
        mapping.target.field === field.name && mapping.target.table.name === this.table.name
      );
    },
    fieldDoubleClicked(field) {
      this.$emit('fieldDoubleClicked', field.name, this.table.name);
    }
  },
  watch: {
    collapsed(val) {
      if (!val) {
        this.$emit('expanded', this.table);
      }
    }
  }
};
</script>

<style scoped>
.table-component {
  border: 1px solid #ccc;
  padding: 10px;
  margin: 10px;
}
.table-component.drag-over {
  border-color: #007bff;
}
ul {
  list-style-type: none;
  padding: 0;
}
li.field-item {
  display: flex;
  justify-content: space-between;
  margin: 3px 0;
  padding: 3px;
  background-color: #f0f0f0;
  cursor: pointer;
}
li.field-item.highlighted {
  background-color: #ffdada;
}
</style>
