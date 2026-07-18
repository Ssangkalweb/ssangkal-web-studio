const menuButton = document.querySelector('.menu-toggle');
const mainMenu = document.querySelector('.main-nav');
const menuLabel = menuButton?.querySelector('.sr-only');
const currentYear = document.querySelector('#current-year');
const themeButton = document.querySelector('.theme-toggle');
const themeLabel = themeButton?.querySelector('.theme-label');
const themeStorageKey = 'homepage-theme';

function getSavedTheme() {
  try {
    const savedTheme = localStorage.getItem(themeStorageKey);
    return savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : null;
  } catch {
    return null;
  }
}

function setTheme(theme, { save = false } = {}) {
  const isDark = theme === 'dark';
  document.documentElement.dataset.theme = isDark ? 'dark' : 'light';

  if (themeButton && themeLabel) {
    themeLabel.textContent = `현재: ${isDark ? '다크' : '라이트'} 모드`;
    themeButton.setAttribute('aria-label', `${isDark ? '라이트' : '다크'} 모드로 전환`);
  }

  if (save) {
    try {
      localStorage.setItem(themeStorageKey, isDark ? 'dark' : 'light');
    } catch {
      // 저장이 제한된 브라우저에서도 현재 페이지의 테마 전환은 유지합니다.
    }
  }
}

const initialTheme = getSavedTheme() ||
  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
setTheme(initialTheme);

themeButton?.addEventListener('click', () => {
  const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  setTheme(nextTheme, { save: true });
});

function closeMenu({ returnFocus = false } = {}) {
  if (!menuButton || !mainMenu || !menuLabel) return;

  mainMenu.classList.remove('open');
  menuButton.setAttribute('aria-expanded', 'false');
  menuLabel.textContent = '메뉴 열기';
  document.documentElement.classList.remove('menu-open');

  if (returnFocus) menuButton.focus();
}

if (menuButton && mainMenu && menuLabel) {
  menuButton.addEventListener('click', () => {
    const willOpen = menuButton.getAttribute('aria-expanded') !== 'true';

    mainMenu.classList.toggle('open', willOpen);
    menuButton.setAttribute('aria-expanded', String(willOpen));
    menuLabel.textContent = willOpen ? '메뉴 닫기' : '메뉴 열기';
    document.documentElement.classList.toggle('menu-open', willOpen);

    if (willOpen) mainMenu.querySelector('a')?.focus();
  });

  mainMenu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => closeMenu());
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && mainMenu.classList.contains('open')) {
      closeMenu({ returnFocus: true });
    }
  });

  document.addEventListener('click', (event) => {
    if (
      mainMenu.classList.contains('open') &&
      !mainMenu.contains(event.target) &&
      !menuButton.contains(event.target)
    ) {
      closeMenu();
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 960) closeMenu();
  });
}

if (currentYear) currentYear.textContent = new Date().getFullYear();
