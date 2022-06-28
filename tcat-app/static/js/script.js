const DARK_MODE_KEY = 'darkMode';

const html = document.querySelector('html');
const btn = document.querySelector('button.mobile-menu-button');
const menu = document.querySelector('.mobile-menu');
const toggleDarkMode = document.querySelector('#toggle-dark-mode');

const modalToggle = document.querySelector('#modal-toggle');
const modalConfirm = document.querySelector('#modal-confirm');
const modalContent = document.querySelector('#modal-content');
const modalTitle = document.querySelector('#modal-title');

let modalConfirmationCallback = undefined

if(btn && menu) {
	btn.addEventListener('click', () => {
		menu.classList.toggle('hidden');
	});
}

if(toggleDarkMode) {
	toggleDarkMode.addEventListener('change', (e) => {
		setDarkMode(e.currentTarget.checked);
	});
}

if(modalConfirm) {
	modalConfirm.addEventListener('click', (e) => {
		hideModal();
		if(modalConfirmationCallback) modalConfirmationCallback();
	});
}

function openModal(title, content, callback) {
	if(modalTitle) modalTitle.innerHTML = title;
	if(modalContent) modalContent.innerHTML = content;
	modalConfirmationCallback = callback;
	modalToggle.checked = true;
}

function hideModal() {
	modalToggle.checked = false;
}

function isDarkMode() {
	let darkMode = localStorage.getItem(DARK_MODE_KEY);
	return (darkMode === 'true');
}

function setDarkMode(enabled, save=true) {
	if(enabled) {
		html.setAttribute('data-theme', 'dracula');
	} else {
		html.setAttribute('data-theme', 'emerald');
	}
	if(save)
		localStorage.setItem(DARK_MODE_KEY, enabled);
}

function checkDarkMode() {
	if(isDarkMode()) {
		setDarkMode(true, false);
		toggleDarkMode.checked = true;
		return;
	}
	setDarkMode(false, false);
	toggleDarkMode.checked = false;
}

document.addEventListener("DOMContentLoaded", () => {
  checkDarkMode();
});