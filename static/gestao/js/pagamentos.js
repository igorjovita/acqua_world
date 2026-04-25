function abrirModalAcerto(id, nome, saldo, passageirosJson, vendedor) {
    document.getElementById('modal-reserva-id').value = id;
    document.getElementById('modal-titulo-reserva').innerText = "Reserva: " + nome;
    document.getElementById('modal-vendedor-reserva').innerText = "Vendedor: " + vendedor;
    
    const passageiros = JSON.parse(passageirosJson);
    const tbody = document.getElementById('lista-passageiros-checkin');
    tbody.innerHTML = '';

    passageiros.forEach(p => {
        const row = `
            <tr>
                <td><input type="checkbox" name="ids_passageiros" value="${p.id_cr}" data-saldo="${p.saldo}" onchange="recalcularTotalCheckin()"></td>
                <td>${p.nome}</td>
                <td>${p.atividade}</td>
                <td>R$ ${p.valor_cobrado.toFixed(2)}</td>
                <td>R$ ${p.pago.toFixed(2)}</td>
                <td style="font-weight: bold; color: #ef4444;">R$ ${p.saldo.toFixed(2)}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    document.getElementById('input-valor-final').value = "0.00";
    document.getElementById('modal-acerto').style.display = 'flex';
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