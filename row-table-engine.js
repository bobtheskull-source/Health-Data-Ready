/**
 * Row-Table Engine - Reusable component for tabular data entry
 * Used across documents for: devices, vendors, findings, staff, incidents, remediation
 */

class RowTableEngine {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container #${containerId} not found`);
        }

        this.options = {
            type: 'generic', // device, vendor, finding, staff, incident, remediation
            title: 'Items',
            description: '',
            columns: [],
            allowAdd: true,
            allowEdit: true,
            allowDelete: true,
            allowDuplicate: true,
            mobileOptimized: true,
            emptyMessage: 'No items added yet. Click "Add" to get started.',
            ...options
        };

        this.rows = [];
        this.editingId = null;
        
        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
    }

    // ===== RENDERING =====

    render() {
        const html = `
            <div class="row-table-container" data-type="${this.options.type}">
                <div class="row-table-header">
                    <div class="row-table-title">
                        <h3>${this.options.title}</h3>
                        ${this.options.description ? `<p>${this.options.description}</p>` : ''}
                    </div>
                    ${this.options.allowAdd ? `
                        <button class="btn btn-primary btn-add" onclick="rowTableAdd('${this.container.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 5v14M5 12h14"></path>
                            </svg>
                            Add
                        </button>
                    ` : ''}
                </div>

                <div class="row-table-toolbar">
                    <input type="text" class="row-table-search" placeholder="Search..." 
                           onkeyup="rowTableSearch('${this.container.id}', this.value)">
                    <span class="row-table-count">${this.rows.length} items</span>
                </div>

                <div class="row-table-wrapper">
                    ${this.renderTable()}
                </div>

                ${this.renderFormModal()}
            </div>
        `;

        this.container.innerHTML = html;
    }

    renderTable() {
        if (this.rows.length === 0) {
            return `
                <div class="row-table-empty">
                    <div class="empty-icon">📋</div>
                    <p>${this.options.emptyMessage}</p>
                </div>
            `;
        }

        const isMobile = window.innerWidth < 768 && this.options.mobileOptimized;

        if (isMobile) {
            return this.renderMobileCards();
        }

        return this.renderDesktopTable();
    }

    renderDesktopTable() {
        return `
            <table class="row-table">
                <thead>
                    <tr>
                        ${this.options.columns.map(col => `
                            <th class="col-${col.key} ${col.sortable ? 'sortable' : ''}" 
                                ${col.sortable ? `onclick="rowTableSort('${this.container.id}', '${col.key}')"` : ''}>
                                ${col.label}
                                ${col.sortable ? '<span class="sort-indicator">↕</span>' : ''}
                            </th>
                        `).join('')}
                        ${this.hasActions() ? '<th class="col-actions">Actions</th>' : ''}
                    </tr>
                </thead>
                <tbody>
                    ${this.rows.map(row => this.renderRow(row)).join('')}
                </tbody>
            </table>
        `;
    }

    renderMobileCards() {
        return `
            <div class="row-table-cards">
                ${this.rows.map(row => this.renderMobileCard(row)).join('')}
            </div>
        `;
    }

    renderRow(row) {
        return `
            <tr data-id="${row.id}">
                ${this.options.columns.map(col => `
                    <td class="col-${col.key}">${this.formatCell(row[col.key], col)}</td>
                `).join('')}
                ${this.hasActions() ? `
                    <td class="col-actions">
                        ${this.options.allowEdit ? `
                            <button class="btn-icon-action" onclick="rowTableEdit('${this.container.id}', '${row.id}')" title="Edit">
                                ✏️
                            </button>
                        ` : ''}
                        ${this.options.allowDuplicate ? `
                            <button class="btn-icon-action" onclick="rowTableDuplicate('${this.container.id}', '${row.id}')" title="Duplicate">
                                📋
                            </button>
                        ` : ''}
                        ${this.options.allowDelete ? `
                            <button class="btn-icon-action btn-delete" onclick="rowTableDelete('${this.container.id}', '${row.id}')" title="Delete">
                                🗑️
                            </button>
                        ` : ''}
                    </td>
                ` : ''}
            </tr>
        `;
    }

    renderMobileCard(row) {
        return `
            <div class="row-table-card" data-id="${row.id}">
                <div class="card-content">
                    ${this.options.columns.map(col => `
                        <div class="card-field">
                            <span class="field-label">${col.label}</span>
                            <span class="field-value">${this.formatCell(row[col.key], col)}</span>
                        </div>
                    `).join('')}
                </div>
                ${this.hasActions() ? `
                    <div class="card-actions">
                        ${this.options.allowEdit ? `
                            <button class="btn-card-action" onclick="rowTableEdit('${this.container.id}', '${row.id}')">Edit</button>
                        ` : ''}
                        ${this.options.allowDuplicate ? `
                            <button class="btn-card-action" onclick="rowTableDuplicate('${this.container.id}', '${row.id}')">Duplicate</button>
                        ` : ''}
                        ${this.options.allowDelete ? `
                            <button class="btn-card-action btn-delete" onclick="rowTableDelete('${this.container.id}', '${row.id}')">Delete</button>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderFormModal() {
        return `
            <div class="row-table-modal" id="${this.container.id}-modal" style="display: none;">
                <div class="modal-backdrop" onclick="rowTableCloseModal('${this.container.id}')"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="${this.container.id}-modal-title">Add ${this.options.title}</h3>
                        <button class="btn-close" onclick="rowTableCloseModal('${this.container.id}')">&times;</button>
                    </div>
                    <form id="${this.container.id}-form" onsubmit="rowTableSubmit('${this.container.id}', event)">
                        <div class="modal-body">
                            ${this.options.columns.map(col => this.renderFormField(col)).join('')}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="rowTableCloseModal('${this.container.id}')">Cancel</button>
                            <button type="submit" class="btn btn-primary">Save</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    renderFormField(col) {
        const required = col.required ? ' required' : '';
        const value = col.defaultValue || '';

        switch (col.type) {
            case 'select':
                return `
                    <div class="form-group">
                        <label for="${this.container.id}-${col.key}">${col.label}${col.required ? ' *' : ''}</label>
                        <select id="${this.container.id}-${col.key}" name="${col.key}"${required}>
                            <option value="">Select ${col.label}...</option>
                            ${col.options.map(opt => `
                                <option value="${opt.value}" ${opt.value === value ? 'selected' : ''}>${opt.label}</option>
                            `).join('')}
                        </select>
                    </div>
                `;

            case 'textarea':
                return `
                    <div class="form-group">
                        <label for="${this.container.id}-${col.key}">${col.label}${col.required ? ' *' : ''}</label>
                        <textarea id="${this.container.id}-${col.key}" name="${col.key}" rows="3"${required} 
                                  placeholder="${col.placeholder || ''}">${value}</textarea>
                    </div>
                `;

            case 'checkbox':
                return `
                    <div class="form-group form-checkbox">
                        <label>
                            <input type="checkbox" id="${this.container.id}-${col.key}" name="${col.key}" 
                                   ${value ? 'checked' : ''}>
                            ${col.label}${col.required ? ' *' : ''}
                        </label>
                    </div>
                `;

            case 'date':
                return `
                    <div class="form-group">
                        <label for="${this.container.id}-${col.key}">${col.label}${col.required ? ' *' : ''}</label>
                        <input type="date" id="${this.container.id}-${col.key}" name="${col.key}"${required} value="${value}">
                    </div>
                `;

            default: // text
                return `
                    <div class="form-group">
                        <label for="${this.container.id}-${col.key}">${col.label}${col.required ? ' *' : ''}</label>
                        <input type="text" id="${this.container.id}-${col.key}" name="${col.key}"${required} 
                               value="${value}" placeholder="${col.placeholder || ''}">
                    </div>
                `;
        }
    }

    // ===== DATA OPERATIONS =====

    addRow(data) {
        const row = {
            id: 'row_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            ...data,
            createdAt: new Date().toISOString()
        };
        this.rows.push(row);
        this.refresh();
        return row;
    }

    updateRow(id, data) {
        const index = this.rows.findIndex(r => r.id === id);
        if (index === -1) return null;

        this.rows[index] = {
            ...this.rows[index],
            ...data,
            updatedAt: new Date().toISOString()
        };
        this.refresh();
        return this.rows[index];
    }

    deleteRow(id) {
        const index = this.rows.findIndex(r => r.id === id);
        if (index === -1) return false;

        this.rows.splice(index, 1);
        this.refresh();
        return true;
    }

    duplicateRow(id) {
        const original = this.rows.find(r => r.id === id);
        if (!original) return null;

        const { id: _, createdAt: __, updatedAt: ___, ...data } = original;
        return this.addRow({
            ...data,
            name: data.name ? `${data.name} (Copy)` : undefined
        });
    }

    getRow(id) {
        return this.rows.find(r => r.id === id);
    }

    getAllRows() {
        return [...this.rows];
    }

    setRows(rows) {
        this.rows = rows.map(r => ({
            ...r,
            id: r.id || 'row_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
        }));
        this.refresh();
    }

    // ===== FORM HANDLING =====

    openAddModal() {
        this.editingId = null;
        document.getElementById(`${this.container.id}-modal-title`).textContent = `Add ${this.options.title}`;
        document.getElementById(`${this.container.id}-form`).reset();
        this.showModal();
    }

    openEditModal(id) {
        const row = this.getRow(id);
        if (!row) return;

        this.editingId = id;
        document.getElementById(`${this.container.id}-modal-title`).textContent = `Edit ${this.options.title}`;

        // Populate form fields
        this.options.columns.forEach(col => {
            const field = document.getElementById(`${this.container.id}-${col.key}`);
            if (field) {
                if (col.type === 'checkbox') {
                    field.checked = row[col.key] || false;
                } else {
                    field.value = row[col.key] || '';
                }
            }
        });

        this.showModal();
    }

    submitForm(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = {};

        this.options.columns.forEach(col => {
            if (col.type === 'checkbox') {
                data[col.key] = formData.get(col.key) === 'on';
            } else {
                data[col.key] = formData.get(col.key) || '';
            }
        });

        if (this.editingId) {
            this.updateRow(this.editingId, data);
        } else {
            this.addRow(data);
        }

        this.closeModal();

        // Trigger callback
        if (this.options.onSave) {
            this.options.onSave(data, this.editingId);
        }
    }

    showModal() {
        document.getElementById(`${this.container.id}-modal`).style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        document.getElementById(`${this.container.id}-modal`).style.display = 'none';
        document.body.style.overflow = '';
        this.editingId = null;
    }

    // ===== SEARCH & FILTER =====

    search(query) {
        const term = query.toLowerCase();
        const rows = this.container.querySelectorAll('[data-id]');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    }

    sort(key) {
        const col = this.options.columns.find(c => c.key === key);
        if (!col || !col.sortable) return;

        this.rows.sort((a, b) => {
            let aVal = a[key] || '';
            let bVal = b[key] || '';

            if (typeof aVal === 'string') aVal = aVal.toLowerCase();
            if (typeof bVal === 'string') bVal = bVal.toLowerCase();

            if (aVal < bVal) return -1;
            if (aVal > bVal) return 1;
            return 0;
        });

        this.refresh();
    }

    // ===== HELPERS =====

    formatCell(value, col) {
        if (value === undefined || value === null || value === '') {
            return '<span class="cell-empty">—</span>';
        }

        if (col.type === 'checkbox') {
            return value ? '✓' : '—';
        }

        if (col.format) {
            return col.format(value);
        }

        if (col.type === 'select' && col.options) {
            const option = col.options.find(o => o.value === value);
            return option ? option.label : value;
        }

        return this.escapeHtml(String(value));
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    hasActions() {
        return this.options.allowEdit || this.options.allowDelete || this.options.allowDuplicate;
    }

    refresh() {
        const wrapper = this.container.querySelector('.row-table-wrapper');
        if (wrapper) {
            wrapper.innerHTML = this.renderTable();
        }

        const countEl = this.container.querySelector('.row-table-count');
        if (countEl) {
            countEl.textContent = `${this.rows.length} items`;
        }
    }

    attachEventListeners() {
        // Resize handler for mobile/desktop switching
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.refresh(), 150);
        });
    }
}

