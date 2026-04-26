// ==========================================
// FUNÇÕES DOS MODAIS DE CADASTRO RÁPIDO
// ==========================================
function abrirModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function fecharModal(id) {
    document.getElementById(id).style.display = 'none';
}

// ==========================================
// 1. CARREGAMENTO DOS DADOS DO BACKEND
// ==========================================
let atividades = [];

try {
    const rawData = document.getElementById('atividades-data').textContent;
    if (rawData.trim() !== '') {
        atividades = JSON.parse(rawData);
    }
} catch (e) {
    console.error("Nenhum dado de atividade encontrado ou erro de formatação.", e);
}

// Trava de segurança: Garante que atividades seja sempre uma lista (Array)
if (!Array.isArray(atividades)) {
    atividades = [];
}

// Prepara as opções dos Selects de Atividade
let optionsAtividades = '<option value="" disabled selected hidden>Selecione a atividade...</option>';
atividades.forEach(ativ => {
    optionsAtividades += `<option value="${ativ.id}" data-valor="${ativ.valor_padrao}">${ativ.apelido}</option>`;
});

// ==========================================
// 2. CONTROLE PRINCIPAL DA TELA
// ==========================================
const quantidadeClientes = document.getElementById('quantidade-cliente');
const containerClientes = document.getElementById('container-clientes');
const formActions = document.getElementById('form-actions'); // Botão de salvar
let memoriaClientes = {};

