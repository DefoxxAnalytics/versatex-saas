/**
 * Upload Wizard JavaScript
 * Handles the 5-step CSV upload wizard for Django Admin
 * Uses safe DOM manipulation (textContent and createElement) to prevent XSS
 */

const UploadWizard = {
    // State
    currentStep: 1,
    file: null,
    previewData: null,
    mapping: {},
    validationResults: null,
    taskId: null,
    uploadId: null,
    pollInterval: null,

    // Target fields for column mapping
    TARGET_FIELDS: [
        { key: 'supplier', label: 'Supplier', required: true },
        { key: 'category', label: 'Category', required: true },
        { key: 'amount', label: 'Amount', required: true },
        { key: 'date', label: 'Date', required: true },
        { key: 'description', label: 'Description', required: false },
        { key: 'subcategory', label: 'Subcategory', required: false },
        { key: 'location', label: 'Location', required: false },
        { key: 'fiscal_year', label: 'Fiscal Year', required: false },
        { key: 'spend_band', label: 'Spend Band', required: false },
        { key: 'payment_method', label: 'Payment Method', required: false },
        { key: 'invoice_number', label: 'Invoice Number', required: false },
    ],

    // Column aliases for auto-detection
    COLUMN_ALIASES: {
        'supplier': ['supplier', 'vendor', 'supplier_name', 'vendor_name', 'supplier name', 'vendor name'],
        'category': ['category', 'cat', 'category_name', 'spend_category', 'category name', 'spend category'],
        'amount': ['amount', 'total', 'value', 'cost', 'price', 'spend', 'total_amount', 'total amount'],
        'date': ['date', 'transaction_date', 'trans_date', 'invoice_date', 'transaction date', 'invoice date'],
        'description': ['description', 'desc', 'details', 'notes', 'memo'],
        'invoice_number': ['invoice', 'invoice_number', 'invoice_no', 'inv_num', 'invoice number', 'inv no'],
        'fiscal_year': ['fiscal_year', 'fiscal year', 'fy', 'year'],
        'location': ['location', 'site', 'branch', 'office'],
        'subcategory': ['subcategory', 'sub_category', 'sub category'],
        'spend_band': ['spend_band', 'spend band', 'band'],
        'payment_method': ['payment_method', 'payment method', 'payment', 'method']
    },

    /**
     * Initialize the wizard
     */
    init() {
        this.bindEvents();
        this.initOrganizationDropdown();
        this.loadTemplates();
        this.showStep(1);
    },

    /**
     * Bind all event listeners
     */
    bindEvents() {
        // Step 1: File Selection
        const dropzone = document.getElementById('file-dropzone');
        const fileInput = document.getElementById('file-input');
        const browseBtn = document.getElementById('browse-btn');
        const removeBtn = document.getElementById('remove-file-btn');

        dropzone.addEventListener('click', () => fileInput.click());
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeFile();
        });

        // Drag and drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this.handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        // Navigation buttons
        document.getElementById('step1-next').addEventListener('click', () => this.goToStep(2));
        document.getElementById('step2-back').addEventListener('click', () => this.goToStep(1));
        document.getElementById('step2-next').addEventListener('click', () => this.goToStep(3));
        document.getElementById('step3-back').addEventListener('click', () => this.goToStep(2));
        document.getElementById('step3-next').addEventListener('click', () => this.goToStep(4));
        document.getElementById('step4-back').addEventListener('click', () => this.goToStep(3));
        document.getElementById('step4-next').addEventListener('click', () => this.startUpload());

        // Template buttons
        document.getElementById('load-template-btn').addEventListener('click', () => this.loadSelectedTemplate());
        document.getElementById('save-template-btn').addEventListener('click', () => this.saveTemplate());

        // New upload button
        document.getElementById('new-upload-btn').addEventListener('click', () => this.resetWizard());

        // Skip duplicates checkbox - disable strict mode when skip is checked
        const skipDuplicatesCheckbox = document.getElementById('skip-duplicates');
        const strictDuplicatesCheckbox = document.getElementById('strict-duplicates');
        const strictDuplicatesLabel = document.getElementById('strict-duplicates-label');
        if (skipDuplicatesCheckbox && strictDuplicatesCheckbox) {
            skipDuplicatesCheckbox.addEventListener('change', () => {
                if (skipDuplicatesCheckbox.checked) {
                    strictDuplicatesCheckbox.checked = false;
                    strictDuplicatesCheckbox.disabled = true;
                    if (strictDuplicatesLabel) {
                        strictDuplicatesLabel.style.opacity = '0.5';
                    }
                } else {
                    strictDuplicatesCheckbox.disabled = false;
                    if (strictDuplicatesLabel) {
                        strictDuplicatesLabel.style.opacity = '1';
                    }
                }
            });
        }
    },

    /**
     * Initialize organization dropdown for superusers
     */
    initOrganizationDropdown() {
        if (!CONFIG.isSuperuser) return;

        const select = document.getElementById('organization-select');
        if (!select) return;

        // Apply styling
        this.applyDarkSelectStyle(select);

        CONFIG.organizations.forEach(org => {
            const option = document.createElement('option');
            option.value = org.id;
            option.textContent = org.name;
            option.style.setProperty('background-color', '#ffffff', 'important');
            option.style.setProperty('color', '#1f2937', 'important');
            select.appendChild(option);
        });

        // Pre-select user's organization if available
        if (CONFIG.userOrganization) {
            select.value = CONFIG.userOrganization.id;
        }

        // Add change listener to update selection display
        select.addEventListener('change', () => this.updateOrganizationDisplay());

        // Initial update
        this.updateOrganizationDisplay();
    },

    /**
     * Update the organization selection display label
     */
    updateOrganizationDisplay() {
        const select = document.getElementById('organization-select');
        const display = document.getElementById('org-selection-display');

        if (!select || !display) return;

        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.value) {
            display.textContent = selectedOption.text;
            display.classList.add('visible');
        } else {
            display.textContent = '';
            display.classList.remove('visible');
        }
    },

    /**
     * Apply light color-scheme styling to select elements for visibility
     * The key is color-scheme: light to override Django's dark mode
     */
    applyDarkSelectStyle(select) {
        select.style.setProperty('color-scheme', 'light', 'important');
        select.style.setProperty('background-color', '#ffffff', 'important');
        select.style.setProperty('color', '#1f2937', 'important');
        select.style.setProperty('border', '1px solid #d1d5db', 'important');
        select.style.setProperty('-webkit-appearance', 'menulist', 'important');
        select.style.setProperty('appearance', 'menulist', 'important');
    },

    /**
     * Get selected organization ID
     */
    getOrganizationId() {
        if (CONFIG.isSuperuser) {
            const select = document.getElementById('organization-select');
            return select ? select.value : '';
        }
        return CONFIG.userOrganization ? CONFIG.userOrganization.id : '';
    },

    /**
     * Handle file selection
     */
    handleFileSelect(file) {
        if (!file) return;

        // Validate file
        if (!file.name.toLowerCase().endsWith('.csv')) {
            this.showError('File must be a CSV file');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            this.showError('File size must be less than 50MB');
            return;
        }

        this.file = file;
        this.updateFileDisplay();
        document.getElementById('step1-next').disabled = false;
    },

    /**
     * Update file display
     */
    updateFileDisplay() {
        const fileInfo = document.getElementById('file-info');
        const dropzone = document.getElementById('file-dropzone');

        if (this.file) {
            document.getElementById('selected-file-name').textContent = this.file.name;
            document.getElementById('selected-file-size').textContent = this.formatFileSize(this.file.size);
            fileInfo.classList.remove('hidden');
            dropzone.style.display = 'none';
        } else {
            fileInfo.classList.add('hidden');
            dropzone.style.display = 'block';
        }
    },

    /**
     * Remove selected file
     */
    removeFile() {
        this.file = null;
        this.previewData = null;
        this.mapping = {};
        document.getElementById('file-input').value = '';
        this.updateFileDisplay();
        document.getElementById('step1-next').disabled = true;
    },

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Navigate to a step
     */
    goToStep(step) {
        if (step < 1 || step > 5) return;

        // Execute step-specific logic before showing
        if (step === 2 && !this.previewData) {
            this.fetchPreview();
        } else if (step === 3) {
            this.renderMappingUI();
        } else if (step === 4) {
            this.runValidation();
        }

        this.showStep(step);
    },

    /**
     * Show a specific step
     */
    showStep(step) {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));

        // Show target step
        const stepEl = document.getElementById('step-' + step);
        if (stepEl) {
            stepEl.classList.add('active');
        }

        // Update progress bar
        document.querySelectorAll('.progress-step').forEach((el, index) => {
            el.classList.remove('active', 'completed');
            if (index + 1 < step) {
                el.classList.add('completed');
            } else if (index + 1 === step) {
                el.classList.add('active');
            }
        });

        // Update progress lines
        document.querySelectorAll('.progress-line').forEach((el, index) => {
            el.classList.remove('completed');
            if (index + 1 < step) {
                el.classList.add('completed');
            }
        });

        this.currentStep = step;
    },

    /**
     * Create loading indicator element
     */
    createLoadingIndicator(message) {
        const div = document.createElement('div');
        div.className = 'loading-indicator';

        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        div.appendChild(spinner);

        const p = document.createElement('p');
        p.textContent = message;
        div.appendChild(p);

        return div;
    },

    /**
     * Create error message element
     */
    createErrorMessage(message) {
        const div = document.createElement('div');
        div.className = 'loading-indicator';

        const p = document.createElement('p');
        p.style.color = '#dc2626';
        p.textContent = 'Error: ' + message;
        div.appendChild(p);

        return div;
    },

    /**
     * Fetch file preview
     */
    async fetchPreview() {
        const container = document.getElementById('preview-table-container');
        // Clear container and add loading indicator
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.appendChild(this.createLoadingIndicator('Loading preview...'));

        const formData = new FormData();
        formData.append('file', this.file);
        formData.append('organization_id', this.getOrganizationId());

        try {
            const response = await fetch(CONFIG.apiUrls.preview, {
                method: 'POST',
                headers: { 'X-CSRFToken': CONFIG.csrfToken },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Preview failed');
            }

            this.previewData = await response.json();
            this.renderPreviewTable();
            this.autoDetectMapping();

        } catch (error) {
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }
            container.appendChild(this.createErrorMessage(error.message));
        }
    },

    /**
     * Render preview table using safe DOM methods
     */
    renderPreviewTable() {
        const container = document.getElementById('preview-table-container');

        // Update stats
        document.getElementById('total-rows').textContent = this.previewData.total_rows;
        document.getElementById('total-columns').textContent = this.previewData.headers.length;

        // Create table
        const table = document.createElement('table');
        table.className = 'preview-table';

        // Header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        this.previewData.headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Body
        const tbody = document.createElement('tbody');
        this.previewData.preview_rows.forEach(row => {
            const tr = document.createElement('tr');
            this.previewData.headers.forEach(header => {
                const td = document.createElement('td');
                td.textContent = row[header] || '';
                td.title = row[header] || '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        // Clear and append
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.appendChild(table);
    },

    /**
     * Auto-detect column mappings
     */
    autoDetectMapping() {
        if (!this.previewData) return;

        this.mapping = {};
        const headers = this.previewData.headers;

        headers.forEach(header => {
            const normalized = header.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_');

            for (const [field, aliases] of Object.entries(this.COLUMN_ALIASES)) {
                if (aliases.some(alias => {
                    const normalizedAlias = alias.replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_');
                    return normalized === normalizedAlias || normalized.includes(normalizedAlias);
                })) {
                    // Only map if not already mapped
                    if (!Object.values(this.mapping).includes(field)) {
                        this.mapping[header] = field;
                    }
                    break;
                }
            }
        });
    },

    /**
     * Render mapping UI using safe DOM methods
     */
    renderMappingUI() {
        const grid = document.getElementById('mapping-grid');

        // Clear existing content safely
        while (grid.firstChild) {
            grid.removeChild(grid.firstChild);
        }

        this.TARGET_FIELDS.forEach(field => {
            const item = document.createElement('div');
            item.className = 'mapping-item';
            if (field.required) {
                item.classList.add('required');
            }

            // Check if mapped
            const mappedColumn = Object.keys(this.mapping).find(k => this.mapping[k] === field.key);
            if (mappedColumn) {
                item.classList.add('mapped');
            }

            const label = document.createElement('div');
            label.className = 'mapping-label';
            label.textContent = field.label;
            if (field.required) {
                const star = document.createElement('span');
                star.className = 'required-star';
                star.textContent = ' *';
                label.appendChild(star);
            }

            const select = document.createElement('select');
            select.className = 'form-select mapping-select';
            select.dataset.targetField = field.key;
            select.id = 'mapping-select-' + field.key;

            // Apply dark theme styling
            this.applyDarkSelectStyle(select);

            // Empty option
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '-- Select column --';
            emptyOption.style.setProperty('background-color', '#ffffff', 'important');
            emptyOption.style.setProperty('color', '#6b7280', 'important');
            select.appendChild(emptyOption);

            // Add column options
            this.previewData.headers.forEach(header => {
                const option = document.createElement('option');
                option.value = header;
                option.textContent = header;
                option.style.setProperty('background-color', '#ffffff', 'important');
                option.style.setProperty('color', '#1f2937', 'important');
                if (mappedColumn === header) {
                    option.selected = true;
                }
                select.appendChild(option);
            });

            // Create selection display label (workaround for invisible dropdown text)
            const selectionDisplay = document.createElement('div');
            selectionDisplay.className = 'mapping-selection-display';
            selectionDisplay.id = 'mapping-display-' + field.key;
            if (mappedColumn) {
                selectionDisplay.textContent = mappedColumn;
                selectionDisplay.classList.add('visible');
            }

            // Update selection display on change
            select.addEventListener('change', (e) => {
                const selectedValue = e.target.value;
                const display = document.getElementById('mapping-display-' + field.key);
                if (display) {
                    if (selectedValue) {
                        display.textContent = selectedValue;
                        display.classList.add('visible');
                    } else {
                        display.textContent = '';
                        display.classList.remove('visible');
                    }
                }
                this.updateMapping(field.key, selectedValue);
            });

            item.appendChild(label);
            item.appendChild(select);
            item.appendChild(selectionDisplay);
            grid.appendChild(item);
        });
    },

    /**
     * Update column mapping
     */
    updateMapping(targetField, csvColumn) {
        // Remove old mapping for this target field
        Object.keys(this.mapping).forEach(key => {
            if (this.mapping[key] === targetField) {
                delete this.mapping[key];
            }
        });

        // Add new mapping
        if (csvColumn) {
            this.mapping[csvColumn] = targetField;
        }

        // Update UI
        this.renderMappingUI();
    },

    /**
     * Load templates from server
     */
    async loadTemplates() {
        try {
            const url = CONFIG.apiUrls.templates + '?organization_id=' + this.getOrganizationId();
            const response = await fetch(url, {
                headers: { 'X-CSRFToken': CONFIG.csrfToken }
            });

            if (!response.ok) return;

            const data = await response.json();
            const select = document.getElementById('template-select');

            // Clear existing options except first
            while (select.options.length > 1) {
                select.remove(1);
            }

            data.templates.forEach(template => {
                const option = document.createElement('option');
                option.value = JSON.stringify(template.mapping);
                option.textContent = template.name + (template.is_default ? ' (Default)' : '');
                option.style.setProperty('background-color', '#ffffff', 'important');
                option.style.setProperty('color', '#1f2937', 'important');
                select.appendChild(option);
            });

            // Apply dark styling to the template select
            this.applyDarkSelectStyle(select);

        } catch (error) {
            console.error('Error loading templates:', error);
        }
    },

    /**
     * Load selected template
     */
    loadSelectedTemplate() {
        const select = document.getElementById('template-select');
        if (!select.value) return;

        try {
            this.mapping = JSON.parse(select.value);
            this.renderMappingUI();
        } catch (error) {
            this.showError('Error loading template');
        }
    },

    /**
     * Save current mapping as template
     */
    async saveTemplate() {
        const nameInput = document.getElementById('template-name');
        const name = nameInput.value.trim();

        if (!name) {
            this.showError('Please enter a template name');
            return;
        }

        try {
            const response = await fetch(CONFIG.apiUrls.saveTemplate, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CONFIG.csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    mapping: this.mapping,
                    organization_id: this.getOrganizationId()
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to save template');
            }

            nameInput.value = '';
            this.loadTemplates();
            this.showSuccess('Template saved successfully');

        } catch (error) {
            this.showError(error.message);
        }
    },

    /**
     * Run validation
     */
    async runValidation() {
        const loading = document.getElementById('validation-loading');
        const results = document.getElementById('validation-results');

        loading.classList.remove('hidden');
        results.classList.add('hidden');

        const skipDuplicates = document.getElementById('skip-duplicates')?.checked || false;
        const strictDuplicates = document.getElementById('strict-duplicates')?.checked || false;

        const formData = new FormData();
        formData.append('file', this.file);
        formData.append('mapping', JSON.stringify(this.mapping));
        formData.append('organization_id', this.getOrganizationId());
        formData.append('skip_duplicates', skipDuplicates);
        formData.append('strict_duplicates', strictDuplicates);

        try {
            const response = await fetch(CONFIG.apiUrls.validate, {
                method: 'POST',
                headers: { 'X-CSRFToken': CONFIG.csrfToken },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Validation failed');
            }

            this.validationResults = data;
            this.renderValidationResults();

        } catch (error) {
            // Clear loading and show error
            while (loading.firstChild) {
                loading.removeChild(loading.firstChild);
            }
            const errorP = document.createElement('p');
            errorP.style.color = '#dc2626';
            errorP.textContent = 'Error: ' + error.message;
            loading.appendChild(errorP);
        }
    },

    /**
     * Render validation results using safe DOM methods
     */
    renderValidationResults() {
        const loading = document.getElementById('validation-loading');
        const results = document.getElementById('validation-results');
        const errorsList = document.getElementById('errors-list');
        const errorsTbody = document.getElementById('errors-tbody');

        loading.classList.add('hidden');
        results.classList.remove('hidden');

        // Update counts
        document.getElementById('valid-count').textContent = this.validationResults.valid_count;
        document.getElementById('error-count').textContent = this.validationResults.error_count;
        document.getElementById('duplicate-count').textContent = this.validationResults.duplicate_count;

        // Clear existing errors
        while (errorsTbody.firstChild) {
            errorsTbody.removeChild(errorsTbody.firstChild);
        }

        // Show errors if any
        if (this.validationResults.errors && this.validationResults.errors.length > 0) {
            errorsList.classList.remove('hidden');

            this.validationResults.errors.forEach(error => {
                const tr = document.createElement('tr');

                const rowTd = document.createElement('td');
                rowTd.textContent = error.row || '-';
                tr.appendChild(rowTd);

                const fieldTd = document.createElement('td');
                fieldTd.textContent = error.field || '-';
                tr.appendChild(fieldTd);

                const msgTd = document.createElement('td');
                msgTd.textContent = error.message || '-';
                tr.appendChild(msgTd);

                const valTd = document.createElement('td');
                valTd.textContent = error.value || '-';
                valTd.style.fontFamily = 'monospace';
                tr.appendChild(valTd);

                errorsTbody.appendChild(tr);
            });
        } else {
            errorsList.classList.add('hidden');
        }

        // Enable/disable next button based on valid count
        const nextBtn = document.getElementById('step4-next');
        nextBtn.disabled = this.validationResults.valid_count === 0;
    },

    /**
     * Start the upload process
     */
    async startUpload() {
        this.showStep(5);

        const progressEl = document.getElementById('upload-progress');
        const completeEl = document.getElementById('upload-complete');

        progressEl.classList.remove('hidden');
        completeEl.classList.add('hidden');

        const skipInvalid = document.getElementById('skip-invalid').checked;
        const skipDuplicates = document.getElementById('skip-duplicates')?.checked || false;
        const strictDuplicates = document.getElementById('strict-duplicates')?.checked || false;

        const formData = new FormData();
        formData.append('file', this.file);
        formData.append('mapping', JSON.stringify(this.mapping));
        formData.append('organization_id', this.getOrganizationId());
        formData.append('skip_invalid', skipInvalid);
        formData.append('skip_duplicates', skipDuplicates);
        formData.append('strict_duplicates', strictDuplicates);

        try {
            const response = await fetch(CONFIG.apiUrls.upload, {
                method: 'POST',
                headers: { 'X-CSRFToken': CONFIG.csrfToken },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            if (data.async) {
                // Start polling for progress
                this.taskId = data.task_id;
                this.uploadId = data.upload_id;
                this.startPolling();
            } else {
                // Sync upload completed
                this.showUploadComplete(data);
            }

        } catch (error) {
            this.showUploadError(error.message);
        }
    },

    /**
     * Start polling for async upload progress
     */
    startPolling() {
        this.pollInterval = setInterval(() => this.pollProgress(), 2000);
    },

    /**
     * Poll for upload progress
     */
    async pollProgress() {
        try {
            const url = CONFIG.apiUrls.progress.replace('TASK_ID', this.taskId);
            const response = await fetch(url, {
                headers: { 'X-CSRFToken': CONFIG.csrfToken }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get progress');
            }

            this.updateProgress(data);

            if (data.status !== 'processing') {
                clearInterval(this.pollInterval);
                this.showUploadComplete(data);
            }

        } catch (error) {
            clearInterval(this.pollInterval);
            this.showUploadError(error.message);
        }
    },

    /**
     * Update progress display
     */
    updateProgress(data) {
        const percent = data.progress_percent || 0;
        const message = data.progress_message || 'Processing...';

        document.getElementById('progress-percent').textContent = percent + '%';
        document.getElementById('progress-message').textContent = message;

        // Update circle progress
        const circle = document.getElementById('progress-fill');
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (percent / 100) * circumference;
        circle.style.strokeDashoffset = offset;
    },

    /**
     * Show upload complete
     */
    showUploadComplete(data) {
        const progressEl = document.getElementById('upload-progress');
        const completeEl = document.getElementById('upload-complete');

        progressEl.classList.add('hidden');
        completeEl.classList.remove('hidden');

        // Update icon and title based on status
        const icon = completeEl.querySelector('.complete-icon');
        const title = document.getElementById('complete-title');

        if (data.status === 'completed') {
            icon.className = 'complete-icon success';
            title.textContent = 'Upload Complete!';
        } else if (data.status === 'partial') {
            icon.className = 'complete-icon partial';
            title.textContent = 'Upload Partially Complete';
        } else {
            icon.className = 'complete-icon failed';
            title.textContent = 'Upload Failed';
        }

        // Update stats
        document.getElementById('complete-successful').textContent = data.successful_rows || 0;
        document.getElementById('complete-failed').textContent = data.failed_rows || 0;
        document.getElementById('complete-duplicates').textContent = data.duplicate_rows || 0;

        // Show buttons
        document.getElementById('finish-btn').style.display = 'inline-flex';
        document.getElementById('new-upload-btn').style.display = 'inline-flex';
    },

    /**
     * Show upload error
     */
    showUploadError(message) {
        const progressEl = document.getElementById('upload-progress');
        const completeEl = document.getElementById('upload-complete');

        progressEl.classList.add('hidden');
        completeEl.classList.remove('hidden');

        const icon = completeEl.querySelector('.complete-icon');
        const title = document.getElementById('complete-title');

        icon.className = 'complete-icon failed';
        title.textContent = 'Upload Error: ' + message;

        document.getElementById('complete-successful').textContent = '0';
        document.getElementById('complete-failed').textContent = '0';
        document.getElementById('complete-duplicates').textContent = '0';

        document.getElementById('finish-btn').style.display = 'inline-flex';
        document.getElementById('new-upload-btn').style.display = 'inline-flex';
    },

    /**
     * Reset wizard for new upload
     */
    resetWizard() {
        this.file = null;
        this.previewData = null;
        this.mapping = {};
        this.validationResults = null;
        this.taskId = null;
        this.uploadId = null;

        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        document.getElementById('file-input').value = '';
        this.updateFileDisplay();
        document.getElementById('step1-next').disabled = true;

        document.getElementById('finish-btn').style.display = 'none';
        document.getElementById('new-upload-btn').style.display = 'none';

        this.showStep(1);
    },

    /**
     * Show error message
     */
    showError(message) {
        alert('Error: ' + message);
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        alert(message);
    }
};

// Initialize wizard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    UploadWizard.init();
});
