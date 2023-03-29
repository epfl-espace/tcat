const kickstageUseDatabaseElement = document.querySelector('[name="kickstage_use_database"]');

const kickstageHeightElement = document.querySelector('[name="kickstage_height"]');
const kickstageDiameterElement = document.querySelector('[name="kickstage_diameter"]');
const kickstageInitialFuelMassElement = document.querySelector('[name="kickstage_initial_fuel_mass"]');
const kickstagePropThrustElement = document.querySelector('[name="kickstage_prop_thrust"]');
const kickstagePropIspElement = document.querySelector('[name="kickstage_prop_isp"]');
const kickstagePropulsionDryMassElement = document.querySelector('[name="kickstage_propulsion_dry_mass"]');
const kickstageDispenserDryMassElement = document.querySelector('[name="kickstage_dispenser_dry_mass"]');
const kickstageStructMassElement = document.querySelector('[name="kickstage_struct_mass"]');
const kickstagePropulsionTypeElement = document.querySelector('[name="kickstage_propulsion_type"]');

const kickstageHeightLabel = document.querySelector('[for="kickstage_height"]');
const kickstageDiameterLabel = document.querySelector('[for="kickstage_diameter"]');
const kickstageInitialFuelMassLabel = document.querySelector('[for="kickstage_initial_fuel_mass"]');
const kickstagePropThrustLabel = document.querySelector('[for="kickstage_prop_thrust"]');
const kickstagePropIspLabel = document.querySelector('[for="kickstage_prop_isp"]');
const kickstagePropulsionDryMassLabel = document.querySelector('[for="kickstage_propulsion_dry_mass"]');
const kickstageDispenserDryMassLabel = document.querySelector('[for="kickstage_dispenser_dry_mass"]');
const kickstageStructMassLabel = document.querySelector('[for="kickstage_struct_mass"]');
const kickstagePropulsionTypeLabel = document.querySelector('[for="kickstage_propulsion_type"]');


const kickstageFieldsThatChangeRequiredState = [
    kickstageHeightElement,
    kickstageDiameterElement,
    kickstageInitialFuelMassElement,
    kickstagePropThrustElement,
    kickstagePropIspElement,
    kickstagePropulsionDryMassElement,
    kickstageDispenserDryMassElement,
    kickstageStructMassElement,
    kickstagePropulsionTypeElement,
]

const kickstageFieldsLabels = [
    kickstageHeightLabel,
    kickstageDiameterLabel,
    kickstageInitialFuelMassLabel,
    kickstagePropThrustLabel,
    kickstagePropIspLabel,
    kickstagePropulsionDryMassLabel,
    kickstageDispenserDryMassLabel,
    kickstageStructMassLabel,
    kickstagePropulsionTypeLabel,
]

document.addEventListener("DOMContentLoaded", () => {
    setRequiredKickstageFields();
});

if(kickstageUseDatabaseElement) {
    kickstageUseDatabaseElement.addEventListener('change', (e) => {
        setRequiredKickstageFields();
    });
}

function setRequiredKickstageFields() {
    const enabled = kickstageUseDatabaseElement && kickstageUseDatabaseElement.checked;

    kickstageFieldsThatChangeRequiredState.forEach((field) => {
        if(field) field.required = !enabled;
    });

    kickstageFieldsLabels.forEach((label) => {
        if (label) {
            if(enabled) {
                label.parentElement.classList.add('hidden');
            } else {
                label.parentElement.classList.remove('hidden');
            }
        }
    });
}