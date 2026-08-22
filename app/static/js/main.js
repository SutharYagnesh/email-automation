// Main UI Interaction JS
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Sidebar Drawer Toggle & Backdrop Overlay
  const toggleBtn = document.getElementById("mobile-sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("active");
      if (backdrop) backdrop.classList.toggle("active");
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeSidebar);
  }

  // Auto-close sidebar on mobile when tapping navigation links
  document.querySelectorAll(".sidebar-nav .nav-item").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 992) {
        closeSidebar();
      }
    });
  });

  // Modal Open/Close Event Listeners
  document.querySelectorAll("[data-modal-target]").forEach((trigger) => {
    trigger.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = trigger.getAttribute("data-modal-target");
      const modal = document.getElementById(targetId);
      if (modal) {
        modal.classList.add("active");
      }
    });
  });

  document.querySelectorAll(".modal-close, [data-modal-close]").forEach((closeBtn) => {
    closeBtn.addEventListener("click", () => {
      const modal = closeBtn.closest(".modal-overlay");
      if (modal) {
        modal.classList.remove("active");
      }
    });
  });

  // Close modal when clicking overlay background
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });

  // Client-side file upload size validation (Max 4.5 MB on Vercel)
  document.querySelectorAll('input[type="file"]').forEach((fileInput) => {
    fileInput.addEventListener("change", () => {
      const maxBytes = 4.5 * 1024 * 1024; // 4.5 MB
      let totalSize = 0;
      for (let i = 0; i < fileInput.files.length; i++) {
        totalSize += fileInput.files[i].size;
      }
      if (totalSize > maxBytes) {
        alert("The selected file(s) size (" + (totalSize / (1024 * 1024)).toFixed(2) + " MB) exceeds the 4.5 MB limit. Please select smaller or compressed files.");
        fileInput.value = "";
      }
    });
  });
});

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || createToastContainer();
  const alert = document.createElement("div");
  alert.className = `alert alert-${type}`;
  alert.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;">&times;</button>`;
  container.appendChild(alert);
  setTimeout(() => {
    if (alert.parentElement) alert.remove();
  }, 4000);
}

function createToastContainer() {
  const container = document.createElement("div");
  container.id = "toast-container";
  container.style.cssText = "position:fixed;top:20px;right:20px;z-index:9999;max-width:350px;";
  document.body.appendChild(container);
  return container;
}
