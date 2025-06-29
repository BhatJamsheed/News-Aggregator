// Optimized dark mode toggle logic with local SVG icons
(function() {
  const toggleBtn = document.getElementById('darkModeToggle');
  const iconImg = document.getElementById('darkModeIconImg');
  const darkClass = 'dark-mode';
  const moonIcon = '/static/moon.svg';
  const sunIcon = '/static/sun.svg';

  // Detect system preference
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // Set mode
  function setMode(dark) {
    if (dark) {
      document.body.classList.add(darkClass);
      iconImg.src = sunIcon;
      iconImg.alt = 'Switch to light mode';
    } else {
      document.body.classList.remove(darkClass);
      iconImg.src = moonIcon;
      iconImg.alt = 'Switch to dark mode';
    }
  }

  // Load mode from storage or system
  function loadMode() {
    const stored = localStorage.getItem('darkMode');
    if (stored === 'dark') return true;
    if (stored === 'light') return false;
    return systemPrefersDark();
  }

  // Save mode
  function saveMode(dark) {
    localStorage.setItem('darkMode', dark ? 'dark' : 'light');
  }

  // Toggle handler
  function toggle() {
    const isDark = document.body.classList.toggle(darkClass);
    iconImg.src = isDark ? sunIcon : moonIcon;
    iconImg.alt = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    saveMode(isDark);
  }

  // Init
  document.addEventListener('DOMContentLoaded', function() {
    setMode(loadMode());
    if (toggleBtn) toggleBtn.addEventListener('click', toggle);
  });
})(); 