// ===== GLOBAL FUNCTIONS FOR INLINE EVENT HANDLERS =====

const rowTableInstances = {};

function createRowTable(containerId, options) {
    rowTableInstances[containerId] = new RowTableEngine(containerId, options);
    return rowTableInstances[containerId];
}

function getRowTable(containerId) {
    return rowTableInstances[containerId];
}

function rowTableAdd(containerId) {
    const table = getRowTable(containerId);
    if (table) table.openAddModal();
}

function rowTableEdit(containerId, id) {
    const table = getRowTable(containerId);
    if (table) table.openEditModal(id);
}

function rowTableDelete(containerId, id) {
    const table = getRowTable(containerId);
    if (!table) return;

    if (confirm('Are you sure you want to delete this item?')) {
        table.deleteRow(id);
    }
}

function rowTableDuplicate(containerId, id) {
    const table = getRowTable(containerId);
    if (table) table.duplicateRow(id);
}

function rowTableSubmit(containerId, event) {
    const table = getRowTable(containerId);
    if (table) table.submitForm(event);
}

function rowTableCloseModal(containerId) {
    const table = getRowTable(containerId);
    if (table) table.closeModal();
}

function rowTableSearch(containerId, query) {
    const table = getRowTable(containerId);
    if (table) table.search(query);
}

function rowTableSort(containerId, key) {
    const table = getRowTable(containerId);
    if (table) table.sort(key);
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RowTableEngine, createRowTable, getRowTable };
}
