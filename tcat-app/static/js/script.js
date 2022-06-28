const DARK_MODE_KEY = 'darkMode';

const html = document.querySelector('html');
const btn = document.querySelector('button.mobile-menu-button');
const menu = document.querySelector('.mobile-menu');
const toggleDarkMode = document.querySelector('#toggle-dark-mode');
const modal = document.querySelector('#modal');
const modalCancel = document.querySelector('#modal-cancel');
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

if(modalCancel) {
	modalCancel.addEventListener('click', hideModal);
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
	modal.style.display = 'block';
}

function hideModal() {
	modal.style.display = 'none';
}

function isDarkMode() {
	let darkMode = localStorage.getItem(DARK_MODE_KEY);
	return (darkMode === 'true');
}

function setDarkMode(enabled, save=true) {
	if(enabled) {
		if(!html.classList.contains('dark'))
			html.classList.add('dark');
	} else {
		if(html.classList.contains('dark'))
			html.classList.remove('dark');
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