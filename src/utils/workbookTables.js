/**
 * Normalize XLSX workbooks into the source-table payloads consumed by MappingTool /
 * SourceTableUpload.vue (sheet name → columns with optional row-2 commentary).
 */

import * as XLSX from 'xlsx';

/**
 * Build table descriptors from a parsed SheetJS workbook.
 * Row 1: field identifiers; row 2: optional human-readable comments per column.
 * @returns {{ name: string, fields: { name: unknown, comment: unknown }[]}[]}
 */
export function tablesFromWorkbook(workbook) {
  return workbook.SheetNames.map((name) => {
    const worksheet = workbook.Sheets[name];
    const grid = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
    const headers = grid[0];
    const commentsRow = grid[1];
    const fields = headers.map((header, index) => ({
      name: header,
      comment: commentsRow ? commentsRow[index] : '',
    }));
    return { name, fields };
  });
}

/** @param {ArrayBuffer | Uint8Array} buffer */
export function tablesFromXlsxArrayBuffer(buffer) {
  const workbook = XLSX.read(buffer, { type: 'array' });
  return tablesFromWorkbook(workbook);
}

/** @param {string} binary legacy FileReader BinaryString payload */
export function tablesFromXlsxBinaryString(binary) {
  const workbook = XLSX.read(binary, { type: 'binary' });
  return tablesFromWorkbook(workbook);
}
