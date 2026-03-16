/**
 * Ciphergy Command Center — Assistant Page
 * Template runner, draft guardian, evidence coach, execution log.
 */
(function() {
    'use strict';

    var templates = [];
    var currentTemplate = null;
    var executions = JSON.parse(localStorage.getItem('ciphergy_executions') || '[]');

    function loadTemplates() {
        fetch('/api/templates')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                templates = data.templates || [];
                populateTemplateSelect();
            })
            .catch(function(err) {
                console.error('Failed to load templates:', err);
            });
    }

    function populateTemplateSelect() {
        var select = document.getElementById('template-select');
        while (select.options.length > 1) {
            select.remove(1);
        }
        templates.forEach(function(t) {
            var opt = document.createElement('option');
            opt.value = t.name;
            opt.textContent = t.name + (t.description ? ' \u2014 ' + t.description.substring(0, 60) : '');
            select.appendChild(opt);
        });
    }

    document.getElementById('template-select').addEventListener('change', function() {
        var name = this.value;
        if (!name) {
            hideTemplateDetails();
            return;
        }

        fetch('/api/templates/' + encodeURIComponent(name))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                currentTemplate = data;
                showTemplateDetails(data);
            })
            .catch(function(err) {
                console.error('Failed to load template:', err);
            });
    });

    function showTemplateDetails(template) {
        var descBox = document.getElementById('template-description');
        var descText = document.getElementById('template-desc-text');
        var triggers = document.getElementById('template-triggers');
        var form = document.getElementById('template-params-form');
        var container = document.getElementById('params-container');

        descText.textContent = template.description || 'No description available.';
        triggers.innerHTML = '';
        (template.trigger_phrases || []).forEach(function(phrase) {
            var tag = document.createElement('span');
            tag.className = 'badge-on-track';
            tag.style.marginRight = '0.25rem';
            tag.textContent = phrase;
            triggers.appendChild(tag);
        });
        descBox.style.display = 'block';

        container.innerHTML = '';
        var fields = template.fields || [];
        if (fields.length === 0) {
            var group = document.createElement('div');
            group.className = 'form-group';
            group.innerHTML = '<label class="form-label" for="param-context">Additional Context</label>' +
                '<textarea id="param-context" name="context" class="form-textarea" rows="4" ' +
                'placeholder="Provide any additional context or parameters..."></textarea>';
            container.appendChild(group);
        } else {
            fields.forEach(function(f) {
                var fieldName = (typeof f === 'string') ? f : (f.name || f);
                var fieldLabel = (typeof f === 'object' && f.label) ? f.label : fieldName;
                var fieldType = (typeof f === 'object' && f.type) ? f.type : 'text';

                var group = document.createElement('div');
                group.className = 'form-group';

                var label = document.createElement('label');
                label.className = 'form-label';
                label.setAttribute('for', 'param-' + fieldName);
                label.textContent = fieldLabel;
                group.appendChild(label);

                var input;
                if (fieldType === 'textarea') {
                    input = document.createElement('textarea');
                    input.className = 'form-textarea';
                    input.rows = 3;
                } else {
                    input = document.createElement('input');
                    input.type = fieldType;
                    input.className = 'form-input';
                }
                input.id = 'param-' + fieldName;
                input.name = fieldName;
                input.placeholder = (typeof f === 'object' && f.placeholder) ? f.placeholder : '';
                group.appendChild(input);

                container.appendChild(group);
            });
        }

        form.style.display = 'block';
    }

    function hideTemplateDetails() {
        document.getElementById('template-description').style.display = 'none';
        document.getElementById('template-params-form').style.display = 'none';
        document.getElementById('prompt-output').innerHTML =
            '<p class="empty-state">Select a template and fill in parameters to generate a prompt for Claude Code.</p>';
        document.getElementById('copy-prompt-btn').style.display = 'none';
        currentTemplate = null;
    }

    document.getElementById('template-params-form').addEventListener('submit', function(e) {
        e.preventDefault();
        if (!currentTemplate) return;

        var formData = new FormData(this);
        var params = {};
        formData.forEach(function(value, key) {
            if (value) params[key] = value;
        });

        fetch('/api/templates/' + encodeURIComponent(currentTemplate.name) + '/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({params: params})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var output = document.getElementById('prompt-output');
            var pre = document.createElement('pre');
            pre.className = 'mono';
            pre.style.whiteSpace = 'pre-wrap';
            pre.style.wordBreak = 'break-word';
            pre.style.maxHeight = '400px';
            pre.style.overflow = 'auto';
            pre.textContent = data.prompt || 'Error generating prompt.';
            output.innerHTML = '';
            output.appendChild(pre);

            document.getElementById('copy-prompt-btn').style.display = 'inline-block';

            var execution = {
                template: currentTemplate.name,
                params: params,
                generated: new Date().toISOString(),
                status: 'generated'
            };
            executions.unshift(execution);
            if (executions.length > 50) executions = executions.slice(0, 50);
            localStorage.setItem('ciphergy_executions', JSON.stringify(executions));
            renderExecutions();
        })
        .catch(function(err) {
            console.error('Error generating prompt:', err);
            document.getElementById('prompt-output').innerHTML =
                '<p class="empty-state" style="color:var(--red,#c0392b);">Error generating prompt. Check console for details.</p>';
        });
    });

    document.getElementById('copy-prompt-btn').addEventListener('click', function() {
        var pre = document.querySelector('#prompt-output pre');
        if (!pre) return;

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(pre.textContent).then(function() {
                var btn = document.getElementById('copy-prompt-btn');
                var orig = btn.textContent;
                btn.textContent = 'Copied';
                setTimeout(function() { btn.textContent = orig; }, 2000);
            });
        } else {
            var range = document.createRange();
            range.selectNodeContents(pre);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            document.execCommand('copy');
            sel.removeAllRanges();
        }
    });

    document.getElementById('clear-params-btn').addEventListener('click', function() {
        document.getElementById('template-params-form').reset();
    });

    document.getElementById('check-gates-btn').addEventListener('click', function() {
        var draftText = document.getElementById('draft-text').value;
        var recipientType = document.getElementById('recipient-type').value;

        if (!draftText.trim()) {
            alert('Please enter draft text to check.');
            return;
        }

        var statusBadge = document.getElementById('guardian-status');
        statusBadge.textContent = 'Checking...';
        statusBadge.className = 'badge-warning';

        fetch('/api/draft-check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                draft_text: draftText,
                recipient_type: recipientType
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            renderGateResults(data);
            statusBadge.textContent = data.passed ? 'PASSED' : 'FAILED';
            statusBadge.className = data.passed ? 'badge-on-track' : 'badge-critical';
        })
        .catch(function(err) {
            console.error('Gate check error:', err);
            statusBadge.textContent = 'Error';
            statusBadge.className = 'badge-critical';
        });
    });

    function renderGateResults(data) {
        var container = document.getElementById('gates-results');
        container.innerHTML = '';

        var summary = document.createElement('div');
        summary.style.padding = '0.75rem';
        summary.style.marginBottom = '1rem';
        summary.style.borderRadius = '4px';
        summary.style.fontWeight = 'bold';
        summary.style.textAlign = 'center';
        if (data.passed) {
            summary.style.background = 'var(--green-bg, #d4edda)';
            summary.style.color = 'var(--green, #27ae60)';
            summary.textContent = 'ALL 7 GATES PASSED';
        } else {
            summary.style.background = 'var(--red-bg, #f8d7da)';
            summary.style.color = 'var(--red, #c0392b)';
            summary.textContent = 'GATES FAILED \u2014 Review required';
        }
        container.appendChild(summary);

        var list = document.createElement('div');
        list.className = 'gate-list';
        (data.gates || []).forEach(function(gate) {
            var el = document.createElement('div');
            el.style.display = 'flex';
            el.style.alignItems = 'flex-start';
            el.style.gap = '0.5rem';
            el.style.padding = '0.5rem 0';
            el.style.borderBottom = '1px solid var(--border, #e0e0e0)';

            var icon = document.createElement('span');
            icon.style.fontWeight = 'bold';
            icon.style.minWidth = '1.5rem';
            if (gate.passed) {
                icon.innerHTML = '&#10003;';
                icon.style.color = 'var(--green, #27ae60)';
            } else {
                icon.innerHTML = '&#10007;';
                icon.style.color = 'var(--red, #c0392b)';
            }
            el.appendChild(icon);

            var info = document.createElement('div');
            info.innerHTML = '<strong>' + gate.name + '</strong><br>' +
                '<span style="font-size:0.85rem;opacity:0.8;">' + (gate.notes || '') + '</span>';
            el.appendChild(info);

            list.appendChild(el);
        });
        container.appendChild(list);

        if (data.warnings && data.warnings.length > 0) {
            var warnSection = document.createElement('div');
            warnSection.style.marginTop = '1rem';
            warnSection.style.padding = '0.5rem';
            warnSection.style.background = 'var(--yellow-bg, #fff3cd)';
            warnSection.style.borderRadius = '4px';
            var warnHtml = '<strong>Warnings:</strong><ul style="margin:0.25rem 0 0 1rem;">';
            data.warnings.forEach(function(w) {
                warnHtml += '<li>' + w + '</li>';
            });
            warnHtml += '</ul>';
            warnSection.innerHTML = warnHtml;
            container.appendChild(warnSection);
        }

        if (data.blocked_phrases && data.blocked_phrases.length > 0) {
            var blockSection = document.createElement('div');
            blockSection.style.marginTop = '0.75rem';
            blockSection.innerHTML = '<strong>Blocked Phrases:</strong> ' +
                data.blocked_phrases.map(function(p) {
                    return '<span class="badge-critical" style="margin-right:0.25rem;">' + p + '</span>';
                }).join('');
            container.appendChild(blockSection);
        }
    }

    var dropZone = document.getElementById('evidence-drop-zone');
    var fileInput = document.getElementById('evidence-file-input');

    dropZone.addEventListener('click', function() {
        fileInput.click();
    });

    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--accent, #3498db)';
        dropZone.style.background = 'var(--accent-bg, #eaf2f8)';
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.style.borderColor = '';
        dropZone.style.background = '';
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '';
        dropZone.style.background = '';
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        var listEl = document.getElementById('evidence-file-list');

        Array.prototype.forEach.call(files, function(file) {
            var item = document.createElement('div');
            item.style.display = 'flex';
            item.style.justifyContent = 'space-between';
            item.style.padding = '0.5rem';
            item.style.borderBottom = '1px solid var(--border, #e0e0e0)';
            var sizeKB = (file.size / 1024).toFixed(1);
            item.innerHTML = '<span>' + file.name + '</span>' +
                '<span class="mono">' + sizeKB + ' KB</span>' +
                '<span class="badge-on-track">Ready</span>';
            listEl.appendChild(item);
        });
    }

    function renderExecutions() {
        var tbody = document.getElementById('executions-body');
        if (executions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No recent executions</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        executions.slice(0, 20).forEach(function(ex) {
            var tr = document.createElement('tr');
            var paramsStr = Object.keys(ex.params || {}).map(function(k) {
                return k + ': ' + String(ex.params[k]).substring(0, 30);
            }).join(', ');
            var dateStr = ex.generated ? new Date(ex.generated).toLocaleString() : '';

            tr.innerHTML = '<td>' + (ex.template || '') + '</td>' +
                '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + paramsStr + '</td>' +
                '<td class="mono">' + dateStr + '</td>' +
                '<td><span class="badge-on-track">' + (ex.status || 'generated') + '</span></td>';
            tbody.appendChild(tr);
        });
    }

    loadTemplates();
    renderExecutions();

})();
