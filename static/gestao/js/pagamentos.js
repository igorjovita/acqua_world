let historicoGlobal = [];

function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor, historicoJson) {
    // Seta IDs (Comuns e específicos)
    const resIdPC = document.getElementById('modal-reserva-id');
    const resIdMob = document.getElementById('modal-reserva-id-mobile');
    if (resIdPC) resIdPC.value = id;
    if (resIdMob) resIdMob.value = id;

    // Títulos PC
    const tituloPC = document.getElementById('modal-titulo-reserva');
    const vendPC = document.getElementById('modal-vendedor-reserva');
    if (tituloPC) tituloPC.innerText = "Reserva: " + nome;
    if (vendPC) vendPC.innerText = "Vendedor: " + (vendedor || 'N/A');

    // Títulos Mobile
    const tituloMob = document.getElementById('modal-titulo');
    if (tituloMob) tituloMob.innerText = nome.toUpperCase();

    // 1. Lida com o Histórico
    try {
        const textoHistorico = (historicoJson && historicoJson !== 'undefined') ? historicoJson : '[]';
        historicoGlobal = JSON.parse(textoHistorico);
    } catch (e) {
        console.warn("Erro ao ler o histórico, assumindo vazio.");
        historicoGlobal = [];
    }

    // 2. Lida com os Passageiros
    try {
        const passageiros = JSON.parse(passageirosJson);
        renderizarPassageiros(passageiros);
    } catch (e) {
        console.error("Erro grave nos passageiros.");
    }

    // 3. Renderiza Histórico
    renderizarHistorico();

    // 4. Define aba padrão
    alternarAba('checkout');

    // 5. Mostra o modal correto
    const modalPC = document.getElementById('modal-acerto');
    if (modalPC) modalPC.style.display = 'flex';

    const modalMob = document.getElementById('modal-acerto-mobile');
    if (modalMob) modalMob.style.display = 'flex';
}

function renderizarPassageiros(passageiros) {
    const tbodyPC = document.getElementById('lista-passageiros-checkin');
    const divMob = document.getElementById('lista-passageiros-mobile');

    // MODO PC (Tabela)
    if (tbodyPC) {
        tbodyPC.innerHTML = '';
        passageiros.forEach(p => {
            tbodyPC.innerHTML += `
                <tr>
                    <td><input type="checkbox" name="ids_passageiros" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()"></td>
                    <td>${p.nome}</td>
                    <td>${p.atividade || 'N/A'}</td>
                    <td>R$ ${p.valor_cobrado.toFixed(2)}</td>
                    <td>R$ ${p.pago.toFixed(2)}</td>
                    <td style="font-weight: bold; color: #ef4444;">R$ ${p.saldo.toFixed(2)}</td>
                </tr>
            `;
        });
        document.getElementById('input-valor-final').value = "0.00";
        const checkAll = document.getElementById('check-all-passageiros');
        if (checkAll) checkAll.checked = false;
    }

    // MODO MOBILE (Cards)
    if (divMob) {
        divMob.innerHTML = '';
        passageiros.forEach(p => {
            divMob.innerHTML += `
                <label class="item-passageiro">
                    <input type="checkbox" name="ids_passageiros" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()">
                    <div class="pass-info">
                        <div class="pass-nome">${p.nome}</div>
                        <div class="pass-ativ">${p.atividade || 'N/A'}</div>
                    </div>
                    <div class="pass-saldo">R$ ${p.saldo.toFixed(2)}</div>
                </label>
            `;
        });
        document.getElementById('input-valor-final-mobile').value = "0.00";
    }
}

