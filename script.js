const menuButton = document.querySelector('.menu-toggle');
const mainMenu = document.querySelector('.main-nav');
const menuLabel = menuButton?.querySelector('.sr-only');
const currentYear = document.querySelector('#current-year');

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
    if (window.innerWidth > 800) closeMenu();
  });
}

if (currentYear) currentYear.textContent = new Date().getFullYear();
