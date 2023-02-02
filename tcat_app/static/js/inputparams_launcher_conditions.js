const launcherUseDatabase = document.querySelector('[name="launcher_use_database"]');

const launcherPerformanceElement = document.querySelector('[name="launcher_performance"]');
const launcherFairingDiameterElement = document.querySelector('[name="launcher_fairing_diameter"]');
const launcherFairingCylinderHeightElement = document.querySelector('[name="launcher_fairing_cylinder_height"]');
const launcherFairingTotalHeightElement = document.querySelector('[name="launcher_fairing_total_height"]');
const launcherInterpolationMethodElement = document.querySelector('[name="launcher_perf_interpolation_method"]');

const launcherPerformanceLabel = document.querySelector('[for="launcher_performance"]');
const launcherFairingDiameterLabel = document.querySelector('[for="launcher_fairing_diameter"]');
const launcherFairingCylinderHeightLabel = document.querySelector('[for="launcher_fairing_cylinder_height"]');
const launcherFairingTotalHeightLabel = document.querySelector('[for="launcher_fairing_total_height"]');
const launcherInterpolationMethodLabel = document.querySelector('[for="launcher_perf_interpolation_method"]');

const launcherCustomFieldsThatChangeRequiredState = [
    launcherPerformanceElement,
    launcherFairingDiameterElement,
    launcherFairingCylinderHeightElement,
    launcherFairingTotalHeightElement,
]

const launcherCustomFieldsLabels = [
    launcherPerformanceLabel,
    launcherFairingDiameterLabel,
    launcherFairingCylinderHeightLabel,
    launcherFairingTotalHeightLabel,
]

const launcherFieldsThatChangeRequiredState = [
    launcherInterpolationMethodElement,
]

const launcherFieldsLabels = [
    launcherInterpolationMethodLabel,
]

document.addEventListener("DOMContentLoaded", () => {
    setRequiredLauncherFields();

});

if(launcherUseDatabase) {
    launcherUseDatabase.addEventListener('change', (e) => {
        setRequiredLauncherFields();
    });
}

function setRequiredLauncherFields() {
    const enabled = launcherUseDatabase && launcherUseDatabase.checked;
    launcherCustomFieldsThatChangeRequiredState.forEach((field) => {
        if(field) field.required = !enabled;
    });
    launcherCustomFieldsLabels.forEach((label) => {
        if (label) {
            if(enabled) {
                label.parentElement.classList.add('hidden');
            } else {
                label.parentElement.classList.remove('hidden');
            }
        }
    });
    launcherFieldsThatChangeRequiredState.forEach((field) => {
        if(field) field.required = enabled;
    });
    launcherFieldsLabels.forEach((label) => {
        if (label) {
            if(!enabled) {
                label.parentElement.classList.add('hidden');
            } else {
                label.parentElement.classList.remove('hidden');
            }
        }
    });
}