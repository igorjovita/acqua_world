let historicoGlobal = [];

function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor, historicoJson) {
    document.getElementById('modal-reserva-id').value = id;
    document.getElementById('modal-titulo-reserva').innerText = "Reserva: " + nome;
    document.getElementById('modal-vendedor-reserva').innerText = "Vendedor: " + (vendedor || 'N/A');
    
    // Tenta ler o histórico sem deixar o sistema quebrar
    try {
        const textoHistorico = (historicoJson && historicoJson !== 'undefined') ? historicoJson : '[]';
        historicoGlobal = JSON.parse(textoHistorico);
    } catch (e) {
        console.warn("Erro ao ler o histórico, assumindo vazio.");
        historicoGlobal = [];
    }
    
    // Renderiza a lista de check-in
    try {
        const passageiros = JSON.parse(passageirosJson);
        renderizarTabelaPassageiros(passageiros);
    } catch (e) {
        console.error("Erro grave nos passageiros.");
    }
    
    renderizarHistorico();
    alternarAba('checkout');
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
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 30px; color: #94a3b8; font-weight: 500;">Nenhum pagamento registrado no extrato.</td></tr>';
        return;
    }

    historicoGlobal.forEach(pg => {
        // Cores diferentes para saber se o dinheiro está com o vendedor ou com a loja
        const corRecebedor = pg.recebedor === 'LOJA' 
            ? 'background: #dcfce7; color: #166534; border: 1px solid #bbf7d0;' // Verde claro pra Loja
            : 'background: #fef9c3; color: #854d0e; border: 1px solid #fef08a;'; // Amarelo pro Vendedor

        const row = `
            <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.2s;">
                <td style="padding: 12px; text-align: center; color: #64748b;">${pg.data || 'N/A'}</td>
                <td style="padding: 12px; text-align: left; font-weight: 500; color: #0f172a;">${pg.passageiro || 'Grupo'}</td>
                <td style="padding: 12px; text-align: center; font-weight: 600; color: #059669;">R$ ${pg.valor.toFixed(2)}</td>
                <td style="padding: 12px; text-align: center;">
                    <span style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                        ${pg.pagador || 'CLIENTE'}
                    </span>
                </td>
                <td style="padding: 12px; text-align: center;">
                    <span style="${corRecebedor} padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                        ${pg.recebedor || 'N/A'}
                    </span>
                </td>
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