// Media Pipeline Dashboard JavaScript

class MediaPipelineDashboard {
    constructor() {
        this.apiBase = '/api';
        this.refreshInterval = 30000; // 30 seconds
        this.logRefreshInterval = 10000; // 10 seconds
        this.isLogAutoRefresh = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
        this.initTheme();
    }

    setupEventListeners() {
        // Tab change events
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const targetTab = e.target.getAttribute('data-bs-target');
                this.onTabChange(targetTab);
            });
        });

        // Log auto-refresh toggle
        document.getElementById('logs-tab').addEventListener('click', () => {
            this.isLogAutoRefresh = true;
            this.startLogAutoRefresh();
        });
    }

    onTabChange(tabId) {
        switch(tabId) {
            case '#dashboard':
                this.loadDashboardData();
                break;
            case '#config':
                this.loadConfiguration();
                this.loadTelegramStatus();
                refreshCacheStats();
                break;
            case '#logs':
                this.loadLogs();
                this.startLogAutoRefresh();
                break;
            case '#troubleshoot':
                this.loadTroubleshootingGuide();
                break;
            case '#analytics':
                this.loadAnalytics();
                this.loadSourcesStatus();
                break;
            case '#services':
                this.loadServices();
                break;
            case '#readme':
                this.loadReadme();
                break;
            case '#docs':
                this.loadDocumentation();
                break;
        }
    }

    async loadInitialData() {
        await this.loadSystemStatus();
        await this.loadDashboardData();
        await refreshCacheStats();
        
        // Pre-load analytics data for better UX
        this.loadAnalytics();
    }

    async loadSystemStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            this.updateStatusCards(data);
            this.updateStatusIndicator(data.overall_status);
        } catch (error) {
            console.error('Failed to load system status:', error);
            this.showAlert('Failed to load system status', 'danger');
        }
    }

    updateStatusCards(data) {
        const container = document.getElementById('status-cards');
        container.innerHTML = '';

        const statusCards = [
            {
                title: 'Media Pipeline Service',
                status: data.services['media-pipeline'],
                icon: 'fas fa-cogs',
                description: 'Main pipeline service'
            },
            {
                title: 'Syncthing Service',
                status: data.services['syncthing@root'],
                icon: 'fas fa-sync',
                description: 'File synchronization service'
            },
            {
                title: 'Database Connections',
                status: this.getDatabaseStatus(data.database),
                icon: 'fas fa-database',
                description: this.getDatabaseDescription(data.database)
            },
            {
                title: 'Storage Mount',
                status: data.storage.mounted ? 'running' : 'stopped',
                icon: 'fas fa-hdd',
                description: 'NAS storage mount'
            }
        ];

        statusCards.forEach(card => {
            const cardElement = this.createStatusCard(card);
            container.appendChild(cardElement);
        });
        
        // Update database status cards
        this.updateDatabaseStatusCards(data.database);
    }

    createStatusCard(card) {
        const div = document.createElement('div');
        div.className = 'col-md-3 col-sm-6 mb-3';
        
        const statusClass = this.getStatusClass(card.status);
        const statusText = this.getStatusText(card.status);
        
        div.innerHTML = `
            <div class="status-card ${statusClass}">
                <div class="status-icon">
                    <i class="${card.icon}"></i>
                </div>
                <h6 class="mb-1">${card.title}</h6>
                <p class="mb-1 text-muted small">${card.description}</p>
                <span class="badge ${this.getStatusBadgeClass(card.status)}">${statusText}</span>
            </div>
        `;
        
        return div;
    }

    getStatusClass(status) {
        switch(status) {
            case 'running': return 'status-success';
            case 'stopped': return 'status-danger';
            case 'warning': return 'status-warning';
            default: return 'status-info';
        }
    }

    getStatusText(status) {
        switch(status) {
            case 'running': return 'Running';
            case 'stopped': return 'Stopped';
            case 'warning': return 'Warning';
            default: return 'Unknown';
        }
    }

    getStatusBadgeClass(status) {
        switch(status) {
            case 'running': return 'bg-success';
            case 'stopped': return 'bg-danger';
            case 'warning': return 'bg-warning';
            default: return 'bg-secondary';
        }
    }

    getDatabaseStatus(database) {
        if (!database) return 'stopped';
        
        const supabaseConnected = database.supabase?.connected || false;
        const localhostConnected = database.localhost_sql?.connected || false;
        
        if (supabaseConnected && localhostConnected) {
            return 'running';
        } else if (supabaseConnected || localhostConnected) {
            return 'warning';
        } else {
            return 'stopped';
        }
    }

    getDatabaseDescription(database) {
        if (!database) return 'Database connections unavailable';
        
        const supabaseConnected = database.supabase?.connected || false;
        const localhostConnected = database.localhost_sql?.connected || false;
        
        if (supabaseConnected && localhostConnected) {
            return 'Supabase + PostgreSQL both connected';
        } else if (supabaseConnected) {
            return 'Supabase connected, PostgreSQL offline';
        } else if (localhostConnected) {
            return 'PostgreSQL connected, Supabase offline';
        } else {
            return 'Both database connections offline';
        }
    }

    updateDatabaseStatusCards(database) {
        const container = document.getElementById('database-status-cards');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!database) {
            container.innerHTML = '<div class="col-12 text-center text-muted">Database status unavailable</div>';
            return;
        }
        
        const supabaseStatus = database.supabase || {};
        const localhostStatus = database.localhost_sql || {};
        
        const supabaseCard = this.createDatabaseStatusCard(
            'Supabase Cloud Database',
            supabaseStatus.connected ? 'running' : 'stopped',
            supabaseStatus.error || 'Connected',
            supabaseStatus.tables || 0,
            'fas fa-cloud'
        );
        
        const localhostCard = this.createDatabaseStatusCard(
            'PostgreSQL Local Database',
            localhostStatus.connected ? 'running' : 'stopped',
            localhostStatus.error || 'Connected',
            localhostStatus.tables || 0,
            'fas fa-server'
        );
        
        container.appendChild(supabaseCard);
        container.appendChild(localhostCard);
    }

    createDatabaseStatusCard(title, status, details, tableCount, icon) {
        const div = document.createElement('div');
        div.className = 'col-md-6 mb-3';
        
        const statusClass = this.getStatusClass(status);
        const statusText = this.getStatusText(status);
        const badgeClass = this.getStatusBadgeClass(status);
        
        div.innerHTML = `
            <div class="card h-100">
                <div class="card-body text-center">
                    <div class="mb-3">
                        <i class="${icon} fa-2x ${statusClass === 'status-success' ? 'text-success' : statusClass === 'status-danger' ? 'text-danger' : 'text-warning'}"></i>
                    </div>
                    <h6 class="card-title">${title}</h6>
                    <p class="card-text small text-muted">${details}</p>
                    <div class="mb-2">
                        <span class="badge ${badgeClass}">${statusText}</span>
                    </div>
                    <div class="small text-muted">
                        <i class="fas fa-table me-1"></i>
                        ${tableCount} tables
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }

    updateStatusIndicator(overallStatus) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        if (overallStatus === 'healthy') {
            indicator.className = 'fas fa-circle text-success me-1';
            text.textContent = 'System Online';
        } else {
            indicator.className = 'fas fa-circle text-danger me-1';
            text.textContent = 'System Issues';
        }
    }

    async loadDashboardData() {
        try {
            const [statsResponse, activityResponse] = await Promise.all([
                fetch(`${this.apiBase}/stats`),
                fetch(`${this.apiBase}/activity`)
            ]);
            
            const stats = await statsResponse.json();
            const activity = await activityResponse.json();
            
            this.updateStatsCards(stats);
            this.updateRecentActivity(activity);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    updateStatsCards(stats) {
        const container = document.getElementById('stats-cards');
        container.innerHTML = '';

        const statCards = [
            {
                number: stats.total_files || 0,
                label: 'Total Files Processed',
                icon: 'fas fa-file'
            },
            {
                number: stats.files_today || 0,
                label: 'Files Processed Today',
                icon: 'fas fa-calendar-day'
            },
            {
                number: this.formatBytes(stats.total_size || 0),
                label: 'Total Data Processed',
                icon: 'fas fa-hdd'
            },
            {
                number: stats.success_rate || 0,
                label: 'Success Rate (%)',
                icon: 'fas fa-chart-line'
            }
        ];

        statCards.forEach(stat => {
            const cardElement = this.createStatCard(stat);
            container.appendChild(cardElement);
        });
    }

    createStatCard(stat) {
        const div = document.createElement('div');
        div.className = 'col-md-3 col-sm-6 mb-3';
        
        div.innerHTML = `
            <div class="stat-card">
                <div class="stat-number">${stat.number}</div>
                <div class="stat-label">${stat.label}</div>
            </div>
        `;
        
        return div;
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('recent-activity');
        container.innerHTML = '';

        if (!activities || activities.length === 0) {
            container.innerHTML = '<p class="text-muted">No recent activity</p>';
            return;
        }

        activities.forEach(activity => {
            const activityElement = this.createActivityItem(activity);
            container.appendChild(activityElement);
        });
    }

    createActivityItem(activity) {
        const div = document.createElement('div');
        div.className = `activity-item activity-${activity.type}`;
        
        const icon = this.getActivityIcon(activity.type);
        const timeAgo = this.formatTimeAgo(activity.timestamp);
        
        div.innerHTML = `
            <div class="activity-icon">
                <i class="${icon}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${activity.title}</div>
                <div class="activity-time">${timeAgo}</div>
            </div>
        `;
        
        return div;
    }

    getActivityIcon(type) {
        switch(type) {
            case 'success': return 'fas fa-check-circle';
            case 'warning': return 'fas fa-exclamation-triangle';
            case 'danger': return 'fas fa-times-circle';
            case 'info': return 'fas fa-info-circle';
            default: return 'fas fa-circle';
        }
    }

    async loadConfiguration() {
        try {
            const response = await fetch(`${this.apiBase}/config`);
            const config = await response.json();
            
            if (config.error) {
                this.showAlert(`Configuration error: ${config.error}`, 'danger');
                return;
            }
            
            this.updateFeatureToggles(config.feature_toggles || {});
            this.updateConfigDisplay(config.settings || {});
        } catch (error) {
            console.error('Failed to load configuration:', error);
            this.showAlert('Failed to load configuration', 'danger');
        }
    }

    updateFeatureToggles(toggles) {
        const container = document.getElementById('feature-toggles');
        container.innerHTML = '';

        Object.entries(toggles).forEach(([key, toggleData]) => {
            const value = toggleData.value;
            const description = toggleData.description || 'Feature toggle';
            const toggleElement = this.createFeatureToggle(key, value, description);
            container.appendChild(toggleElement);
        });
    }

    createFeatureToggle(key, value, description) {
        const div = document.createElement('div');
        div.className = 'col-md-6 mb-3';
        
        const label = this.formatToggleLabel(key);
        
        div.innerHTML = `
            <div class="feature-toggle">
                <div>
                    <label class="form-check-label fw-bold">${label}</label>
                    <div class="small text-muted">${description}</div>
                    <div class="small text-muted">${key}</div>
                </div>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           id="toggle-${key}" ${value ? 'checked' : ''} 
                           onchange="dashboard.toggleFeature('${key}', this.checked)">
                </div>
            </div>
        `;
        
        return div;
    }

    formatToggleLabel(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    getToggleDescription(key) {
        const descriptions = {
            'ENABLE_ICLOUD_UPLOAD': 'Upload files to iCloud Photos',
            'ENABLE_PIXEL_UPLOAD': 'Sync files to Google Photos via Pixel',
            'ENABLE_COMPRESSION': 'Compress media files to save space',
            'ENABLE_DEDUPLICATION': 'Remove duplicate files',
            'ENABLE_SORTING': 'Organize files by date after upload'
        };
        return descriptions[key] || 'Feature toggle';
    }

    async toggleFeature(key, enabled) {
        try {
            const response = await fetch(`${this.apiBase}/config/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ key, enabled })
            });
            
            if (response.ok) {
                this.showAlert(`Feature ${key} ${enabled ? 'enabled' : 'disabled'}`, 'success');
            } else {
                throw new Error('Failed to update feature toggle');
            }
        } catch (error) {
            console.error('Failed to toggle feature:', error);
            this.showAlert('Failed to update feature toggle', 'danger');
            // Revert the toggle
            document.getElementById(`toggle-${key}`).checked = !enabled;
        }
    }

    updateConfigDisplay(settings) {
        const container = document.getElementById('config-display');
        container.innerHTML = '';

        // Group settings by category
        const categories = {};
        Object.entries(settings).forEach(([key, settingData]) => {
            // Handle both old format (string value) and new format (object with value, description, category)
            let data;
            if (typeof settingData === 'string') {
                data = {
                    value: settingData,
                    description: `Configuration option: ${key.replace(/_/g, ' ').toLowerCase()}`,
                    category: 'General'
                };
            } else {
                data = settingData;
            }
            
            const category = data.category || 'General';
            if (!categories[category]) {
                categories[category] = [];
            }
            categories[category].push([key, data]);
        });

        // Display each category
        Object.entries(categories).forEach(([categoryName, categorySettings]) => {
            // Category header
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'mb-4';
            categoryDiv.innerHTML = `
                <h6 class="text-primary border-bottom pb-2">${categoryName}</h6>
            `;
            container.appendChild(categoryDiv);

            // Settings in this category
            categorySettings.forEach(([key, settingData]) => {
                const value = settingData.value;
                const description = settingData.description || 'Configuration option';
                const displayName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const isPassword = key.toLowerCase().includes('password') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('key');
                const inputType = isPassword ? 'password' : 'text';

                const div = document.createElement('div');
                div.className = 'row mb-3 config-item';
                div.innerHTML = `
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <strong>${displayName}</strong>
                                        <div class="small text-muted">${key}</div>
                                    </div>
                                    <div class="col-md-6">
                                        <input type="${inputType}" class="form-control config-input" 
                                               data-key="${key}" value="${value}" 
                                               onchange="updateConfigInline('${key}', this.value)">
                                        <div class="form-text">${description}</div>
                                    </div>
                                    <div class="col-md-2">
                                        <button class="btn btn-outline-primary" 
                                                onclick="updateConfigInline('${key}', document.querySelector('[data-key=\\'${key}\\']').value)">
                                            <i class="fas fa-save"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(div);
            });
        });
    }

    async loadLogs() {
        const logType = document.getElementById('log-type').value;
        const lines = document.getElementById('log-lines').value;
        
        try {
            const response = await fetch(`${this.apiBase}/logs?type=${logType}&lines=${lines}`);
            const data = await response.json();
            
            const logContent = document.getElementById('log-content');
            logContent.textContent = data.content || 'No logs available';
            
            // Scroll to bottom
            logContent.scrollTop = logContent.scrollHeight;
        } catch (error) {
            console.error('Failed to load logs:', error);
            this.showAlert('Failed to load logs', 'danger');
        }
    }

    async loadTroubleshootingGuide() {
        const container = document.getElementById('troubleshooting-guide');
        container.innerHTML = '';

        const issues = [
            {
                title: 'Service Not Starting',
                description: 'The media pipeline service fails to start or keeps restarting.',
                solution: 'Run: sudo ./scripts/check_and_fix.sh --fix-permissions'
            },
            {
                title: 'iCloud Authentication Failed',
                description: 'Cannot authenticate with iCloud or download fails.',
                solution: 'Check credentials in config/settings.env and ensure 2FA is enabled'
            },
            {
                title: 'Syncthing Web Interface Not Accessible',
                description: 'Cannot access Syncthing web interface at http://IP:8384.',
                solution: 'Run: sudo ./scripts/check_and_fix.sh --fix-syncthing'
            },
            {
                title: 'Permission Errors',
                description: 'Permission denied errors when accessing files or directories.',
                solution: 'Run: sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline'
            },
            {
                title: 'Database Connection Issues',
                description: 'Supabase connection fails or database operations error.',
                solution: 'Verify SUPABASE_URL and SUPABASE_KEY in settings.env'
            }
        ];

        issues.forEach(issue => {
            const issueElement = this.createTroubleshootItem(issue);
            container.appendChild(issueElement);
        });
    }

    createTroubleshootItem(issue) {
        const div = document.createElement('div');
        div.className = 'troubleshoot-item';
        
        div.innerHTML = `
            <div class="troubleshoot-title">${issue.title}</div>
            <div class="troubleshoot-description">${issue.description}</div>
            <div class="troubleshoot-solution">${issue.solution}</div>
        `;
        
        return div;
    }

    async loadAnalytics() {
        console.log('Loading analytics...');
        try {
            await this.loadPerformanceMetrics();
            await this.loadProcessingCharts();
            await this.loadHealthMetrics();
            console.log('Analytics loaded successfully');
        } catch (error) {
            console.error('Failed to load analytics:', error);
        }
    }
    
    async loadPerformanceMetrics() {
        console.log('Loading performance metrics...');
        try {
            const [statusResponse, sourcesResponse, cacheResponse] = await Promise.all([
                fetch('/api/status'),
                fetch('/api/sources/status'),
                fetch('/api/cache/stats')
            ]);
            
            const status = await statusResponse.json();
            const sources = await sourcesResponse.json();
            const cache = await cacheResponse.json();
            
            console.log('API responses:', { status, sources, cache });
            
            const metricsContainer = document.getElementById('performance-metrics');
            if (metricsContainer) {
                const totalFiles = Object.values(sources.source_stats).reduce((sum, stats) => sum + stats.file_count, 0);
                const totalSize = Object.values(sources.source_stats).reduce((sum, stats) => sum + parseFloat(stats.total_size_mb), 0);
                
                metricsContainer.innerHTML = `
                    <div class="col-md-3 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-primary">${totalFiles}</h5>
                                <p class="card-text">Total Files</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-success">${totalSize.toFixed(1)} MB</h5>
                                <p class="card-text">Total Size</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title text-info">${sources.enabled_sources.length}</h5>
                                <p class="card-text">Active Sources</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title ${status.overall_status === 'healthy' ? 'text-success' : 'text-warning'}">${status.overall_status}</h5>
                                <p class="card-text">System Status</p>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load performance metrics:', error);
        }
    }
    
    async loadProcessingCharts() {
        try {
            const sourcesResponse = await fetch('/api/sources/status');
            const sources = await sourcesResponse.json();
            
            // Processing Chart
            const processingCtx = document.getElementById('processing-chart');
            if (processingCtx) {
                const labels = Object.keys(sources.source_stats).map(source => 
                    source === 'icloud' ? 'iCloud Photos' : 'Local Folder'
                );
                const fileCounts = Object.values(sources.source_stats).map(stats => stats.file_count);
                const processedCounts = Object.values(sources.source_stats).map(stats => stats.processed_count);
                
                new Chart(processingCtx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Total Files',
                            data: fileCounts,
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }, {
                            label: 'Processed Files',
                            data: processedCounts,
                            backgroundColor: 'rgba(75, 192, 192, 0.5)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'File Processing Status'
                            }
                        }
                    }
                });
                
                // Show the chart and hide loading spinner
                processingCtx.style.display = 'block';
                const processingSpinner = processingCtx.parentElement.querySelector('.spinner-border');
                const processingText = processingCtx.parentElement.querySelector('p');
                if (processingSpinner) processingSpinner.style.display = 'none';
                if (processingText) processingText.style.display = 'none';
            }
            
            // Storage Chart
            const storageCtx = document.getElementById('storage-chart');
            if (storageCtx) {
                const labels = Object.keys(sources.source_stats).map(source => 
                    source === 'icloud' ? 'iCloud Photos' : 'Local Folder'
                );
                const sizes = Object.values(sources.source_stats).map(stats => parseFloat(stats.total_size_mb));
                
                new Chart(storageCtx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: sizes,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.5)',
                                'rgba(54, 162, 235, 0.5)'
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Storage Distribution (MB)'
                            }
                        }
                    }
                });
                
                // Show the chart and hide loading spinner
                storageCtx.style.display = 'block';
                const storageSpinner = storageCtx.parentElement.querySelector('.spinner-border');
                const storageText = storageCtx.parentElement.querySelector('p');
                if (storageSpinner) storageSpinner.style.display = 'none';
                if (storageText) storageText.style.display = 'none';
            }
        } catch (error) {
            console.error('Failed to load processing charts:', error);
        }
    }
    
    async loadHealthMetrics() {
        try {
            const statusResponse = await fetch('/api/status');
            const status = await statusResponse.json();
            
            const healthContainer = document.getElementById('health-metrics');
            if (healthContainer) {
                const services = status.services || {};
                const database = status.database || {};
                const storage = status.storage || {};
                
                healthContainer.innerHTML = `
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">Services Status</h6>
                                    ${Object.entries(services).map(([service, status]) => `
                                        <div class="d-flex justify-content-between align-items-center mb-2">
                                            <span>${service}</span>
                                            <span class="badge ${status === 'running' ? 'bg-success' : 'bg-danger'}">${status}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">Database Health</h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Connection</span>
                                        <span class="badge ${database.connected ? 'bg-success' : 'bg-danger'}">${database.connected ? 'Connected' : 'Disconnected'}</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Tables</span>
                                        <span class="badge bg-info">${database.tables || 0}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">Storage Health</h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Mount Status</span>
                                        <span class="badge ${storage.mounted ? 'bg-success' : 'bg-danger'}">${storage.mounted ? 'Mounted' : 'Unmounted'}</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Usage</span>
                                        <span class="badge ${parseFloat(storage.percent) > 80 ? 'bg-danger' : 'bg-success'}">${storage.percent || 0}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load health metrics:', error);
        }
    }

    async loadServices() {
        try {
            await this.loadServicesStatus();
            await refreshCacheStats();
        } catch (error) {
            console.error('Failed to load services:', error);
        }
    }
    
    async loadServicesStatus() {
        try {
            const statusResponse = await fetch('/api/status');
            const status = await statusResponse.json();
            
            const servicesContainer = document.getElementById('services-status');
            if (servicesContainer) {
                const services = status.services || {};
                
                servicesContainer.innerHTML = `
                    <div class="row">
                        ${Object.entries(services).map(([service, status]) => `
                            <div class="col-md-6 mb-3">
                                <div class="card">
                                    <div class="card-body">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h6 class="card-title mb-1">${service}</h6>
                                                <small class="text-muted">System Service</small>
                                            </div>
                                            <span class="badge ${status === 'running' ? 'bg-success' : 'bg-danger'} fs-6">
                                                ${status === 'running' ? 'Running' : 'Stopped'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load services status:', error);
        }
    }
    
    async testIcloudConnection() {
        try {
            const response = await fetch('/api/test/icloud', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.showAlert('iCloud connection test successful!', 'success');
            } else {
                this.showAlert(`iCloud connection test failed: ${result.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert('Failed to test iCloud connection', 'danger');
        }
    }

    async loadReadme() {
        try {
            const response = await fetch('/api/readme');
            const data = await response.json();
            
            const container = document.getElementById('readme-content');
            container.innerHTML = `
                <div class="readme-content">
                    ${data.content}
                </div>
            `;
        } catch (error) {
            const container = document.getElementById('readme-content');
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Could not load README content. Please check the server logs.
                </div>
            `;
        }
    }

    async loadDocumentation() {
        try {
            const response = await fetch('/api/docs/list');
            const data = await response.json();
            
            if (data.success) {
                this.displayDocumentationList(data.files);
            } else {
                this.showAlert('Failed to load documentation files', 'danger');
            }
        } catch (error) {
            console.error('Failed to load documentation:', error);
            this.showAlert('Failed to load documentation files', 'danger');
        }
    }

    displayDocumentationList(files) {
        const container = document.getElementById('docs-list');
        container.innerHTML = '';

        if (files.length === 0) {
            container.innerHTML = '<div class="text-muted">No documentation files found</div>';
            return;
        }

        files.forEach(file => {
            const fileElement = this.createDocumentationItem(file);
            container.appendChild(fileElement);
        });
    }

    createDocumentationItem(file) {
        const div = document.createElement('div');
        div.className = 'list-group-item list-group-item-action';
        div.style.cursor = 'pointer';
        
        const sizeKB = Math.round(file.size / 1024);
        const modifiedDate = new Date(file.modified).toLocaleDateString();
        
        div.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">
                    <i class="fas fa-file-alt me-2"></i>
                    ${file.name}
                </h6>
                <small>${sizeKB} KB</small>
            </div>
            <p class="mb-1 text-muted small">${file.path}</p>
            <small class="text-muted">Modified: ${modifiedDate}</small>
        `;
        
        div.addEventListener('click', () => {
            this.loadDocumentContent(file.path);
        });
        
        return div;
    }

    async loadDocumentContent(filePath) {
        try {
            const response = await fetch(`/api/docs/read/${encodeURIComponent(filePath)}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayDocumentContent(data);
            } else {
                this.showAlert(`Failed to load document: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error('Failed to load document content:', error);
            this.showAlert('Failed to load document content', 'danger');
        }
    }

    displayDocumentContent(data) {
        const container = document.getElementById('docs-viewer');
        
        // Convert markdown to HTML (basic conversion)
        const htmlContent = this.markdownToHtml(data.content);
        
        container.innerHTML = `
            <div class="document-header mb-3">
                <h5><i class="fas fa-file-alt me-2"></i>${data.filename}</h5>
                <div class="text-muted small">
                    Size: ${Math.round(data.size / 1024)} KB | 
                    Modified: ${new Date(data.modified).toLocaleString()}
                </div>
            </div>
            <div class="document-content">
                ${htmlContent}
            </div>
        `;
    }

    markdownToHtml(markdown) {
        // Basic markdown to HTML conversion
        let html = markdown
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            // Code blocks
            .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
            // Line breaks
            .replace(/\n\n/gim, '</p><p>')
            .replace(/\n/gim, '<br>');
        
        // Wrap in paragraphs
        html = '<p>' + html + '</p>';
        
        return html;
    }

    async loadTelegramConfigAuto() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            
            const tokenField = document.getElementById('telegram-bot-token');
            const chatIdField = document.getElementById('telegram-chat-id');
            
            if (tokenField && chatIdField) {
                tokenField.value = config.settings.TELEGRAM_BOT_TOKEN || '';
                chatIdField.value = config.settings.TELEGRAM_CHAT_ID || '';
            }
            
            // Load and display current status
            await this.loadTelegramStatus();
        } catch (error) {
            console.error('Failed to load Telegram config:', error);
        }
    }
    
    async loadTelegramStatus() {
        try {
            const response = await fetch('/api/telegram/status');
            const status = await response.json();
            
            const statusText = document.getElementById('telegram-status-text');
            if (statusText) {
                let statusMessage = '';
                if (status.bot_configured) {
                    statusMessage = `✅ Bot configured and ${status.service_status}`;
                } else {
                    statusMessage = '❌ Bot not configured';
                }
                statusMessage += ` | Active 2FA requests: ${status.active_2fa_requests}`;
                statusText.textContent = statusMessage;
            }
        } catch (error) {
            console.error('Failed to load Telegram status:', error);
            const statusText = document.getElementById('telegram-status-text');
            if (statusText) {
                statusText.textContent = '❌ Failed to load status';
            }
        }
    }
    
    async loadSourcesStatus() {
        try {
            const response = await fetch('/api/sources/status');
            const data = await response.json();
            
            const sourcesDisplay = document.getElementById('sources-status-display');
            if (sourcesDisplay) {
                let html = '<div class="row">';
                
                data.enabled_sources.forEach(source => {
                    const stats = data.source_stats[source] || { file_count: 0, total_size_mb: 0, processed_count: 0, pending_count: 0 };
                    const sourceName = source === 'icloud' ? 'iCloud Photos' : 'Local Folder';
                    const icon = source === 'icloud' ? 'fas fa-cloud' : 'fas fa-folder';
                    
                    html += `
                        <div class="col-md-6 mb-3">
                            <div class="card border-primary">
                                <div class="card-body">
                                    <h6 class="card-title">
                                        <i class="${icon} me-2"></i>
                                        ${sourceName}
                                    </h6>
                                    <div class="row text-center">
                                        <div class="col-6">
                                            <div class="text-primary fw-bold">${stats.file_count}</div>
                                            <small class="text-muted">Files</small>
                                        </div>
                                        <div class="col-6">
                                            <div class="text-success fw-bold">${stats.total_size_mb} MB</div>
                                            <small class="text-muted">Total Size</small>
                                        </div>
                                    </div>
                                    <div class="mt-2">
                                        <small class="text-muted">
                                            Processed: ${stats.processed_count} | Pending: ${stats.pending_count}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                
                if (data.enabled_sources.length === 0) {
                    html = '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>No media sources are currently enabled.</div>';
                }
                
                sourcesDisplay.innerHTML = html;
            }
        } catch (error) {
            console.error('Failed to load sources status:', error);
            const sourcesDisplay = document.getElementById('sources-status-display');
            if (sourcesDisplay) {
                sourcesDisplay.innerHTML = '<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Failed to load sources status.</div>';
            }
        }
    }

    // Pipeline Control Methods
    async runStep(step) {
        this.showProgressModal(`Running ${step}...`);
        
        try {
            const response = await fetch(`${this.apiBase}/pipeline/step`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ step })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`${step} completed successfully`, 'success');
            } else {
                this.showAlert(`${step} failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error(`Failed to run ${step}:`, error);
            this.showAlert(`Failed to run ${step}`, 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    async runFullPipeline() {
        this.showProgressModal('Running complete pipeline...');
        
        try {
            const response = await fetch(`${this.apiBase}/pipeline/run`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Pipeline completed successfully', 'success');
            } else {
                this.showAlert(`Pipeline failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error('Failed to run pipeline:', error);
            this.showAlert('Failed to run pipeline', 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    async runHealthCheck() {
        this.showProgressModal('Running health check...');
        
        try {
            const response = await fetch(`${this.apiBase}/health-check`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Health check completed', 'success');
                this.loadSystemStatus(); // Refresh status
            } else {
                this.showAlert(`Health check found issues: ${data.issues}`, 'warning');
            }
        } catch (error) {
            console.error('Failed to run health check:', error);
            this.showAlert('Failed to run health check', 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    async serviceAction(service, action) {
        this.showProgressModal(`${action} ${service}...`);
        
        try {
            const response = await fetch(`${this.apiBase}/service/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ service })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`${service} ${action} successful`, 'success');
                this.loadSystemStatus(); // Refresh status
            } else {
                this.showAlert(`${service} ${action} failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error(`Failed to ${action} ${service}:`, error);
            this.showAlert(`Failed to ${action} ${service}`, 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    // Manual pipeline execution methods
    async runManualPipeline(action) {
        this.showProgressModal(`Running manual pipeline: ${action}...`);
        
        try {
            let url = `${this.apiBase}/manual-pipeline/${action}`;
            let options = { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (action === 'interval') {
                const interval = document.getElementById('customInterval').value;
                if (!interval || interval < 1 || interval > 1440) {
                    this.showAlert('Please enter a valid interval (1-1440 minutes)', 'warning');
                    return;
                }
                options.body = JSON.stringify({ interval: parseInt(interval) });
            }
            
            const response = await fetch(url, options);
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Manual execution started successfully`, 'success');
                if (action === 'status' && data.data) {
                    this.displayManualStatus(data.data);
                }
            } else {
                this.showAlert(`Manual execution failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showAlert(`Error: ${error.message}`, 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    displayManualStatus(statusData) {
        const statusModal = document.createElement('div');
        statusModal.className = 'modal fade';
        statusModal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-info-circle me-2"></i>
                            Pipeline Status
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre class="bg-dark text-light p-3 rounded">${statusData}</pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(statusModal);
        const modal = new bootstrap.Modal(statusModal);
        modal.show();
        
        statusModal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(statusModal);
        });
    }

    async runDiagnostic(type) {
        this.showProgressModal(`Running ${type} diagnostic...`);
        
        try {
            const response = await fetch(`${this.apiBase}/diagnostic/${type}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`${type} diagnostic completed`, 'success');
            } else {
                this.showAlert(`${type} diagnostic found issues: ${data.issues}`, 'warning');
            }
        } catch (error) {
            console.error(`Failed to run ${type} diagnostic:`, error);
            this.showAlert(`Failed to run ${type} diagnostic`, 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    async runAutoFix(type) {
        this.showProgressModal(`Running auto-fix for ${type}...`);
        
        try {
            const response = await fetch(`${this.apiBase}/auto-fix/${type}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`${type} auto-fix completed`, 'success');
                this.loadSystemStatus(); // Refresh status
            } else {
                this.showAlert(`${type} auto-fix failed: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error(`Failed to run ${type} auto-fix:`, error);
            this.showAlert(`Failed to run ${type} auto-fix`, 'danger');
        } finally {
            this.hideProgressModal();
        }
    }

    // Utility Methods
    showProgressModal(title) {
        document.getElementById('progressTitle').textContent = title;
        document.getElementById('progressText').textContent = 'Starting...';
        document.getElementById('progressBar').style.width = '0%';
        
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
    }

    hideProgressModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        if (modal) {
            modal.hide();
        }
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container');
        const alertId = 'alert-' + Date.now();
        
        const alertDiv = document.createElement('div');
        alertDiv.id = alertId;
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        return `${Math.floor(diffInSeconds / 86400)} days ago`;
    }

    startAutoRefresh() {
        setInterval(() => {
            this.loadSystemStatus();
        }, this.refreshInterval);
    }

    startLogAutoRefresh() {
        if (this.logRefreshInterval) {
            clearInterval(this.logRefreshInterval);
        }
        
        this.logRefreshInterval = setInterval(() => {
            if (this.isLogAutoRefresh) {
                this.loadLogs();
            }
        }, 10000);
    }

    initTheme() {
        // Load saved theme preference
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    // Configuration Management
    async openConfigEditor() {
        try {
            const response = await fetch(`${this.apiBase}/config/open-editor`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('Configuration editor opened successfully', 'success');
            } else {
                this.showAlert(`Failed to open editor: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error('Failed to open config editor:', error);
            this.showAlert('Failed to open configuration editor', 'danger');
        }
    }
    
    async editConfigValue(key, value) {
        try {
            const response = await fetch(`${this.apiBase}/config/edit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ key, value })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert(`Configuration updated: ${key}`, 'success');
                this.loadConfiguration(); // Reload config display
            } else {
                this.showAlert(`Failed to update ${key}: ${data.error}`, 'danger');
            }
        } catch (error) {
            console.error('Failed to edit config:', error);
            this.showAlert('Failed to update configuration', 'danger');
        }
    }

    async reloadConfig() {
        try {
            const response = await fetch(`${this.apiBase}/config/reload`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showAlert('Configuration reloaded successfully', 'success');
                this.loadConfiguration();
            } else {
                throw new Error('Failed to reload configuration');
            }
        } catch (error) {
            console.error('Failed to reload configuration:', error);
            this.showAlert('Failed to reload configuration', 'danger');
        }
    }

    async clearLogs() {
        try {
            const logType = document.getElementById('log-type').value;
            
            if (logType === 'pipeline') {
                // Clear pipeline log file
                const response = await fetch('/api/logs/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        log_type: logType
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showAlert('Log file cleared successfully', 'success');
                    this.loadLogs(); // Reload logs
                } else {
                    this.showAlert('Failed to clear log file: ' + data.error, 'danger');
                }
            } else {
                // For other log types, just clear the display
                document.getElementById('log-content').textContent = '';
                this.showAlert('Log display cleared', 'info');
            }
        } catch (error) {
            this.showAlert('Error clearing logs: ' + error.message, 'danger');
        }
    }
}

// Global functions for button onclick handlers
function refreshStatus() {
    dashboard.loadSystemStatus();
}

function runStep(step) {
    dashboard.runStep(step);
}

function runFullPipeline() {
    dashboard.runFullPipeline();
}

function runHealthCheck() {
    dashboard.runHealthCheck();
}

function serviceAction(service, action) {
    dashboard.serviceAction(service, action);
}

function runDiagnostic(type) {
    dashboard.runDiagnostic(type);
}

function runAutoFix(type) {
    dashboard.runAutoFix(type);
}

function loadLogs() {
    dashboard.loadLogs();
}

function clearLogs() {
    dashboard.clearLogs();
}

function openConfigEditor() {
    dashboard.openConfigEditor();
}

function reloadConfig() {
    dashboard.reloadConfig();
}

function showInlineEditor() {
    document.getElementById('inline-editor').style.display = 'block';
}

function hideInlineEditor() {
    document.getElementById('inline-editor').style.display = 'none';
    document.getElementById('config-key').value = '';
    document.getElementById('config-value').value = '';
}

function updateConfigValue() {
    const key = document.getElementById('config-key').value.trim();
    const value = document.getElementById('config-value').value.trim();
    
    if (!key || !value) {
        dashboard.showAlert('Please enter both key and value', 'warning');
        return;
    }
    
    dashboard.editConfigValue(key, value);
    hideInlineEditor();
}

// Telegram Bot Functions (simplified for Configuration tab)
async function testTelegramBot() {
    showTelegramStatus('Testing bot connection...', 'info');
    
    try {
        // Get current config values
        const response = await fetch('/api/config');
        const config = await response.json();
        
        const botToken = config.settings.TELEGRAM_BOT_TOKEN?.value || '';
        const chatId = config.settings.TELEGRAM_CHAT_ID?.value || '';
        
        if (!botToken || !chatId) {
            showTelegramStatus('❌ Telegram bot token or chat ID not configured. Please set them in the configuration below.', 'warning');
            return;
        }
        
        const testResponse = await fetch('/api/telegram/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                bot_token: botToken,
                chat_id: chatId
            })
        });
        
        const data = await testResponse.json();
        
        if (data.success) {
            showTelegramStatus('✅ ' + data.message, 'success');
        } else {
            showTelegramStatus('❌ ' + data.message, 'danger');
        }
    } catch (error) {
        showTelegramStatus('❌ Bot test failed: ' + error.message, 'danger');
    }
}

function showTelegramStatus(message, type) {
    const statusDiv = document.getElementById('telegram-status');
    statusDiv.textContent = message;
    statusDiv.className = `alert alert-${type}`;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds for success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// Enhanced Telegram Functions
async function sendTelegramStatus() {
    try {
        const response = await fetch('/api/telegram/send-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            showTelegramStatus('✅ Status update sent to Telegram', 'success');
        } else {
            showTelegramStatus(`❌ Failed to send status: ${data.message}`, 'danger');
        }
    } catch (error) {
        showTelegramStatus(`❌ Error sending status: ${error.message}`, 'danger');
    }
}

async function sendTelegramSummary() {
    try {
        const response = await fetch('/api/telegram/send-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            showTelegramStatus('✅ Daily summary sent to Telegram', 'success');
        } else {
            showTelegramStatus(`❌ Failed to send summary: ${data.message}`, 'danger');
        }
    } catch (error) {
        showTelegramStatus(`❌ Error sending summary: ${error.message}`, 'danger');
    }
}

async function checkTelegramStatus() {
    try {
        const response = await fetch('/api/telegram/status');
        const data = await response.json();
        
        let statusMessage = `📊 Telegram Bot Status:\n`;
        statusMessage += `🔧 Service: ${data.service_status}\n`;
        statusMessage += `🔐 Active 2FA Requests: ${data.active_2fa_requests}\n`;
        statusMessage += `⚙️ Bot Configured: ${data.bot_configured ? 'Yes' : 'No'}`;
        
        showTelegramStatus(statusMessage, 'info');
        
        // Update the status display
        const statusText = document.getElementById('telegram-status-text');
        if (statusText) {
            let displayMessage = '';
            if (data.bot_configured) {
                displayMessage = `✅ Bot configured and ${data.service_status}`;
            } else {
                displayMessage = '❌ Bot not configured';
            }
            displayMessage += ` | Active 2FA requests: ${data.active_2fa_requests}`;
            statusText.textContent = displayMessage;
        }
    } catch (error) {
        showTelegramStatus(`❌ Error checking status: ${error.message}`, 'danger');
    }
}

// Cache Management Functions
async function refreshCacheStats() {
    try {
        console.log('refreshCacheStats called');
        const response = await fetch('/api/cache/stats');
        const data = await response.json();
        console.log('API response:', data);
        
        if (data.success) {
            displayCacheStats(data);
            showCacheStatus('✅ Cache statistics refreshed', 'success');
        } else {
            showCacheStatus(`❌ Failed to get cache stats: ${data.message}`, 'danger');
        }
    } catch (error) {
        console.error('refreshCacheStats error:', error);
        showCacheStatus(`❌ Error refreshing cache stats: ${error.message}`, 'danger');
    }
}

function displayCacheStats(data) {
    console.log('displayCacheStats called with data:', data);
    const statsDiv = document.getElementById('cache-stats');
    const redisInfoDiv = document.getElementById('redis-info');
    
    const stats = data.stats || {};
    const databaseInfo = data.database_info || {};
    const syncTimestamps = data.sync_timestamps || {};
    console.log('Stats object:', stats);
    console.log('Sync timestamps:', syncTimestamps);
    
    // Calculate totals
    const totalRecords = (stats.pipeline_logs_count || 0) + 
                        (stats.telegram_2fa_requests_count || 0) + 
                        (stats.telegram_notifications_count || 0) + 
                        (stats.cache_metrics_count || 0) + 
                        (stats.pipeline_metrics_count || 0);
    
    const totalUnsynced = (stats.pipeline_logs_unsynced || 0) + 
                         (stats.telegram_2fa_requests_unsynced || 0) + 
                         (stats.telegram_notifications_unsynced || 0) + 
                         (stats.cache_metrics_unsynced || 0) + 
                         (stats.pipeline_metrics_unsynced || 0);
    
    const syncRate = totalRecords > 0 ? ((totalRecords - totalUnsynced) / totalRecords * 100).toFixed(1) : 100;
    
    let syncRateColor = 'success';
    if (syncRate < 80) syncRateColor = 'danger';
    else if (syncRate < 95) syncRateColor = 'warning';
    
    statsDiv.innerHTML = `
        <div class="row">
            <div class="col-6">
                <div class="text-center">
                    <div class="h4 text-${syncRateColor}">${syncRate}%</div>
                    <small class="text-muted">Sync Rate</small>
                </div>
            </div>
            <div class="col-6">
                <div class="text-center">
                    <div class="h4 text-primary">${totalRecords}</div>
                    <small class="text-muted">Total Records</small>
                </div>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-6">
                <small><strong>Pipeline Logs:</strong> ${stats.pipeline_logs_count || 0}</small><br>
                <small><strong>2FA Requests:</strong> ${stats.telegram_2fa_requests_count || 0}</small><br>
                <small><strong>Notifications:</strong> ${stats.telegram_notifications_count || 0}</small>
            </div>
            <div class="col-6">
                <small><strong>Cache Metrics:</strong> ${stats.cache_metrics_count || 0}</small><br>
                <small><strong>Pipeline Metrics:</strong> ${stats.pipeline_metrics_count || 0}</small><br>
                <small><strong>Unsynced:</strong> ${totalUnsynced}</small>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-12">
                <small class="text-muted">
                    <strong>Last Sync Times:</strong><br>
                    Pipeline Logs: ${syncTimestamps.pipeline_logs ? new Date(syncTimestamps.pipeline_logs).toLocaleString() : 'Never'}<br>
                    2FA Requests: ${syncTimestamps.telegram_2fa_requests ? new Date(syncTimestamps.telegram_2fa_requests).toLocaleString() : 'Never'}<br>
                    Notifications: ${syncTimestamps.telegram_notifications ? new Date(syncTimestamps.telegram_notifications).toLocaleString() : 'Never'}<br>
                    Cache Metrics: ${syncTimestamps.cache_metrics ? new Date(syncTimestamps.cache_metrics).toLocaleString() : 'Never'}<br>
                    Pipeline Metrics: ${syncTimestamps.pipeline_metrics ? new Date(syncTimestamps.pipeline_metrics).toLocaleString() : 'Never'}
                </small>
            </div>
        </div>
    `;
    
    // Display database information
    redisInfoDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <small><strong>Database Type:</strong> ${databaseInfo.type || 'PostgreSQL'}</small><br>
                <small><strong>Host:</strong> ${databaseInfo.host || 'localhost'}</small><br>
                <small><strong>Port:</strong> ${databaseInfo.port || '5432'}</small>
            </div>
            <div class="col-md-6">
                <small><strong>Database:</strong> ${databaseInfo.database || 'media_pipeline'}</small><br>
                <small><strong>Status:</strong> <span class="text-success">Connected</span></small><br>
                <small><strong>Sync:</strong> <span class="text-info">Local → Supabase</span></small>
            </div>
        </div>
    `;
}

async function optimizeCache() {
    try {
        const response = await fetch('/api/cache/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            showCacheStatus('✅ Cache optimized successfully', 'success');
            refreshCacheStats(); // Refresh stats after optimization
        } else {
            showCacheStatus(`❌ Failed to optimize cache: ${data.message}`, 'danger');
        }
    } catch (error) {
        showCacheStatus(`❌ Error optimizing cache: ${error.message}`, 'danger');
    }
}

async function clearCache() {
    if (!confirm('Are you sure you want to clear the cache? This will remove all cached data.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            showCacheStatus('✅ Cache cleared successfully', 'success');
            refreshCacheStats(); // Refresh stats after clearing
        } else {
            showCacheStatus(`❌ Failed to clear cache: ${data.message}`, 'danger');
        }
    } catch (error) {
        showCacheStatus(`❌ Error clearing cache: ${error.message}`, 'danger');
    }
}

function showCacheStatus(message, type) {
    const statusDiv = document.getElementById('cache-status');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

// Inline configuration update function
async function updateConfigInline(key, value) {
    try {
        const response = await fetch('/api/config/edit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                key: key,
                value: value
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            dashboard.showAlert(`✅ ${key} updated successfully`, 'success');
        } else {
            dashboard.showAlert(`❌ Failed to update ${key}: ${data.error}`, 'danger');
        }
    } catch (error) {
        dashboard.showAlert(`❌ Error updating ${key}: ${error.message}`, 'danger');
    }
}

// Global documentation function
function loadDocumentation() {
    if (dashboard) {
        dashboard.loadDocumentation();
    }
}

// Global theme toggle function
function toggleTheme() {
    if (dashboard) {
        dashboard.toggleTheme();
    } else {
        // Fallback for when dashboard is not initialized
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
}

// Manual pipeline execution functions
function runManualPipeline(action) {
    if (dashboard) {
        dashboard.runManualPipeline(action);
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new MediaPipelineDashboard();
});