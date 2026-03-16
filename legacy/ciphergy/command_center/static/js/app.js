/**
 * Ciphergy Command Center — Core UI
 * Sidebar, drawer, tabs, auto-refresh, template runner, draft guardian.
 */

/* ---- Sidebar Toggle ---- */

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
    document.getElementById('main-wrapper').classList.toggle('sidebar-collapsed');
}

/* ---- AI Drawer Toggle ---- */

function toggleDrawer() {
    var drawer = document.getElementById('ai-drawer');
    var chevron = document.getElementById('drawer-chevron');
    drawer.classList.toggle('collapsed');
    if (drawer.classList.contains('collapsed')) {
        chevron.innerHTML = '\u25B2';
    } else {
        chevron.innerHTML = '\u25BC';
    }
}

/* ---- Tab Switching ---- */

function switchTab(tabGroup, tabName) {
    var panels = document.querySelectorAll('[data-tab-group="' + tabGroup + '"]');
    var buttons = document.querySelectorAll('[data-tab-btn="' + tabGroup + '"]');
    panels.forEach(function(p) {
        p.style.display = p.getAttribute('data-tab') === tabName ? 'block' : 'none';
    });
    buttons.forEach(function(b) {
        if (b.getAttribute('data-tab-target') === tabName) {
            b.classList.add('tab-active');
        } else {
            b.classList.remove('tab-active');
        }
    });
}

/* ---- Collapsible Sections ---- */

function toggleCollapsible(id) {
    var el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

/* ---- Auto-Refresh (Cascade Feed) ---- */

(function() {
    var refreshInterval = 30000;
    var lastRefresh = Date.now();

    function checkForUpdates() {
        fetch('/api/cascade')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var cascadeEl = document.getElementById('cascade-feed');
                if (cascadeEl && data.length > 0) {
                    var latestTs = data[0].ts || data[0].timestamp || '';
                    var stored = sessionStorage.getItem('last_cascade_ts');
                    if (stored && latestTs !== stored) {
                        location.reload();
                    }
                    sessionStorage.setItem('last_cascade_ts', latestTs);
                }
            })
            .catch(function() {});
    }

    setInterval(checkForUpdates, refreshInterval);

    setInterval(function() {
        var pills = document.querySelectorAll('.deadline-days');
        pills.forEach(function(pill) {
            var days = parseInt(pill.getAttribute('data-days'));
            if (!isNaN(days)) {
                var elapsed = Math.floor((Date.now() - lastRefresh) / 86400000);
                pill.textContent = (days - elapsed) + 'd';
            }
        });
    }, 60000);
})();

/* ---- Template Runner (base drawer) ---- */

function showTemplateInfo() {
    var sel = document.getElementById('template-select');
    document.getElementById('template-info').style.display = sel.value ? 'block' : 'none';
    document.getElementById('prompt-output').style.display = 'none';
}

function generatePrompt() {
    var template = document.getElementById('template-select').value;
    var subject = document.getElementById('template-subject').value;
    var matter = document.getElementById('template-matter').value;
    var names = {
        'entity_analysis': 'Entity Analysis (Person Analysis Report)',
        'output_draft': 'Output Draft (Communication)',
        'source_prep': 'Source Prep (Witness Declaration)',
        'evidence_intake': 'Evidence Intake Scoring',
        'deliverable_checklist': 'Deliverable Checklist (Filing QA)',
        'adversary_playbook': 'Adversary Playbook'
    };
    var prompt = 'Run a full ' + (names[template] || template) + ' for ' + (subject || '[SUBJECT]');
    if (matter) prompt += ' in matter: ' + matter;
    prompt += '. Follow PERSON_ANALYSIS_REPORT_TEMPLATE.md exactly. All 15 sections. Stress-test every claim. Generate both .md and .docx.';
    document.getElementById('prompt-text').value = prompt;
    document.getElementById('prompt-output').style.display = 'block';
}

function copyPrompt() {
    var text = document.getElementById('prompt-text');
    text.select();
    document.execCommand('copy');
    alert('Prompt copied to clipboard. Paste into Claude Code.');
}

/* ---- Toast Notifications ---- */

