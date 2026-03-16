/**
 * Ciphergy Command Center — Mail Compose Page
 * Address book, document selection, cost estimation, mail sending, tracking.
 */
(function() {
    'use strict';

    var COSTS = {
        base: 1.50,
        certified: 4.85,
        return_receipt: 3.35,
        color_surcharge: 0.50,
        double_sided_discount: -0.10
    };

    var currentFilter = 'all';

    function loadAddressBook() {
        fetch('/api/address-book')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var contacts = data.contacts || [];
                var select = document.getElementById('recipient-select');
                contacts.forEach(function(c) {
                    var opt = document.createElement('option');
                    opt.value = JSON.stringify(c);
                    opt.textContent = c.name + (c.company ? ' (' + c.company + ')' : '');
                    select.appendChild(opt);
                });
            })
            .catch(function(err) {
                console.error('Failed to load address book:', err);
            });
    }

    function loadDocuments() {
        fetch('/api/documents')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var docs = data.documents || [];
                var select = document.getElementById('document-select');
                docs.forEach(function(d) {
                    var opt = document.createElement('option');
                    opt.value = d.path || d.name;
                    opt.textContent = d.name + (d.date ? ' (' + d.date + ')' : '');
                    select.appendChild(opt);
                });
            })
            .catch(function(err) {
                console.error('Failed to load documents:', err);
            });
    }

    document.getElementById('recipient-select').addEventListener('change', function() {
        if (!this.value) return;
        try {
            var contact = JSON.parse(this.value);
            document.getElementById('recipient-name').value = contact.name || '';
            document.getElementById('recipient-addr1').value = contact.address_line1 || '';
            document.getElementById('recipient-addr2').value = contact.address_line2 || '';
            document.getElementById('recipient-city').value = contact.city || '';
            document.getElementById('recipient-state').value = contact.state || '';
            document.getElementById('recipient-zip').value = contact.zip || '';
            updatePreview();
        } catch(e) {
            console.error('Error parsing contact:', e);
        }
    });

    document.getElementById('document-select').addEventListener('change', function() {
        var val = this.value;
        var info = document.getElementById('document-info');
        if (val) {
            document.getElementById('document-name').textContent = val.split('/').pop();
            info.style.display = 'block';
        } else {
            info.style.display = 'none';
        }
    });

    var previewFields = ['recipient-name', 'recipient-addr1', 'recipient-addr2',
                         'recipient-city', 'recipient-state', 'recipient-zip'];

    previewFields.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', updatePreview);
    });

    function updatePreview() {
        var name = document.getElementById('recipient-name').value;
        var addr1 = document.getElementById('recipient-addr1').value;
        var addr2 = document.getElementById('recipient-addr2').value;
        var city = document.getElementById('recipient-city').value;
        var state = document.getElementById('recipient-state').value;
        var zip = document.getElementById('recipient-zip').value;

        var toText = '';
        if (name) toText += name + '\n';
        if (addr1) toText += addr1 + '\n';
        if (addr2) toText += addr2 + '\n';
        if (city || state || zip) {
            toText += [city, state].filter(Boolean).join(', ');
            if (zip) toText += ' ' + zip;
        }

        document.getElementById('preview-to-text').textContent = toText || 'Select or enter recipient';
    }

    document.getElementById('opt-certified').addEventListener('change', function() {
        var stamp = document.getElementById('preview-certified-stamp');
        stamp.style.opacity = this.checked ? '1' : '0.3';
        updateCostEstimate();
    });

    document.getElementById('opt-return-receipt').addEventListener('change', function() {
        var stamp = document.getElementById('preview-return-stamp');
        stamp.style.opacity = this.checked ? '1' : '0.3';
        updateCostEstimate();
    });

    document.getElementById('opt-color').addEventListener('change', updateCostEstimate);
    document.getElementById('opt-double-sided').addEventListener('change', updateCostEstimate);

    function updateCostEstimate() {
        var base = COSTS.base;
        var certified = document.getElementById('opt-certified').checked ? COSTS.certified : 0;
        var returnReceipt = document.getElementById('opt-return-receipt').checked ? COSTS.return_receipt : 0;
        var color = document.getElementById('opt-color').checked ? COSTS.color_surcharge : 0;
        var doubleSided = document.getElementById('opt-double-sided').checked ? COSTS.double_sided_discount : 0;

        var total = base + certified + returnReceipt + color + doubleSided;

        document.getElementById('cost-base').textContent = '$' + base.toFixed(2);
        document.getElementById('cost-certified').textContent = '$' + certified.toFixed(2);
        document.getElementById('cost-return').textContent = '$' + returnReceipt.toFixed(2);
        document.getElementById('cost-total').textContent = '$' + total.toFixed(2);

        document.getElementById('cost-certified-row').style.display = certified > 0 ? '' : 'none';
        document.getElementById('cost-return-row').style.display = returnReceipt > 0 ? '' : 'none';
    }

    document.getElementById('send-mail-btn').addEventListener('click', function() {
        var sendBtn = this;
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';

        var recipient = {
            name: document.getElementById('recipient-name').value,
            address_line1: document.getElementById('recipient-addr1').value,
            address_line2: document.getElementById('recipient-addr2').value,
            city: document.getElementById('recipient-city').value,
            state: document.getElementById('recipient-state').value,
            zip: document.getElementById('recipient-zip').value
        };

        var documentPath = document.getElementById('document-select').value;

        var options = {
            certified: document.getElementById('opt-certified').checked,
            return_receipt: document.getElementById('opt-return-receipt').checked,
            color: document.getElementById('opt-color').checked,
            double_sided: document.getElementById('opt-double-sided').checked
        };

        var payload = {
            recipient: recipient,
            document_path: documentPath,
            options: options
        };

        fetch('/api/mail/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                alert('Send failed: ' + data.error);
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send Certified Mail';
                return;
            }

            document.getElementById('confirm-tracking').textContent = data.tracking_number || 'N/A';
            document.getElementById('confirm-delivery').textContent = data.expected_delivery || 'N/A';
            document.getElementById('confirm-cost').textContent = '$' + (data.cost || 0).toFixed(2);
            document.getElementById('send-confirmation').style.display = 'block';

            sendBtn.disabled = false;
            sendBtn.textContent = 'Send Certified Mail';

            loadTracking();
        })
        .catch(function(err) {
            console.error('Send error:', err);
            alert('Failed to send mail. Check console for details.');
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send Certified Mail';
        });
    });

    function loadTracking() {
        fetch('/api/mail/tracking')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                renderTracking(data.records || []);
            })
            .catch(function(err) {
                console.error('Failed to load tracking:', err);
            });
    }

    function renderTracking(records) {
        var tbody = document.getElementById('tracking-body');

        var filtered = records;
        if (currentFilter !== 'all') {
            filtered = records.filter(function(r) {
                if (currentFilter === 'pending') {
                    return r.status === 'queued' || r.status === 'pending';
                }
                return r.status === currentFilter;
            });
        }

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No mail records match filter</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        filtered.forEach(function(record) {
            var tr = document.createElement('tr');
            var recipientName = '';
            if (typeof record.recipient === 'object') {
                recipientName = record.recipient.name || '';
            } else {
                recipientName = record.recipient || '';
            }

            var statusBadge = 'badge-on-track';
            if (record.status === 'delivered') {
                statusBadge = 'badge-on-track';
            } else if (record.status === 'returned' || record.status === 'error') {
                statusBadge = 'badge-critical';
            } else {
                statusBadge = 'badge-warning';
            }

            tr.innerHTML =
                '<td class="mono">' + (record.tracking_number || 'N/A') + '</td>' +
                '<td>' + recipientName + '</td>' +
                '<td>' + (record.document || record.document_path || '').split('/').pop() + '</td>' +
                '<td class="mono">' + (record.sent_at ? new Date(record.sent_at).toLocaleDateString() : '') + '</td>' +
                '<td>' + (record.expected_delivery || 'N/A') + '</td>' +
                '<td><span class="' + statusBadge + '">' + (record.status || 'unknown').toUpperCase().replace(/-/g, ' ') + '</span></td>';
            tbody.appendChild(tr);
        });
    }

    document.querySelectorAll('.filter-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(function(b) {
                b.classList.remove('filter-active');
            });
            this.classList.add('filter-active');
            currentFilter = this.getAttribute('data-filter');
            loadTracking();
        });
    });

    document.getElementById('refresh-tracking-btn').addEventListener('click', loadTracking);

    loadAddressBook();
    loadDocuments();
    updateCostEstimate();
    loadTracking();

})();
