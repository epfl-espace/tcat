const launcherUseDatabase = document.querySelector('[name="launcher_use_database"]');

const launcherPerformanceElement = document.querySelector('[name="launcher_performance"]');
const launcherFairingDiameterElement = document.querySelector('[name="launcher_fairing_diameter"]');
const launcherFairingCylinderHeightElement = document.querySelector('[name="launcher_fairing_cylinder_height"]');
const launcherFairingTotalHeightElement = document.querySelector('[name="launcher_fairing_total_height"]');

const launcherPerformanceLabel = document.querySelector('[for="launcher_performance"]');
const launcherFairingDiameterLabel = document.querySelector('[for="launcher_fairing_diameter"]');
const launcherFairingCylinderHeightLabel = document.querySelector('[for="launcher_fairing_cylinder_height"]');
const launcherFairingTotalHeightLabel = document.querySelector('[for="launcher_fairing_total_height"]');

const launcherFieldsThatChangeRequiredState = [
    launcherPerformanceElement,
    launcherFairingDiameterElement,
    launcherFairingCylinderHeightElement,
    launcherFairingTotalHeightElement,
]

const launcherFieldsLabels = [
    launcherPerformanceLabel,
    launcherFairingDiameterLabel,
    launcherFairingCylinderHeightLabel,
    launcherFairingTotalHeightLabel,
]

document.addEventListener("DOMContentLoaded", () => {
    setRequiredLauncherFields();

});

if(launcherUseDatabase) {
    launcherUseDatabase.addEventListener('change', (e) => {
        console.log('changed use database')
        setRequiredLauncherFields();
    });
}

function setRequiredLauncherFields() {
    const enabled = launcherUseDatabase && launcherUseDatabase.checked;
    launcherFieldsThatChangeRequiredState.forEach((field) => {
        if(field) field.required = !enabled;
    });
    launcherFieldsLabels.forEach((label) => {
        if (label) {
            if(enabled) {
                label.classList.remove('font-semibold');
                label.classList.add('italic', 'font-light');
            } else {
                label.classList.remove('italic', 'font-light');
                label.classList.add('font-semibold');
            }
        }
    });
}