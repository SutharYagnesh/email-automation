// Main UI Interaction JS
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Sidebar Drawer Toggle
  const toggleBtn = document.getElementById("mobile-sidebar-toggle");
  const sidebar = document.getElementById("sidebar");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("active");
    });
  }

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
