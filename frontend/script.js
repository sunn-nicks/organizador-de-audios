const sendBtn = document.getElementById("sendBtn");
const audioInput = document.getElementById("audioInput");
const progress = document.querySelector(".progress");
const progressContainer = document.querySelector(".progress-container");
const resultBox = document.getElementById("result");
const downloadLink = document.getElementById("downloadLink");

sendBtn.onclick = async () => {
    if (!audioInput.files.length) {
        alert("Selecione pelo menos 1 arquivo!");
        return;
    }

    progressContainer.classList.remove("hidden");
    resultBox.classList.add("hidden");
    progress.style.width = "0%";

    let form = new FormData();
    for (let file of audioInput.files) {
        form.append("files", file);
    }

    const response = await fetch("http://127.0.0.1:8000/process", {
        method: "POST",
        body: form
    });

    // Atualiza barra
    progress.style.width = "100%";

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    downloadLink.href = url;
    resultBox.classList.remove("hidden");
};
