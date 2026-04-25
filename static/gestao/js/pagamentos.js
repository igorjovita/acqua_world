let historicoGlobal = [];

function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor, historicoJson) {
    document.getElementById('modal-reserva-id').value = id;
    document.getElementById('modal-titulo-reserva').innerText = "Reserva: " + nome;
    document.getElementById('modal-vendedor-reserva').innerText = "Vendedor: " + vendedor;
    
    // 1. Lida com o Histórico
    const textoHistorico = historicoJson ? historicoJson : '[]';
    historicoGlobal = JSON.parse(textoHistorico);
    
    // 2. Lida com os Passageiros e renderiza a tabela de checkout
    const passageiros = JSON.parse(passageirosJson);
    renderizarTabelaPassageiros(passageiros);
    
    // 3. Renderiza a tabela do histórico
    renderizarHistorico();
    
    // 4. Define a aba padrão ao abrir
    alternarAba('checkout');
    
    // 5. Mostra o modal
    document.getElementById('modal-acerto').style.display = 'flex';
}

function renderizarTabelaPassageiros(passageiros) {
    const tbody = document.getElementById('lista-passageiros-checkin');
    tbody.innerHTML = '';

    passageiros.forEach(p => {
        // Criar linha da tabela para cada passageiro
        const row = `
            <tr>
                <td><input type="checkbox" name="ids_passageiros" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()"></td>
                <td>${p.nome}</td>
                <td>${p.atividade || 'N/A'}</td>
                <td>R$ ${p.valor_cobrado.toFixed(2)}</td>
                <td>R$ ${p.pago.toFixed(2)}</td>
                <td style="font-weight: bold; color: #ef4444;">R$ ${p.saldo.toFixed(2)}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    // Zera o input de valor a receber
    document.getElementById('input-valor-final').value = "0.00";
    
    // Desmarca o checkbox "Selecionar Todos" por precaução
    const checkAll = document.getElementById('check-all-passageiros');
    if(checkAll) checkAll.checked = false;
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
                <td>${pg.passageiro || 'Grupo'}</td>
                <td style="font-weight: 600;">R$ ${pg.valor.toFixed(2)}</td>
                <td><span class="badge-mini">${pg.pagador || 'CLIENTE'}</span></td>
                <td><span class="badge-mini">${pg.recebedor || 'N/A'}</span></td>
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
        // Recarrega o histórico caso tenha mudado
        renderizarHistorico(); 
    }
}

function recalcularTotalCheckin() {
    let total = 0;
    const checks = document.querySelectorAll('input[name="ids_passageiros"]:checked');
    checks.forEach(c => {
        total += parseFloat(c.getAttribute('data-saldo'));
    });
    // Atualiza o input que a atendente pode editar
    document.getElementById('input-valor-final').value = total.toFixed(2);
}

function selecionarTodosPassageiros(source) {
    const checkboxes = document.querySelectorAll('input[name="ids_passageiros"]');
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = source.checked;
    }
    // Após selecionar/deselecionar, recalcula o total
    recalcularTotalCheckin();
}

function fecharModalAcerto() {
    document.getElementById('modal-acerto').style.display = 'none';
}