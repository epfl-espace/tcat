const imageContainer = document.querySelector('#image-container');

let checkForPlotImagesInterval;
let addedPlotImages = [];

function failedRunningConfig() {
    let txt = document.createElement('p');
    txt.innerText = 'FAILED to run configuration'
    txt.classList.add('text-red-600', 'dark:text-red-300');
    imageContainer.appendChild(txt);
}

function addPlotImage(scenarioId, config_run_id, file) {
    let r = new XMLHttpRequest();
    r.addEventListener('load', (e) => {
        let img = document.createElement('img');
        img.src = 'data:image/png;base64,' + e.currentTarget.response;
        imageContainer.appendChild(img);
        addedPlotImages.push(file);
    });
    r.open('GET', `/configure/run/plot/${scenarioId}/${config_run_id}/${file}`);
    r.send();
}

function checkForPlotImages(scenarioId, configRunId, finishedOrFailed) {
    let request = new XMLHttpRequest();
    request.addEventListener('load', (e) => {
        let response = JSON.parse(e.currentTarget.response);
        if (response.failed || response.finished || response.plot_files.length > 0) {
            imageContainer.classList.remove('hidden');
            if (response.failed || response.finished) {
                clearInterval(checkForPlotImagesInterval);
                if (finishedOrFailed) finishedOrFailed();
            }

            for (let i = 0; i < response.plot_files.length; i++) {
                let file = response.plot_files[i];
                if (addedPlotImages.indexOf(file) > -1) continue;
                addPlotImage(scenarioId, configRunId, file);
            }

            if (response.failed) {
                failedRunningConfig();
            }
        }
    });
    request.open('GET', `/configure/run/plot/${scenarioId}/${configRunId}`);
    request.send();
}