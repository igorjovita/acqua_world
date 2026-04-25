let historicoGlobal = [];

function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor, historicoJson) {
    const resIdPC = document.getElementById('modal-reserva-id');
    const resIdMob = document.getElementById('modal-reserva-id-mobile');
    if (resIdPC) resIdPC.value = id;
    if (resIdMob) resIdMob.value = id;

    // Reseta inputs de edição ao abrir
    if(document.getElementById('pagamento-id-edicao-pc')) document.getElementById('pagamento-id-edicao-pc').value = "";
    if(document.getElementById('pagamento-id-edicao-mobile')) document.getElementById('pagamento-id-edicao-mobile').value = "";
    if(document.getElementById('btn-confirmar-mobile')) document.getElementById('btn-confirmar-mobile').innerText = "Confirmar Recebimento";

    const tituloPC = document.getElementById('modal-titulo-reserva');
    const vendPC = document.getElementById('modal-vendedor-reserva');
    if (tituloPC) tituloPC.innerText = "Reserva: " + nome;
    if (vendPC) vendPC.innerText = "Vendedor: " + (vendedor || 'N/A');

    const tituloMob = document.getElementById('modal-titulo');
    if (tituloMob) tituloMob.innerText = nome.toUpperCase();

    try {
        const textoHistorico = (historicoJson && historicoJson !== 'undefined') ? historicoJson : '[]';
        historicoGlobal = JSON.parse(textoHistorico);
    } catch (e) { historicoGlobal = []; }

    try {
        const passageiros = JSON.parse(passageirosJson);
        renderizarPassageiros(passageiros);
    } catch (e) {}

    renderizarHistorico();
    alternarAba('checkout');

    const modalPC = document.getElementById('modal-acerto');
    if (modalPC) modalPC.style.display = 'flex';

    const modalMob = document.getElementById('modal-acerto-mobile');
    if (modalMob) modalMob.style.display = 'flex';
}

