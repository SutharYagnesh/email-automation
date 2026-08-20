// Sender accounts & Deliverability JS
function testSenderConnection(senderId) {
  const btn = document.getElementById(`test-btn-${senderId}`);
  const statusBadge = document.getElementById(`status-badge-${senderId}`);
  
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "Testing...";
  }
  
  fetch(`/senders/${senderId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
    .then(res => res.json())
    .then(data => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = "Test Connection";
      }
      if (data.success) {
        showToast(data.message, "success");
        if (statusBadge) {
          statusBadge.className = "badge badge-success";
          statusBadge.innerText = "connected";
        }
      } else {
        showToast(data.message, "danger");
        if (statusBadge) {
          statusBadge.className = "badge badge-danger";
          statusBadge.innerText = "error";
        }
      }
    })
    .catch(err => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = "Test Connection";
      }
      showToast("Connection test failed: " + err, "danger");
    });
}

function runDeliverabilityCheck(domain) {
  const modal = document.getElementById("deliverability-modal");
  const contentContainer = document.getElementById("deliverability-results");
  
  if (modal) modal.classList.add("active");
  if (contentContainer) contentContainer.innerHTML = "<p>Analyzing domain DNS records (SPF, DKIM, DMARC, MX)...</p>";
  
  fetch("/senders/check-domain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain: domain })
  })
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        contentContainer.innerHTML = `<p class="text-danger">Check failed: ${data.message}</p>`;
        return;
      }
      
      const r = data.results;
      contentContainer.innerHTML = `
        <div style="margin-bottom:16px;">
          <h4>Domain: <strong>${r.domain}</strong></h4>
          <p>Overall Deliverability Score: <strong>${r.deliverability_score}/100</strong></p>
        </div>
        <div style="display:grid;gap:12px;">
          <div class="card" style="padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>SPF Record</strong>
              <span class="badge badge-${r.spf.status === 'pass' ? 'success' : r.spf.status === 'warning' ? 'warning' : 'danger'}">${r.spf.status}</span>
            </div>
            <div style="font-size:0.85rem;color:#64748b;margin-top:4px;">${r.spf.details}</div>
            <code style="font-size:0.8rem;background:#f1f5f9;padding:4px;display:block;margin-top:6px;border-radius:4px;">${r.spf.record || 'None'}</code>
          </div>
          
          <div class="card" style="padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>DMARC Policy</strong>
              <span class="badge badge-${r.dmarc.status === 'pass' ? 'success' : 'warning'}">${r.dmarc.status}</span>
            </div>
            <div style="font-size:0.85rem;color:#64748b;margin-top:4px;">${r.dmarc.details}</div>
            <code style="font-size:0.8rem;background:#f1f5f9;padding:4px;display:block;margin-top:6px;border-radius:4px;">${r.dmarc.record || 'None'}</code>
          </div>

          <div class="card" style="padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>MX Records</strong>
              <span class="badge badge-${r.mx.status === 'pass' ? 'success' : 'danger'}">${r.mx.status}</span>
            </div>
            <div style="font-size:0.85rem;color:#64748b;margin-top:4px;">${r.mx.details}</div>
            <code style="font-size:0.8rem;background:#f1f5f9;padding:4px;display:block;margin-top:6px;border-radius:4px;">${r.mx.record}</code>
          </div>

          <div class="card" style="padding:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>DKIM Guidance</strong>
              <span class="badge badge-info">${r.dkim.status}</span>
            </div>
            <div style="font-size:0.85rem;color:#64748b;margin-top:4px;">${r.dkim.details}</div>
          </div>
        </div>
      `;
    })
    .catch(err => {
      contentContainer.innerHTML = `<p class="text-danger">Failed to query DNS: ${err}</p>`;
    });
}
