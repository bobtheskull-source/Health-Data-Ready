/**
 * Health Data Ready - Data Model Layer
 * Provides IndexedDB abstraction for Engagement/Document/RowEntry storage
 */

const DB_NAME = 'HealthDataReady';
const DB_VERSION = 2;

class DataModel {
    constructor() {
        this.db = null;
        this.ready = this.initDB();
    }

    async initDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Engagements store
                if (!db.objectStoreNames.contains('engagements')) {
                    const store = db.createObjectStore('engagements', { keyPath: 'id' });
                    store.createIndex('clientName', 'clientName', { unique: false });
                    store.createIndex('startDate', 'startDate', { unique: false });
                    store.createIndex('status', 'status', { unique: false });
                }

                // Documents store
                if (!db.objectStoreNames.contains('documents')) {
                    const docStore = db.createObjectStore('documents', { keyPath: 'id' });
                    docStore.createIndex('engagementId', 'engagementId', { unique: false });
                    docStore.createIndex('type', 'type', { unique: false });
                }

                // RowEntries store (reusable for devices, vendors, findings, etc.)
                if (!db.objectStoreNames.contains('rowEntries')) {
                    const rowStore = db.createObjectStore('rowEntries', { keyPath: 'id' });
                    rowStore.createIndex('engagementId', 'engagementId', { unique: false });
                    rowStore.createIndex('documentId', 'documentId', { unique: false });
                    rowStore.createIndex('type', 'type', { unique: false });
                }