function renderizarPassageiros(passageiros) {
    const tbodyPC = document.getElementById('lista-passageiros-checkin');
    const divMob = document.getElementById('lista-passageiros-mobile');

    if (tbodyPC) {
        tbodyPC.innerHTML = '';
        passageiros.forEach(p => {
            tbodyPC.innerHTML += `
                <tr>
                    <td><input type="checkbox" name="ids_passageiros" id="check-pc-${p.id_cr}" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()"></td>
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

    if (divMob) {
        divMob.innerHTML = '';
        passageiros.forEach(p => {
            divMob.innerHTML += `
                <label class="item-passageiro">
                    <input type="checkbox" name="ids_passageiros" id="check-mob-${p.id_cr}" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()">
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
        if (tbodyPC) tbodyPC.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 30px; color: #94a3b8;">Nenhum pagamento registrado.</td></tr>';
        if (divMob) divMob.innerHTML = '<div style="text-align:center; padding: 30px; color:#94a3b8;">Nenhum pagamento registrado.</div>';
        return;
    }

    if (tbodyPC) tbodyPC.innerHTML = '';
    if (divMob) divMob.innerHTML = '';

    historicoGlobal.forEach(pg => {
        const isLoja = pg.recebedor === 'LOJA';
        const corRec = isLoja ? 'color: #166534;' : 'color: #854d0e;';
        const bgRec = isLoja ? 'background: #dcfce7; border: 1px solid #bbf7d0;' : 'background: #fef9c3; border: 1px solid #fef08a;';

        if (tbodyPC) {
            tbodyPC.innerHTML += `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 12px; text-align: center; color: #64748b;">${pg.data || 'N/A'}</td>
                    <td style="padding: 12px; text-align: left; font-weight: 500;">${pg.passageiro || 'Grupo'}</td>
                    <td style="padding: 12px; text-align: center; font-weight: 600; color: #059669;">R$ ${pg.valor.toFixed(2)}</td>
                    <td style="padding: 12px; text-align: center;">
                        <span style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">${pg.pagador || 'CLIENTE'}</span>
                    </td>
                    <td style="padding: 12px; text-align: center;">
                        <span style="${bgRec} ${corRec} padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">${pg.recebedor || 'N/A'}</span>
                    </td>
                    <td style="padding: 12px; text-align: center; display: flex; gap: 5px; justify-content: center;">
                        <button type="button" onclick="editarPagamento(${pg.id})" style="background:#f59e0b; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;" title="Editar"><span class="material-symbols-outlined" style="font-size:16px;">edit</span></button>
                        <button type="button" onclick="deletarPagamento(${pg.id})" style="background:#ef4444; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;" title="Excluir"><span class="material-symbols-outlined" style="font-size:16px;">delete</span></button>
                    </td>
                </tr>
            `;
        }

        if (divMob) {
            divMob.innerHTML += `
                <div class="swipe-container" ontouchstart="handleTouchStart(event)" ontouchmove="handleTouchMove(event)" ontouchend="handleTouchEnd(event, this)">
                    <div class="swipe-content">
                        <div class="hist-linha">
                            <span class="hist-data">${pg.data || 'N/A'}</span>
                            <span class="hist-valor">R$ ${pg.valor.toFixed(2)}</span>
                        </div>
                        <div style="font-size: 13px; color: #0f172a; margin-bottom: 8px;">${pg.passageiro || 'Grupo'}</div>
                        <div style="display: flex; gap: 5px;">
                            <span style="font-size: 10px; background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; font-weight: bold;">Por: ${pg.pagador || 'CLIENTE'}</span>
                            <span style="font-size: 10px; ${bgRec} ${corRec} padding: 3px 8px; border-radius: 4px; font-weight: bold;">Para: ${pg.recebedor}</span>
                        </div>
                    </div>
                    <div class="swipe-actions">
                        <button type="button" class="btn-swipe btn-swipe-edit" onclick="editarPagamento(${pg.id})"><span class="material-symbols-outlined">edit</span>Editar</button>
                        <button type="button" class="btn-swipe btn-swipe-del" onclick="deletarPagamento(${pg.id})"><span class="material-symbols-outlined">delete</span>Apagar</button>
                    </div>
                </div>
            `;
        }
    });
}

// =====================================
// FUNÇÕES DE EDIÇÃO E EXCLUSÃO
// =====================================
function editarPagamento(id_pag) {
    const pg = historicoGlobal.find(p => p.id === id_pag);
    if (!pg) return;

    // Desmarca todos primeiro
    document.querySelectorAll('input[name="ids_passageiros"]').forEach(c => c.checked = false);
    
    // Marca apenas o cliente do pagamento (PC ou Mobile)
    const checkPC = document.getElementById(`check-pc-${pg.id_cr}`);
    const checkMob = document.getElementById(`check-mob-${pg.id_cr}`);
    if(checkPC) checkPC.checked = true;
    if(checkMob) checkMob.checked = true;

    // Seta IDs ocultos
    if(document.getElementById('pagamento-id-edicao-pc')) document.getElementById('pagamento-id-edicao-pc').value = pg.id;
    if(document.getElementById('pagamento-id-edicao-mobile')) document.getElementById('pagamento-id-edicao-mobile').value = pg.id;

    // Preenche Formulário PC (Se existir)
    if(document.querySelector('input[name="data_pagamento"]')) document.querySelector('input[name="data_pagamento"]').value = pg.data_iso;
    if(document.getElementById('input-valor-final')) document.getElementById('input-valor-final').value = pg.valor.toFixed(2);
    if(document.querySelector('select[name="forma_pg"]')) document.querySelector('select[name="forma_pg"]').value = pg.forma;
    if(document.querySelector('select[name="recebedor_pg"]')) document.querySelector('select[name="recebedor_pg"]').value = pg.recebedor;

    // Preenche Formulário Mobile (Se existir)
    if(document.getElementById('data-pagamento-mobile')) document.getElementById('data-pagamento-mobile').value = pg.data_iso;
    if(document.getElementById('input-valor-final-mobile')) document.getElementById('input-valor-final-mobile').value = pg.valor.toFixed(2);
    if(document.getElementById('forma-pg-mobile')) document.getElementById('forma-pg-mobile').value = pg.forma;
    if(document.getElementById('recebedor-pg-mobile')) document.getElementById('recebedor-pg-mobile').value = pg.recebedor;
    if(document.getElementById('btn-confirmar-mobile')) document.getElementById('btn-confirmar-mobile').innerText = "Salvar Edição";

    // Vai pra tela de acerto
    alternarAba('checkout');
}

function deletarPagamento(id_pag) {
    if (confirm("Tem certeza que deseja apagar este pagamento permanentemente? Isso também removerá o valor do Livro Caixa.")) {
        const inputId = document.getElementById('delete-pagamento-id');
        const formDelete = document.getElementById('form-delete-pagamento');
        if (inputId && formDelete) {
            inputId.value = id_pag;
            formDelete.submit();
        }
    }
}

// =====================================
// LÓGICA DE SWIPE MOBILE
// =====================================
let startX = 0;
function handleTouchStart(e) { startX = e.touches[0].clientX; }
function handleTouchMove(e) { /* Opcional: Animação acompanhando o dedo */ }
function handleTouchEnd(e, container) {
    const endX = e.changedTouches[0].clientX;
    const swipeContent = container.querySelector('.swipe-content');
    
    // Fecha todos os outros abertos
    document.querySelectorAll('.swipe-content').forEach(el => {
        if(el !== swipeContent) el.classList.remove('swiped');
    });

    if (startX - endX > 50) {
        swipeContent.classList.add('swiped'); // Deslizou pra esquerda (Abre)
    } else if (endX - startX > 50) {
        swipeContent.classList.remove('swiped'); // Deslizou pra direita (Fecha)
    }
}

// =====================================
// NAVEGAÇÃO E RECALCULO
// =====================================
function alternarAba(aba) {
    const checkout = document.getElementById('aba-checkout');
    const historico = document.getElementById('aba-historico');
    const btnCheck = document.getElementById('btn-tab-checkout');
    const btnHist = document.getElementById('btn-tab-historico');
    const footerMobile = document.getElementById('footer-inputs-pagamento');

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
        
        // Fecha todos os swipes que ficaram abertos
        document.querySelectorAll('.swipe-content').forEach(el => el.classList.remove('swiped'));
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
    document.querySelectorAll('input[name="ids_passageiros"]').forEach(c => c.checked = source.checked);
    recalcularTotalCheckin();
}

function fecharModalAcerto() {
    if(document.getElementById('modal-acerto')) document.getElementById('modal-acerto').style.display = 'none';
    if(document.getElementById('modal-acerto-mobile')) document.getElementById('modal-acerto-mobile').style.display = 'none';
}