function showToast(title, text, type) {
    type = type || '';
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast' + (type ? ' toast-' + type : '');
    var icons = { success: '\u2713', warning: '\u26A0', error: '\u2716' };
    toast.innerHTML =
        '<span class="toast-icon">' + (icons[type] || '\u2139') + '</span>' +
        '<div class="toast-body">' +
            '<div class="toast-title">' + title + '</div>' +
            (text ? '<div class="toast-text">' + text + '</div>' : '') +
        '</div>' +
        '<button class="toast-close">&times;</button>';
    container.appendChild(toast);
    setTimeout(function() {
        toast.classList.add('toast-leaving');
        setTimeout(function() { toast.remove(); }, 300);
    }, 5000);
}

/* ---- Auto-wire event handlers (replaces inline onclick attributes) ---- */

document.addEventListener('DOMContentLoaded', function() {
    // Wire sidebar toggle buttons
    document.querySelectorAll('.sidebar-toggle, .menu-btn').forEach(function(btn) {
        btn.addEventListener('click', toggleSidebar);
    });

    // Wire drawer handle
    var drawerHandle = document.querySelector('.ai-drawer-handle');
    if (drawerHandle) {
        drawerHandle.addEventListener('click', toggleDrawer);
    }

    // Wire all tab buttons via data attributes
    document.querySelectorAll('[data-tab-btn][data-tab-target]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var group = this.getAttribute('data-tab-btn');
            var target = this.getAttribute('data-tab-target');
            switchTab(group, target);
        });
    });

    // Wire collapsible headers
    document.querySelectorAll('.collapsible-header').forEach(function(header) {
        header.addEventListener('click', function() {
            var targetId = this.getAttribute('data-collapse-target');
            if (targetId) toggleCollapsible(targetId);
        });
    });

    // Wire template select (base drawer)
    var templateSelect = document.getElementById('template-select');
    if (templateSelect && templateSelect.closest('.ai-drawer-body')) {
        templateSelect.addEventListener('change', showTemplateInfo);
    }

    // Wire generate prompt button (base drawer)
    document.querySelectorAll('[data-action="generate-prompt"]').forEach(function(btn) {
        btn.addEventListener('click', generatePrompt);
    });

    // Wire copy prompt button (base drawer)
    document.querySelectorAll('[data-action="copy-prompt"]').forEach(function(btn) {
        btn.addEventListener('click', copyPrompt);
    });

    // Wire draft check button (base drawer)
    document.querySelectorAll('[data-action="run-draft-check"]').forEach(function(btn) {
        btn.addEventListener('click', runDraftCheck);
    });

    // Wire clear cache button (settings page)
    document.querySelectorAll('[data-action="clear-cache"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (typeof clearCache === 'function') clearCache();
        });
    });

    // Wire toast close buttons (delegate on container)
    var toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
        toastContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('toast-close')) {
                e.target.parentElement.remove();
            }
        });
    }
});

/* ---- Draft Guardian (base drawer) ---- */

function runDraftCheck() {
    var text = document.getElementById('draft-text').value;
    var recipientType = document.getElementById('recipient-type').value;
    if (!text.trim()) { alert('Paste a draft first.'); return; }

    var form = new FormData();
    form.append('text', text);
    form.append('recipient_type', recipientType);

    fetch('/api/draft-check', { method: 'POST', body: form })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var html = '<div style="margin-bottom:8px;"><strong>' +
                (data.passed ? '<span style="color:#28a745;">ALL GATES PASSED</span>' :
                 '<span style="color:#dc3545;">GATE FAILURE</span>') + '</strong></div>';
            data.gates.forEach(function(g) {
                var icon = g.passed ? '\u2713' : '\u2717';
                var color = g.passed ? '#28a745' : '#dc3545';
                html += '<div style="padding:4px 0;border-bottom:1px solid #eee;">' +
                    '<span style="color:' + color + ';">' + icon + '</span> ' +
                    '<strong>' + g.name + '</strong>: ' +
                    '<span style="color:#666;">' + g.notes + '</span></div>';
            });
            document.getElementById('gate-list').innerHTML = html;
            document.getElementById('gate-results').style.display = 'block';
        });
}