quantidadeClientes.addEventListener('input', function () {
    const quantidadeAtual = parseInt(this.value, 10) || 0;
    
    if (quantidadeAtual > 0) {
        if (formActions) formActions.style.display = 'flex';
    } else {
        if (formActions) formActions.style.display = 'none';
        containerClientes.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 40px; color: #94a3b8;">
                <span class="material-symbols-outlined" style="font-size: 48px; opacity: 0.5;">scuba_diving</span>
                <p>Informe a quantidade de mergulhadores acima para iniciar o preenchimento.</p>
            </div>`;
        return;
    }

    // Salva na memória ANTES de limpar (AGORA SALVA O STATUS DO PIER)
    document.querySelectorAll('.mergulhador-card').forEach((el, index) => {
        const i = index + 1;
        memoriaClientes[i] = {
            nome: document.getElementById(`nome-${i}`)?.value || '',
            status_checkin: document.getElementById(`status-checkin-hidden-${i}`)?.value || '', // <- SALVA O PIER
            telefone: document.getElementById(`telefone-${i}`)?.value || '',
            documento: document.getElementById(`doc-${i}`)?.value || '',
            peso: document.getElementById(`peso-${i}`)?.value || '',
            altura: document.getElementById(`altura-${i}`)?.value || '',
            atividade: document.getElementById(`atividade-${i}`)?.value || '',
            valor: document.getElementById(`valor-${i}`)?.value || '',
            temSinal: document.getElementById(`tem-sinal-${i}`)?.value || 'nao',
            valorSinal: document.getElementById(`valor-sinal-${i}`)?.value || '',
            formaPgSinal: document.getElementById(`forma-pg-sinal-${i}`)?.value || '',
            recebedorSinal: document.getElementById(`recebedor-sinal-${i}`)?.value || 'LOJA',
            cr_id: document.getElementById(`cr-id-${i}`)?.value || '' // Guarda o ID oculto se existir
        };
    });

    containerClientes.innerHTML = ""; 

    for (let i = 1; i <= quantidadeAtual; i++) {
        const divCliente = document.createElement('div');
        divCliente.classList.add('mergulhador-card');

        // Cria o campo de ID oculto para edição
        const inputHiddenID = `<input type="hidden" name="cr_id" id="cr-id-${i}" value="">`;

        // Puxa da memória se é PIER ou se está em branco
        const statusMemoria = memoriaClientes[i] ? (memoriaClientes[i].status_checkin || "") : "";
        const isPier = (statusMemoria === "PIER");

        divCliente.innerHTML = `
            <div class="card-header">
                <h3><span class="material-symbols-outlined">person</span> Mergulhador ${i}</h3>
            </div>
            
            <div class="card-body">
                ${inputHiddenID}
                <div class="secao-interna">
                    <div class="fields-row">
                        <div class="inputs field-group" style="flex: 2; min-width: 200px;">
                            <label>Nome Completo:</label>
                            <input type="text" name="nome" id="nome-${i}" class="modern-input" required>
                        </div>
                        
                        <div class="inputs field-group" style="flex: 1; min-width: 150px; display: flex; align-items: flex-end; padding-bottom: 5px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #475569; font-weight: 500; font-size: 13px; margin:0;">
                                <input type="checkbox" id="check-pier-${i}"
                                       onchange="this.nextElementSibling.value = this.checked ? 'PIER' : ''" 
                                       ${isPier ? 'checked' : ''} 
                                       style="width: 18px; height: 18px; cursor: pointer;">
                                <input type="hidden" name="status_checkin" id="status-checkin-hidden-${i}" value="${statusMemoria}">
                                <span class="material-symbols-outlined" style="color: #eab308; font-size: 18px;">sailing</span>
                                Direto pro Pier (Amarelo)
                            </label>
                        </div>
                    </div>

                    <div class="fields-row" style="margin-top: 10px;">
                        <div class="inputs field-group" style="flex: 1; min-width: 150px;">
                            <label>Telefone:</label>
                            <input type="tel" name="telefone" id="telefone-${i}" class="modern-input" placeholder="(22) 99999-9999">
                        </div>
                        <div class="inputs field-group" style="flex: 1; min-width: 150px;">
                            <label>Documento (RG/CPF):</label>
                            <input type="text" name="documento" id="doc-${i}" class="modern-input">
                        </div>
                    </div>
                </div>

                <div class="secao-interna">
                    <div class="fields-row">
                        <div class="inputs field-group" style="width: 90px;">
                            <label>Peso (kg):</label>
                            <input type="number" step="0.1" name="peso" id="peso-${i}" class="modern-input">
                        </div>
                        <div class="inputs field-group" style="width: 90px;">
                            <label>Alt. (m):</label>
                            <input type="number" step="0.01" name="altura" id="altura-${i}" class="modern-input">
                        </div>
                        <div class="inputs field-group" style="flex: 2; min-width: 200px;">
                            <label>Atividade:</label>
                            <select name="atividade" id="atividade-${i}" class="modern-input select-atividade" required>
                                ${optionsAtividades}
                            </select>
                        </div>
                    </div>
                </div>

                <div class="secao-interna" style="border-bottom: none; margin-bottom: 0; padding-bottom: 0;">
                    <div class="fields-row" style="align-items: flex-end;">
                        <div class="inputs field-group" style="flex: 1;">
                            <label>Valor a receber (R$):</label>
                            <input type="number" step="0.01" name="valor" id="valor-${i}" class="modern-input valor-input" style="font-weight: bold; color: #091521;" required>
                        </div>
                        <div class="inputs field-group" style="flex: 1;">
                            <label>Pagou Sinal?</label>
                            <select id="tem-sinal-${i}" class="modern-input toggle-sinal" data-target="box-sinal-${i}">
                                <option value="nao">Não</option>
                                <option value="sim">Sim, adiantou valor</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div id="box-sinal-${i}" class="box-sinal-expandivel">
                    <input type="hidden" name="tem_sinal" id="hidden-sinal-${i}" value="nao">
                    <div class="fields-row" style="margin-bottom: 0;">
                        <div class="inputs field-group">
                            <label>Valor do Sinal (R$):</label>
                            <input type="number" step="0.01" name="valor_sinal" id="valor-sinal-${i}" class="modern-input input-req-${i}">
                        </div>
                        <div class="inputs field-group">
                            <label>Forma do Sinal:</label>
                            <select name="forma_pg_sinal" id="forma-pg-sinal-${i}" class="modern-input input-req-${i}">
                                <option value="" disabled selected hidden>Selecione...</option>
                                <option value="PIX">Pix</option>
                                <option value="DINHEIRO">Dinheiro</option>
                                <option value="CREDITO">Crédito</option>
                                <option value="DEBITO">Débito</option>
                            </select>
                        </div>
                        <div class="inputs field-group">
                            <label>Recebedor do Sinal:</label>
                            <select name="recebedor_sinal" id="recebedor-sinal-${i}" class="modern-input">
                                <option value="LOJA">Acqua World (Loja)</option>
                                <option value="VENDEDOR">Comissário (Retido)</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="inputs field-group" style="flex: 100%; margin-top: 10px;">
                    <label>Observação Interna (Aparece na Planilha):</label>
                    <input type="text" name="observacao" id="obs-${i}" class="modern-input">
                </div>
            </div>
        `;

        containerClientes.appendChild(divCliente);

        // Preenchimento automático do valor total
        document.getElementById(`atividade-${i}`).addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const valorPadrao = selectedOption.getAttribute('data-valor');
            const inputValor = document.getElementById(`valor-${i}`);
            if (valorPadrao && !inputValor.value) { 
                inputValor.value = parseFloat(valorPadrao).toFixed(2);
            }
        });

        // Evento para abrir/fechar a caixinha de Sinal
        document.getElementById(`tem-sinal-${i}`).addEventListener('change', function() {
            const box = document.getElementById(this.getAttribute('data-target'));
            const inputsParaObrigar = document.querySelectorAll(`.input-req-${i}`);
            const inputHidden = document.getElementById(`hidden-sinal-${i}`);
            
            if (this.value === 'sim') {
                box.classList.add('ativo');
                inputHidden.value = 'sim';
                inputsParaObrigar.forEach(inp => inp.required = true);
            } else {
                box.classList.remove('ativo');
                inputHidden.value = 'nao';
                inputsParaObrigar.forEach(inp => { inp.required = false; inp.value = ''; });
                document.getElementById(`recebedor-sinal-${i}`).value = 'LOJA';
            }
        });

        // RESTAURAÇÃO DE MEMÓRIA (Se o usuário apagar/adicionar clientes ou na EDIÇÃO)
        if (memoriaClientes[i]) {
            document.getElementById(`cr-id-${i}`).value = memoriaClientes[i].cr_id || '';
            document.getElementById(`nome-${i}`).value = memoriaClientes[i].nome;
            document.getElementById(`telefone-${i}`).value = memoriaClientes[i].telefone;
            document.getElementById(`doc-${i}`).value = memoriaClientes[i].documento;
            document.getElementById(`peso-${i}`).value = memoriaClientes[i].peso;
            document.getElementById(`altura-${i}`).value = memoriaClientes[i].altura;
            document.getElementById(`atividade-${i}`).value = memoriaClientes[i].atividade;
            document.getElementById(`valor-${i}`).value = memoriaClientes[i].valor;
            document.getElementById(`obs-${i}`).value = memoriaClientes[i].observacao || '';
            const selectSinal = document.getElementById(`tem-sinal-${i}`);
            selectSinal.value = memoriaClientes[i].temSinal;
            if (memoriaClientes[i].temSinal === 'sim') {
                selectSinal.dispatchEvent(new Event('change'));
                document.getElementById(`valor-sinal-${i}`).value = memoriaClientes[i].valorSinal;
                document.getElementById(`forma-pg-sinal-${i}`).value = memoriaClientes[i].formaPgSinal;
                document.getElementById(`recebedor-sinal-${i}`).value = memoriaClientes[i].recebedorSinal;
            }
        }
    }
});

// O Gatilho da Edição que preenche tudo automático!
document.addEventListener('DOMContentLoaded', () => {
    if (typeof DADOS_EDICAO !== 'undefined' && DADOS_EDICAO !== null) {
        
        document.getElementById('reserva-id-edicao').value = DADOS_EDICAO.reserva_id;
        document.querySelector('input[type="date"]').value = DADOS_EDICAO.data;
        document.querySelector('select[name="vendedor"]').value = DADOS_EDICAO.vendedor;
        
        let selectQtde = document.getElementById('quantidade-cliente');
        selectQtde.value = DADOS_EDICAO.quantidade;

        // Ao invés de usar setTimeOut, preenchemos a 'memória' e forçamos a tela a se desenhar
        DADOS_EDICAO.clientes.forEach((cli, index) => {
            let i = index + 1;
            memoriaClientes[i] = {
                cr_id: cli.cr_id, 
                nome: cli.nome,
                status_checkin: cli.status_checkin || '', // <-- PUXA O STATUS DA EDIÇÃO
                telefone: cli.telefone,
                documento: cli.documento,
                peso: cli.peso,
                altura: cli.altura,
                atividade: cli.atividade,
                valor: cli.valor,
                temSinal: cli.tem_sinal,
                valorSinal: cli.valor_sinal,
                formaPgSinal: cli.forma_pg_sinal,
                recebedorSinal: cli.recebedor_sinal,
                observacao: cli.observacao || ''
            };
        });

        // Dispara o evento para desenhar os cards baseados na memória que acabamos de injetar
        selectQtde.dispatchEvent(new Event('input'));
    }
});