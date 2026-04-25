let historicoGlobal = [];

function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor, historicoJson) {
    document.getElementById('modal-reserva-id').value = id;
    document.getElementById('modal-titulo-reserva').innerText = "Reserva: " + nome;
    document.getElementById('modal-vendedor-reserva').innerText = "Vendedor: " + vendedor;
    
    // Armazena o histórico para uso posterior
    historicoGlobal = JSON.parse(historicoJson);
    
    // Renderiza a lista de check-in (passageiros)
    const passageiros = JSON.parse(passageirosJson);
    renderizarTabelaPassageiros(passageiros);
    
    // Limpa e prepara a aba de histórico
    renderizarHistorico();
    
    // Reset para a aba de checkout ao abrir
    alternarAba('checkout');
    
    document.getElementById('modal-acerto').style.display = 'flex';
}


function renderizarHistorico() {
    const tbody = document.getElementById('lista-historico-pagamentos');
    tbody.innerHTML = '';

    if (historicoGlobal.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color: #64748b;">Nenhum pagamento registrado.</td></tr>';
        return;
    }

    historicoGlobal.forEach(pg => {
        const row = `
            <tr>
                <td>${pg.data || 'N/A'}</td>
                <td>${pg.passageiro}</td>
                <td style="font-weight: 600;">R$ ${pg.valor.toFixed(2)}</td>
                <td><span class="badge-mini">${pg.pagador || 'CLIENTE'}</span></td>
                <td><span class="badge-mini">${pg.recebedor}</span></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function alternarAba(aba) {
    const checkout = document.getElementById('aba-checkout');
    const historico = document.getElementById('aba-historico');
    const btnCheckout = document.getElementById('btn-tab-checkout');
    const btnHistorico = document.getElementById('btn-tab-historico');

    if (aba === 'checkout') {
        checkout.style.display = 'block';
        historico.style.display = 'none';
        btnCheckout.classList.add('active');
        btnHistorico.classList.remove('active');
    } else {
        checkout.style.display = 'none';
        historico.style.display = 'block';
        btnCheckout.classList.remove('active');
        btnHistorico.classList.add('active');
        renderizarHistorico();
    }
}

function recalcularTotalCheckin() {
    let total = 0;
    const checks = document.querySelectorAll('input[name="ids_passageiros"]:checked');
    checks.forEach(c => {
        total += parseFloat(c.getAttribute('data-saldo'));
    });
    document.getElementById('input-valor-final').value = total.toFixed(2);
}

function selecionarTodosPassageiros(source) {
    const checkboxes = document.querySelectorAll('input[name="ids_passageiros"]');
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = source.checked;
    }
    recalcularTotalCheckin();
}


function fecharModalAcerto() {
    document.getElementById('modal-acerto').style.display = 'none';
}

function alternarModoPagamento() {
    const modo = document.getElementById('tipo_acerto').value;
    const blocoGrupo = document.getElementById('bloco-pg-grupo');
    const blocoInd = document.getElementById('bloco-pg-individual');
    const selectGrupo = document.getElementById('select-forma-grupo');
    
    if (modo === 'grupo') {
        blocoGrupo.style.display = 'block';
        blocoInd.style.display = 'none';
        selectGrupo.required = true;
    } else {
        blocoGrupo.style.display = 'none';
        blocoInd.style.display = 'block';
        selectGrupo.required = false;
    }
}