                // Autosave drafts store
                if (!db.objectStoreNames.contains('drafts')) {
                    const draftStore = db.createObjectStore('drafts', { keyPath: 'id' });
                    draftStore.createIndex('engagementId', 'engagementId', { unique: false });
                }
            };
        });
    }

    // ===== ENGAGEMENT OPERATIONS =====

    async createEngagement(data) {
        await this.ready;
        const engagement = {
            id: this.generateId('eng'),
            clientName: data.clientName,
            consultantName: data.consultantName,
            startDate: data.startDate,
            referenceNumber: data.referenceNumber,
            notes: data.notes || '',
            status: 'active',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            completionPercent: 0,
            documentProgress: {}
        };

        const tx = this.db.transaction(['engagements'], 'readwrite');
        const store = tx.objectStore('engagements');
        await store.add(engagement);
        return engagement;
    }

    async getEngagement(id) {
        await this.ready;
        const tx = this.db.transaction(['engagements'], 'readonly');
        const store = tx.objectStore('engagements');
        return store.get(id);
    }

    async updateEngagement(id, updates) {
        await this.ready;
        const engagement = await this.getEngagement(id);
        if (!engagement) throw new Error('Engagement not found');

        const updated = {
            ...engagement,
            ...updates,
            updatedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['engagements'], 'readwrite');
        const store = tx.objectStore('engagements');
        await store.put(updated);
        return updated;
    }

    async listEngagements() {
        await this.ready;
        const tx = this.db.transaction(['engagements'], 'readonly');
        const store = tx.objectStore('engagements');
        return store.getAll();
    }

    // ===== DOCUMENT OPERATIONS =====

    async createDocument(engagementId, type, data = {}) {
        await this.ready;
        const document = {
            id: this.generateId('doc'),
            engagementId,
            type,
            status: 'draft',
            progress: 0,
            data: data,
            requiredFields: this.getRequiredFields(type),
            completedFields: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['documents'], 'readwrite');
        const store = tx.objectStore('documents');
        await store.add(document);
        return document;
    }

    async getDocument(id) {
        await this.ready;
        const tx = this.db.transaction(['documents'], 'readonly');
        const store = tx.objectStore('documents');
        return store.get(id);
    }

    async getDocumentByType(engagementId, type) {
        await this.ready;
        const tx = this.db.transaction(['documents'], 'readonly');
        const store = tx.objectStore('documents');
        const index = store.index('type');
        const all = await index.getAll(type);
        return all.find(d => d.engagementId === engagementId);
    }

    async updateDocument(id, updates) {
        await this.ready;
        const doc = await this.getDocument(id);
        if (!doc) throw new Error('Document not found');

        const updated = {
            ...doc,
            data: { ...doc.data, ...updates.data },
            status: updates.status || doc.status,
            progress: updates.progress !== undefined ? updates.progress : doc.progress,
            completedFields: updates.completedFields || doc.completedFields,
            updatedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['documents'], 'readwrite');
        const store = tx.objectStore('documents');
        await store.put(updated);
        return updated;
    }

    async listDocuments(engagementId) {
        await this.ready;
        const tx = this.db.transaction(['documents'], 'readonly');
        const store = tx.objectStore('documents');
        const index = store.index('engagementId');
        return index.getAll(engagementId);
    }

    // ===== ROW ENTRY OPERATIONS =====

    async createRowEntry(engagementId, documentId, type, data) {
        await this.ready;
        const entry = {
            id: this.generateId('row'),
            engagementId,
            documentId,
            type,
            data,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['rowEntries'], 'readwrite');
        const store = tx.objectStore('rowEntries');
        await store.add(entry);
        return entry;
    }

    async getRowEntry(id) {
        await this.ready;
        const tx = this.db.transaction(['rowEntries'], 'readonly');
        const store = tx.objectStore('rowEntries');
        return store.get(id);
    }

    async updateRowEntry(id, updates) {
        await this.ready;
        const entry = await this.getRowEntry(id);
        if (!entry) throw new Error('Row entry not found');

        const updated = {
            ...entry,
            data: { ...entry.data, ...updates },
            updatedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['rowEntries'], 'readwrite');
        const store = tx.objectStore('rowEntries');
        await store.put(updated);
        return updated;
    }

    async deleteRowEntry(id) {
        await this.ready;
        const tx = this.db.transaction(['rowEntries'], 'readwrite');
        const store = tx.objectStore('rowEntries');
        await store.delete(id);
    }

    async listRowEntries(filters = {}) {
        await this.ready;
        const tx = this.db.transaction(['rowEntries'], 'readonly');
        const store = tx.objectStore('rowEntries');
        
        let entries = await store.getAll();
        
        if (filters.engagementId) {
            entries = entries.filter(e => e.engagementId === filters.engagementId);
        }
        if (filters.documentId) {
            entries = entries.filter(e => e.documentId === filters.documentId);
        }
        if (filters.type) {
            entries = entries.filter(e => e.type === filters.type);
        }
        
        return entries;
    }

    // ===== DRAFT/AUTOSAVE OPERATIONS =====

    async saveDraft(engagementId, documentId, fieldData) {
        await this.ready;
        const draft = {
            id: `${engagementId}_${documentId}`,
            engagementId,
            documentId,
            data: fieldData,
            savedAt: new Date().toISOString()
        };

        const tx = this.db.transaction(['drafts'], 'readwrite');
        const store = tx.objectStore('drafts');
        await store.put(draft);
    }

    async loadDraft(engagementId, documentId) {
        await this.ready;
        const tx = this.db.transaction(['drafts'], 'readonly');
        const store = tx.objectStore('drafts');
        return store.get(`${engagementId}_${documentId}`);
    }

    async deleteDraft(engagementId, documentId) {
        await this.ready;
        const tx = this.db.transaction(['drafts'], 'readwrite');
        const store = tx.objectStore('drafts');
        await store.delete(`${engagementId}_${documentId}`);
    }

    // ===== PROGRESS CALCULATION =====

    async calculateEngagementProgress(engagementId) {
        const documents = await this.listDocuments(engagementId);
        if (documents.length === 0) return 0;
        
        const totalProgress = documents.reduce((sum, doc) => sum + (doc.progress || 0), 0);
        return Math.round(totalProgress / documents.length);
    }

    async updateEngagementProgress(engagementId) {
        const progress = await this.calculateEngagementProgress(engagementId);
        await this.updateEngagement(engagementId, { completionPercent: progress });
        return progress;
    }

    // ===== SHARED DATA (Cross-Document) =====

    async getSharedVendors(engagementId) {
        return this.listRowEntries({ engagementId, type: 'vendor' });
    }

    async getSharedDevices(engagementId) {
        return this.listRowEntries({ engagementId, type: 'device' });
    }

    async getSharedFindings(engagementId) {
        return this.listRowEntries({ engagementId, type: 'finding' });
    }

    // ===== UTILITY =====

    generateId(prefix) {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getRequiredFields(docType) {
        const fields = {
            'overview': ['clientName', 'consultantName', 'startDate'],
            'device-inventory': ['deviceName', 'deviceCategory'],
            'vulnerability': ['findingDescription', 'severity'],
            'mhmd': ['applicabilityDetermined'],
            'remediation': ['remediationItems'],
            'hipaa': ['entityType'],
            'data-inventory': ['dataCategories'],
            'incident': ['incidentLog'],
            'staff': ['trainingRoster'],
            'annual-summary': ['summaryGenerated']
        };
        return fields[docType] || [];
    }
}

// Singleton instance
const dataModel = new DataModel();

// Export for module usage (if supported)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DataModel, dataModel };
}
