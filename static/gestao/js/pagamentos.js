function abrirModalAcerto(reservaId, nomeExibicao, saldoTotal, passageirosJsonStr) {
    document.getElementById('modal-acerto').style.display = 'flex';
    document.getElementById('modal-reserva-id').value = reservaId;
    document.getElementById('modal-titulo-reserva').textContent = `Acerto: ${nomeExibicao}`;
    
    // Formata o saldo total no cabeçalho
    document.getElementById('modal-saldo-total').textContent = saldoTotal.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
    
    // Preenche o input automático do pagamento em grupo
    document.getElementById('input-valor-grupo').value = saldoTotal.toFixed(2);
    
    // Processa a lista de passageiros
    const passageiros = JSON.parse(passageirosJsonStr);
    const containerInd = document.getElementById('container-passageiros-pagamento');
    containerInd.innerHTML = ''; // Limpa anterior
    
    passageiros.forEach((p, index) => {
        // Se o saldo for 0, o passageiro já pagou a parte dele
        const jaPago = p.saldo <= 0;
        
        containerInd.innerHTML += `
            <div class="linha-passageiro-pg ${jaPago ? 'pg-concluido' : ''}">
                <div class="info-pg-pessoal">
                    <strong>${p.nome}</strong>
                    <span class="info-sinal">Sinal pago: R$ ${p.pago.toFixed(2)} (${p.recebedor})</span>
                </div>
                
                <input type="hidden" name="id_cr" value="${p.id_cr}">
                
                <div class="inputs-pg-pessoal">
                    <div style="width: 120px;">
                        <label>Saldo (R$)</label>
                        <input type="number" step="0.01" name="valor_ind" class="modern-input" value="${jaPago ? '0.00' : p.saldo.toFixed(2)}" ${jaPago ? 'readonly' : ''}>
                    </div>
                    <div style="flex: 1;">
                        <label>Forma PG</label>
                        <select name="forma_pg_ind" class="modern-input" ${jaPago ? 'disabled' : ''}>
                            <option value="PIX">Pix</option>
                            <option value="DINHEIRO">Dinheiro</option>
                            <option value="CREDITO">Crédito</option>
                            <option value="DEBITO">Débito</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Reseta o toggle para grupo por padrão
    document.getElementById('tipo_acerto').value = 'grupo';
    alternarModoPagamento();
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