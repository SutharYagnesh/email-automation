// Campaign progress & helper JS
function updateRecipientPreview() {
  const typeGroup = document.getElementById("recipient_type_groups");
  const typeContact = document.getElementById("recipient_type_contacts");
  
  const groupSelect = document.getElementById("group_select_container");
  const contactSelect = document.getElementById("contact_select_container");
  
  const isGroups = typeGroup && typeGroup.checked;
  
  if (groupSelect) groupSelect.style.display = isGroups ? "block" : "none";
  if (contactSelect) contactSelect.style.display = !isGroups ? "block" : "none";
  
  const selectedGroups = Array.from(document.querySelectorAll("input[name='group_ids']:checked")).map(el => el.value);
  const selectedContacts = Array.from(document.querySelectorAll("input[name='contact_ids']:checked")).map(el => el.value);
  
  fetch("/campaigns/preview-recipients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      recipient_type: isGroups ? "groups" : "contacts",
      group_ids: selectedGroups,
      contact_ids: selectedContacts
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        const counterEl = document.getElementById("recipient-count-badge");
        if (counterEl) {
          counterEl.innerText = `${data.count} Recipients`;
        }
      }
    })
    .catch(err => console.log(err));
}

function pollCampaignProgress(campaignId) {
  const fill = document.getElementById("progress-fill");
  const text = document.getElementById("progress-text");
  const statusBadge = document.getElementById("campaign-status-badge");
  
  if (!campaignId || !fill) return;
  
  const interval = setInterval(() => {
    fetch(`/campaigns/${campaignId}/status`)
      .then(res => res.json())
      .then(data => {
        if (!data.success) return;
        
        fill.style.width = `${data.progress_percent}%`;
        if (text) text.innerText = `${data.sent_count} / ${data.total_recipients} Sent (${data.progress_percent}%)`;
        
        if (statusBadge) {
          statusBadge.innerText = data.status;
          statusBadge.className = `badge badge-${data.status === 'completed' ? 'success' : data.status === 'sending' ? 'primary' : 'secondary'}`;
        }
        
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
          setTimeout(() => location.reload(), 1500);
        }
      })
      .catch(err => console.log(err));
  }, 2500);
}
