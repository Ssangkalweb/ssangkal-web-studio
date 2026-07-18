const menuButton = document.querySelector('.menu-toggle');
const mainMenu = document.querySelector('.main-nav');
const menuLabel = menuButton.querySelector('.sr-only');

function closeMenu() {
  mainMenu.classList.remove('open');
  menuButton.setAttribute('aria-expanded', 'false');
  menuLabel.textContent = '메뉴 열기';
}

menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  mainMenu.classList.toggle('open', !isOpen);
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  menuLabel.textContent = isOpen ? '메뉴 열기' : '메뉴 닫기';
});

mainMenu.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', closeMenu);
});

window.addEventListener('resize', () => {
  if (window.innerWidth > 800) closeMenu();
});

document.querySelector('#current-year').textContent = new Date().getFullYear();