function renderizarHistorico() {
    const tbodyPC = document.getElementById('lista-historico-pagamentos');
    const divMob = document.getElementById('lista-historico-mobile');

    if (historicoGlobal.length === 0) {
        if (tbodyPC) tbodyPC.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 30px; color: #94a3b8;">Nenhum pagamento registrado.</td></tr>';
        if (divMob) divMob.innerHTML = '<div style="text-align:center; padding: 30px; color:#94a3b8;">Nenhum pagamento registrado.</div>';
        return;
    }

    if (tbodyPC) tbodyPC.innerHTML = '';
    if (divMob) divMob.innerHTML = '';

    historicoGlobal.forEach(pg => {
        const isLoja = pg.recebedor === 'LOJA';
        const corRecebedor = isLoja ? 'color: #166534;' : 'color: #854d0e;';
        const bgRecebedor = isLoja ? 'background: #dcfce7; border: 1px solid #bbf7d0;' : 'background: #fef9c3; border: 1px solid #fef08a;';

        // Linha do PC
        if (tbodyPC) {
            tbodyPC.innerHTML += `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 12px; text-align: center; color: #64748b;">${pg.data || 'N/A'}</td>
                    <td style="padding: 12px; text-align: left; font-weight: 500;">${pg.passageiro || 'Grupo'}</td>
                    <td style="padding: 12px; text-align: center; font-weight: 600; color: #059669;">R$ ${pg.valor.toFixed(2)}</td>
                    <td style="padding: 12px; text-align: center;">
                        <span style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            ${pg.pagador || 'CLIENTE'}
                        </span>
                    </td>
                    <td style="padding: 12px; text-align: center;">
                        <span style="${bgRecebedor} ${corRecebedor} padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            ${pg.recebedor || 'N/A'}
                        </span>
                    </td>
                </tr>
            `;
        }

        // Card do Mobile
        if (divMob) {
            divMob.innerHTML += `
                <div class="item-historico">
                    <div class="hist-linha">
                        <span class="hist-data">${pg.data || 'N/A'}</span>
                        <span class="hist-valor">R$ ${pg.valor.toFixed(2)}</span>
                    </div>
                    <div style="font-size: 13px; color: #0f172a; margin-bottom: 8px;">${pg.passageiro || 'Grupo'}</div>
                    <div style="display: flex; gap: 5px;">
                        <span style="font-size: 10px; background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; font-weight: bold;">Por: ${pg.pagador || 'CLIENTE'}</span>
                        <span style="font-size: 10px; ${bgRecebedor} ${corRecebedor} padding: 3px 8px; border-radius: 4px; font-weight: bold;">Para: ${pg.recebedor}</span>
                    </div>
                </div>
            `;
        }
    });
}

function alternarAba(aba) {
    const checkout = document.getElementById('aba-checkout');
    const historico = document.getElementById('aba-historico');
    const btnCheck = document.getElementById('btn-tab-checkout');
    const btnHist = document.getElementById('btn-tab-historico');
    const footerMobile = document.getElementById('footer-inputs-pagamento'); // Só existe no mobile

    if (aba === 'checkout') {
        if(checkout) checkout.style.display = 'block';
        if(historico) historico.style.display = 'none';
        if(btnCheck) btnCheck.classList.add('active');
        if(btnHist) btnHist.classList.remove('active');
        if(footerMobile) footerMobile.style.display = 'block';
    } else {
        if(checkout) checkout.style.display = 'none';
        if(historico) historico.style.display = 'block';
        if(btnCheck) btnCheck.classList.remove('active');
        if(btnHist) btnHist.classList.add('active');
        if(footerMobile) footerMobile.style.display = 'none';
        renderizarHistorico(); 
    }
}

function recalcularTotalCheckin() {
    let total = 0;
    document.querySelectorAll('input[name="ids_passageiros"]:checked').forEach(c => {
        total += parseFloat(c.getAttribute('data-saldo'));
    });
    
    const inputPC = document.getElementById('input-valor-final');
    if (inputPC) inputPC.value = total.toFixed(2);
    
    const inputMob = document.getElementById('input-valor-final-mobile');
    if (inputMob) inputMob.value = total.toFixed(2);
}

function selecionarTodosPassageiros(source) {
    const checkboxes = document.querySelectorAll('input[name="ids_passageiros"]');
    checkboxes.forEach(c => c.checked = source.checked);
    recalcularTotalCheckin();
}

function fecharModalAcerto() {
    const modalPC = document.getElementById('modal-acerto');
    if (modalPC) modalPC.style.display = 'none';

    const modalMob = document.getElementById('modal-acerto-mobile');
    if (modalMob) modalMob.style.display = 'none';
}