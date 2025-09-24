// --- LÓGICA PARA O POP-UP DE CONFIRMAÇÃO ---

// Variáveis para guardar o estado da confirmação
let confirmCallback = null;
let cancelCallback = null;
let formToSubmit = null;

// Elementos do DOM
const popupOverlay = document.createElement('div');
popupOverlay.className = 'popup-overlay';

const popupContent = document.createElement('div');
popupContent.className = 'popup-content';

popupOverlay.appendChild(popupContent);
document.body.appendChild(popupOverlay);

/**
 * Exibe um pop-up de confirmação customizado.
 * @param {string} title - O título do pop-up.
 * @param {string} message - A mensagem a ser exibida.
 * @param {HTMLElement} form - O formulário a ser submetido se confirmado.
 */
function showConfirmPopup(title, message, form) {
    // Guarda o formulário para submissão posterior
    formToSubmit = form;

    // Preenche o conteúdo do pop-up
    popupContent.innerHTML = `
        <h2>${title}</h2>
        <p>${message}</p>
        <div class="popup-buttons">
            <button id="popup-cancel" class="btn btn-yellow">Cancelar</button>
            <button id="popup-confirm" class="btn btn-red">Confirmar</button>
        </div>
    `;

    // Mostra o pop-up
    popupOverlay.style.display = 'flex';

    // Adiciona os event listeners aos botões
    document.getElementById('popup-confirm').addEventListener('click', handleConfirm);
    document.getElementById('popup-cancel').addEventListener('click', handleCancel);
}

// Função para fechar o pop-up
function closePopup() {
    popupOverlay.style.display = 'none';
    formToSubmit = null; // Limpa a referência ao formulário
}

// Função executada ao confirmar
function handleConfirm() {
    if (formToSubmit) {
        formToSubmit.submit(); // Envia o formulário original
    }
    closePopup();
}

// Função executada ao cancelar
function handleCancel() {
    closePopup();
}

// Adiciona um listener para todos os formulários de exclusão
document.addEventListener('DOMContentLoaded', () => {
    const deleteForms = document.querySelectorAll('form.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            // Previne o envio padrão do formulário
            event.preventDefault();
            
            // Pega a mensagem customizada do atributo data, se existir
            const message = this.dataset.confirmMessage || 'Esta ação não pode ser desfeita.';
            
            // Exibe o pop-up
            showConfirmPopup('Tem certeza?', message, this);
        });
    });
});
