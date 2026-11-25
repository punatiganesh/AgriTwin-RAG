/**
 * AgriTwin-RAG Client Authentication & Profile Manager (js/auth.js)
 * Manages authenticated farmer sessions, dynamic UI identity updates, dropdown menus, and logout actions.
 */

const AgriAuth = (function () {
  let currentUser = null;
  let currentFarm = null;

  async function checkAuth(autoRedirect = true) {
    try {
      const response = await fetch("/api/auth/user");
      if (!response.ok) {
        if (autoRedirect && !isPublicPage()) {
          window.location.href = `/login.html?next=${encodeURIComponent(window.location.pathname)}`;
        }
        return null;
      }
      const data = await response.json();
      if (data && data.success && data.farmer) {
        currentUser = data.farmer;
        currentFarm = data.farm || null;

        updateUI(currentUser, currentFarm);
        return { farmer: currentUser, farm: currentFarm };
      } else {
        if (autoRedirect && !isPublicPage()) {
          window.location.href = "/login.html";
        }
        return null;
      }
    } catch (err) {
      console.warn("Auth status check warning:", err);
      return null;
    }
  }

  function isPublicPage() {
    const path = window.location.pathname.toLowerCase();
    return (
      path.endsWith("login.html") ||
      path.endsWith("register.html") ||
      path.endsWith("login") ||
      path.endsWith("register")
    );
  }

  function updateUI(user, farm) {
    if (!user) return;

    const displayName = user.name || "Farmer";
    const initial = displayName.charAt(0).toUpperCase();

    // Topbar elements
    const topbarAvatar = document.getElementById("topbarAvatar");
    if (topbarAvatar) topbarAvatar.textContent = initial;

    const topbarName = document.getElementById("topbarName");
    if (topbarName) topbarName.textContent = displayName;

    // Dropdown elements
    const dropdownAvatar = document.getElementById("dropdownAvatar");
    if (dropdownAvatar) dropdownAvatar.textContent = initial;

    const dropdownName = document.getElementById("dropdownName");
    if (dropdownName) dropdownName.textContent = displayName;

    const dropdownSub = document.getElementById("dropdownSub");
    if (dropdownSub) {
      dropdownSub.textContent = user.email || (user.phone ? `+91 ${user.phone}` : "Authenticated Farmer");
    }

    // Sidebar elements
    const userAvatar = document.getElementById("userAvatar");
    if (userAvatar) userAvatar.textContent = initial;

    const userName = document.getElementById("userName");
    if (userName) userName.textContent = displayName;

    const userMeta = document.getElementById("userMeta");
    if (userMeta) {
      userMeta.textContent = farm ? (farm.farm_name || "AgriTwin Farm") : "Farmer Profile";
    }

    // Topbar location text
    const locationText = document.getElementById("locationText");
    if (locationText && farm) {
      const locLabel =
        farm.locality ||
        farm.district ||
        farm.place_name ||
        (farm.latitude && farm.longitude
          ? `${farm.latitude.toFixed(4)}, ${farm.longitude.toFixed(4)}`
          : "Srivilliputhur, TN");
      locationText.textContent = locLabel;
    }

    setupUserDropdown();
    attachLogoutHandler();
  }

  function setupUserDropdown() {
    const userMenuBtn = document.getElementById("userMenuBtn");
    const userMenuWrapper = document.getElementById("userMenuWrapper");
    const userDropdownMenu = document.getElementById("userDropdownMenu");

    if (userMenuBtn && userDropdownMenu && userMenuWrapper) {
      // Toggle dropdown on button click
      userMenuBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isOpen = userDropdownMenu.classList.contains("show");
        if (isOpen) {
          userDropdownMenu.classList.remove("show");
          userMenuWrapper.classList.remove("open");
          userMenuBtn.setAttribute("aria-expanded", "false");
        } else {
          userDropdownMenu.classList.add("show");
          userMenuWrapper.classList.add("open");
          userMenuBtn.setAttribute("aria-expanded", "true");
        }
      };

      // Close dropdown when clicking outside
      document.addEventListener("click", (e) => {
        if (!userMenuWrapper.contains(e.target)) {
          userDropdownMenu.classList.remove("show");
          userMenuWrapper.classList.remove("open");
          userMenuBtn.setAttribute("aria-expanded", "false");
        }
      });
    }
  }

  function attachLogoutHandler() {
    document.querySelectorAll(".btn-logout, #logoutBtn, #topbarLogoutBtn").forEach((btn) => {
      btn.onclick = (e) => {
        e.preventDefault();
        logout();
      };
    });
  }

  async function logout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (e) {
      console.warn("Logout fetch failed:", e);
    }
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch (e) {}
    window.location.replace("login.html");
  }

  // Automatically check authentication on DOM ready for all pages
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      if (!isPublicPage()) {
        checkAuth(true);
      }
      setupUserDropdown();
      attachLogoutHandler();
    });
  } else {
    if (!isPublicPage()) {
      checkAuth(true);
    }
    setupUserDropdown();
    attachLogoutHandler();
  }

  return {
    checkAuth,
    getUser: () => currentUser,
    getFarm: () => currentFarm,
    logout,
    updateUI,
  };
})();

// Export if in module context
if (typeof module !== "undefined" && module.exports) {
  module.exports = AgriAuth;
}
