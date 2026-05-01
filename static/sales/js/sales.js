// =====================================================================
// 1. SEGURANÇA E UTILITÁRIOS
// =====================================================================
const Utils = {
    escapeHTML(str) {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g, tag => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
        }[tag]));
    },
    gerarIdUnico() {
        return 'cr_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 5);
    }
};

// =====================================================================
// 2. SCHEMA E VALIDAÇÃO (Camada de Integridade)
// =====================================================================
const criarMergulhadorBase = (id) => ({
    id: id, cr_id: '', nome: '', status_checkin: '', telefone: '',
    documento: '', peso: '', altura: '', atividade: '', valor: '',
    temSinal: 'nao', valorSinal: '', formaPgSinal: '', recebedorSinal: '', 
    observacao: '', isCortesia: 'nao', precisaPratica2: false, dataPratica2: ''
});

// Validador simples: impede que letras entrem em campos de dinheiro/peso
const validarDado = (campo, valor) => {
    const camposNumericos = ['peso', 'altura', 'valor', 'valorSinal'];
    if (camposNumericos.includes(campo) && valor !== '') {
        if (isNaN(parseFloat(valor.replace(',', '.')))) return false;
    }
    return true;
};

// =====================================================================
// 3. STORE (Imutabilidade e Batching de Render)
// =====================================================================
const ReservaStore = {
    state: {
        byId: {}, 
        allIds: []
    },
    
    listeners: [],
    renderPendente: false, // Trava de Batching

    subscribe(listenerFunc) {
        this.listeners.push(listenerFunc);
    },

    // BATCHING: Agrupa várias mudanças em um único "frame" da tela
    notify() {
        if (!this.renderPendente) {
            this.renderPendente = true;
            // requestAnimationFrame aguarda o navegador estar pronto para desenhar a próxima tela
            requestAnimationFrame(() => {
                this.listeners.forEach(listener => listener(this.state));
                this.renderPendente = false;
            });
        }
    },

    ajustarQuantidade(novaQtd) {
        const atual = this.state.allIds.length;
        // IMUTABILIDADE: Criamos cópias do estado, nunca alteramos diretamente
        let nextById = { ...this.state.byId };
        let nextAllIds = [ ...this.state.allIds ];
        
        if (novaQtd > atual) {
            for (let i = atual; i < novaQtd; i++) {
                const novoId = Utils.gerarIdUnico();
                nextById[novoId] = criarMergulhadorBase(novoId);
                nextAllIds.push(novoId);
            }
        } else if (novaQtd < atual) {
            const idsRemovidos = nextAllIds.splice(novaQtd);
            idsRemovidos.forEach(id => delete nextById[id]);
        }

        this.state = { byId: nextById, allIds: nextAllIds };
        this.notify();
    },

    atualizarCampo(id, campo, valor) {
        if (!validarDado(campo, valor)) return; // Trava de validação
        if (!this.state.byId[id]) return;

        // IMUTABILIDADE: Object Spread Syntax (Padrão Redux)
        this.state = {
            ...this.state,
            byId: {
                ...this.state.byId,
                [id]: {
                    ...this.state.byId[id],
                    [campo]: valor
                }
            }
        };
        this.notify();
    },

    processarRegraNegocio(id, campo, valor, elementoDisparador) {
        this.atualizarCampo(id, campo, valor);

        const cliente = this.state.byId[id];
        if (!cliente) return;

        // Regra 1: Atividade altera o Valor
        if (campo === 'atividade' && elementoDisparador) {
            const opcaoSelecionada = elementoDisparador.options[elementoDisparador.selectedIndex];
            const valorPadrao = opcaoSelecionada.getAttribute('data-valor');
            if (valorPadrao && !this.state.byId[id].valor) {
                this.atualizarCampo(id, 'valor', parseFloat(valorPadrao).toFixed(2));
            }
        }

        // Regra 2: Limpa resíduos se remover o sinal
        if (campo === 'temSinal' && valor === 'nao') {
            this.atualizarCampo(id, 'valorSinal', '');
            this.atualizarCampo(id, 'formaPgSinal', '');
            this.atualizarCampo(id, 'recebedorSinal', 'LOJA');
        }

        // REGRA DA CORTESIA: Se mudou para "sim", zera o valor e tira o sinal
        if (campo === 'isCortesia') {
            if (valor === 'sim') {
                this.atualizarCampo(id, 'valor', '0.00');
                this.atualizarCampo(id, 'temSinal', 'nao');
                this.atualizarCampo(id, 'valorSinal', '');
            } else {
                // Se ele desmarcou a cortesia, a gente apaga o zero pro cara digitar o valor real
                this.atualizarCampo(id, 'valor', '');
            }
        }

        if (campo === 'atividade' && elementoDisparador) {
            const opcao = elementoDisparador.options[elementoDisparador.selectedIndex];
            const valorPadrao = opcao.getAttribute('data-valor');
            
            // Puxa o apelido exato e oculto que colocamos no HTML
            const apelidoAtividade = opcao.getAttribute('data-apelido')?.toUpperCase() || '';

            // 1. Atualiza o valor financeiro (Mas SOMENTE se não for Cortesia)
            if (valorPadrao && !cliente.valor && cliente.isCortesia === 'nao') {
                this.atualizarCampo(id, 'valor', parseFloat(valorPadrao).toFixed(2));
            }

            // 2. Inteligência Exata da Prática 2: Agora é cravado!
            if (apelidoAtividade === 'OWD' || apelidoAtividade === 'ADV') {
                this.atualizarCampo(id, 'precisaPratica2', true);
            } else {
                this.atualizarCampo(id, 'precisaPratica2', false);
                this.atualizarCampo(id, 'dataPratica2', ''); // Limpa a data se ele mudar pra BAT
            }
        }
    }
};

// =====================================================================
// 4. VIEW & SYNC ENGINE (Reconciliação Completa / Diffing)
// =====================================================================
function syncDOM(estado) {
    const { allIds, byId } = estado;

    // 1. Remove cards que não existem mais
    Array.from(containerClientes.children).forEach(card => {
        if (!card.classList.contains('mergulhador-card')) return;
        if (!allIds.includes(card.getAttribute('data-id'))) {
            card.remove();
        }
    });

    // 2. Reconciliação (Diffing)
    allIds.forEach((id, index) => {
        const cliente = byId[id];
        let card = containerClientes.querySelector(`.mergulhador-card[data-id="${id}"]`);

        // Criação inicial se não existir
        if (!card) {
            card = document.createElement('div');
            card.className = 'mergulhador-card';
            card.setAttribute('data-id', id);
            card.innerHTML = gerarTemplateCard(index + 1, cliente);
            containerClientes.appendChild(card);
            return; // Já criamos com os dados certos, vamos pro próximo
        } 

        // Se JÁ EXISTE, atualiza cirurgicamente sem usar innerHTML
        card.querySelector('.titulo-mergulhador').innerHTML = `<span class="material-symbols-outlined">person</span> Mergulhador ${index + 1}`;

        // DIFFING COMPLETO DE INPUTS: Atualiza os valores da tela se a Store mudou por trás (ex: Regras de negócio)
        const inputs = card.querySelectorAll('input, select');
        inputs.forEach(input => {
            const nomeCampo = input.name;
            if (!nomeCampo || cliente[nomeCampo] === undefined) return;

            // Tratamento especial para Checkbox
            if (input.type === 'checkbox') {
                const isChecked = cliente[nomeCampo] !== '';
                if (input.checked !== isChecked) input.checked = isChecked;
                return;
            }

            // Só atualiza o input se o valor estiver diferente E se o usuário não estiver digitando nele agora
            // Isso evita que o cursor pule para o final enquanto a pessoa digita
            if (input.value !== String(cliente[nomeCampo]) && document.activeElement !== input) {
                input.value = cliente[nomeCampo];
            }
        });

        // UI State-Driven (Sinal)
        const boxSinal = card.querySelector('.box-sinal-expandivel');
        const inputsSinal = boxSinal.querySelectorAll('.input-req');
        if (cliente.temSinal === 'sim') {
            boxSinal.style.display = 'block';
            boxSinal.style.opacity = '1';              // <-- MARRETA DE OPACIDADE
            boxSinal.style.visibility = 'visible';
            inputsSinal.forEach(inp => inp.required = true);
        } else {
            boxSinal.style.display = 'none';
            boxSinal.style.opacity = '0';
            boxSinal.style.visibility = 'hidden';
            inputsSinal.forEach(inp => inp.required = false);
        }

        const boxPratica2 = card.querySelector('.box-pratica2');
        if (boxPratica2) {
            if (cliente.precisaPratica2) {
                boxPratica2.style.display = 'block';
                // Deixa o campo de data obrigatório para ele não esquecer!
                boxPratica2.querySelector('input').required = true; 
            } else {
                boxPratica2.style.display = 'none';
                boxPratica2.querySelector('input').required = false;
            }
        }

        // NOVA UI State-Driven: CORTESIA (Trava o campo de valor financeiro)
        const inputFinanceiro = card.querySelector('input[name="valor"]');
        if (inputFinanceiro) {
            if (cliente.isCortesia === 'sim') {
                inputFinanceiro.setAttribute('readonly', 'true');
                inputFinanceiro.style.backgroundColor = '#f1f5f9'; // Deixa cinza
            } else {
                inputFinanceiro.removeAttribute('readonly');
                inputFinanceiro.style.backgroundColor = 'transparent';
            }
        }
    });
}

ReservaStore.subscribe(syncDOM);

// =====================================================================
// 5. EVENT DELEGATION
// =====================================================================
const quantidadeClientes = document.getElementById('quantidade-cliente');
const containerClientes = document.getElementById('container-clientes');
const formActions = document.getElementById('form-actions');

quantidadeClientes.addEventListener('input', function () {
    const qtd = parseInt(this.value, 10) || 0;
    
    if (qtd <= 0) {
        if (formActions) formActions.style.display = 'none';
        containerClientes.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 40px; color: #94a3b8;">
                <span class="material-symbols-outlined" style="font-size: 48px; opacity: 0.5;">scuba_diving</span>
                <p>Informe a quantidade de mergulhadores acima para iniciar o preenchimento.</p>
            </div>`;
        ReservaStore.ajustarQuantidade(0);
        return;
    }

    if (formActions) formActions.style.display = 'flex';
    ReservaStore.ajustarQuantidade(qtd);
});

containerClientes.addEventListener('input', e => {
    const card = e.target.closest('.mergulhador-card');
    if (!card || !e.target.name) return;
    
    // Ignora os selects aqui para não rodar duas vezes
    if (e.target.tagName !== 'SELECT') {
        ReservaStore.processarRegraNegocio(card.getAttribute('data-id'), e.target.name, e.target.value, e.target);
    }
});

// Escuta cliques e seleções (Selects e Checkboxes)
containerClientes.addEventListener('change', e => {
    const card = e.target.closest('.mergulhador-card');
    if (!card || !e.target.name) return;
    
    // Regra do Checkbox do Pier
    if (e.target.classList.contains('check-pier')) {
        const valor = e.target.checked ? 'PIER' : '';
        ReservaStore.atualizarCampo(card.getAttribute('data-id'), 'status_checkin', valor);
        return;
    }

    // AQUI ESTAVA O PROBLEMA! Garante que as dropdowns (Atividade, Cortesia) rodem a regra
    if (e.target.tagName === 'SELECT') {
        ReservaStore.processarRegraNegocio(card.getAttribute('data-id'), e.target.name, e.target.value, e.target);
    }
});

function gerarTemplateCard(num, dados) {
    const isPier = dados.status_checkin === "PIER";
    
    // Geração dinâmica de options com o data-apelido blindado
    const optionsAtiv = atividades.map(a => 
        `<option value="${a.id}" data-valor="${a.valor_padrao}" data-apelido="${Utils.escapeHTML(a.apelido)}" ${dados.atividade == a.id ? 'selected' : ''}>${Utils.escapeHTML(a.apelido)}</option>`
    ).join('');

    return `
        <div class="card-header">
            <h3 class="titulo-mergulhador"><span class="material-symbols-outlined">person</span> Mergulhador ${num}</h3>
        </div>
        <div class="card-body">
            <input type="hidden" name="cr_id" value="${Utils.escapeHTML(dados.cr_id)}">
            
            <div class="secao-interna">
                <div class="fields-row">
                    <div class="inputs field-group" style="flex: 2; min-width: 200px;">
                        <label>Nome Completo:</label>
                        <input type="text" name="nome" class="modern-input" value="${Utils.escapeHTML(dados.nome)}" required>
                    </div>
                    <div class="inputs field-group" style="flex: 1; min-width: 150px; display: flex; align-items: flex-end; padding-bottom: 5px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #475569; font-weight: 500; font-size: 13px; margin:0;">
                            <input type="checkbox" class="check-pier" ${isPier ? 'checked' : ''} style="width: 18px; height: 18px; cursor: pointer;">
                            <input type="hidden" name="status_checkin" class="hidden-pier" value="${Utils.escapeHTML(dados.status_checkin)}">
                            <span class="material-symbols-outlined" style="color: #eab308; font-size: 18px;">sailing</span>
                            Direto pro Pier
                        </label>
                    </div>
                </div>
                <div class="fields-row" style="margin-top: 10px;">
                    <div class="inputs field-group" style="flex: 1; min-width: 150px;">
                        <label>Telefone:</label>
                        <input type="tel" name="telefone" class="modern-input" value="${Utils.escapeHTML(dados.telefone)}" placeholder="(22) 99999-9999">
                    </div>
                    <div class="inputs field-group" style="flex: 1; min-width: 150px;">
                        <label>Documento (RG/CPF):</label>
                        <input type="text" name="documento" class="modern-input" value="${Utils.escapeHTML(dados.documento)}">
                    </div>
                </div>
            </div>

            <div class="secao-interna">
                <div class="fields-row">
                    <div class="inputs field-group" style="width: 80px;">
                        <label>Peso(kg):</label>
                        <input type="number" step="0.1" name="peso" class="modern-input" value="${Utils.escapeHTML(dados.peso)}">
                    </div>
                    <div class="inputs field-group" style="width: 80px;">
                        <label>Alt.(m):</label>
                        <input type="number" step="0.01" name="altura" class="modern-input" value="${Utils.escapeHTML(dados.altura)}">
                    </div>
                    <div class="inputs field-group" style="flex: 2; min-width: 150px;">
                        <label>Atividade:</label>
                        <select name="atividade" class="modern-input" required>
                            <option value="">Selecione...</option>
                            ${optionsAtiv}
                        </select>
                    </div>
                    <!-- A CAIXA ESCONDIDA DA PRÁTICA 2 -->
                    <div class="inputs field-group box-pratica2" style="display: ${dados.precisaPratica2 ? 'block' : 'none'}; width: 140px; background: #fef08a;">
                        <label style="color: #854d0e;"><span class="material-symbols-outlined" style="font-size: 14px;">calendar_month</span> Prática 2:</label>
                        <input type="date" name="dataPratica2" class="modern-input" value="${Utils.escapeHTML(dados.dataPratica2)}" style="background: transparent;">
                    </div>
                </div>
            </div>

            <div class="secao-interna" style="border-bottom: none; margin-bottom: 0; padding-bottom: 0;">
                <div class="fields-row" style="align-items: flex-end;">
                    <div class="inputs field-group" style="width: 100px;">
                        <label>Cortesia?</label>
                        <select name="isCortesia" class="modern-input">
                            <option value="nao" ${dados.isCortesia === 'nao' ? 'selected' : ''}>Não</option>
                            <option value="sim" ${dados.isCortesia === 'sim' ? 'selected' : ''}>Sim (100%)</option>
                        </select>
                    </div>

                    <div class="inputs field-group" style="flex: 1;">
                        <label>Valor a receber (R$):</label>
                        <input type="number" step="0.01" name="valor" class="modern-input" value="${Utils.escapeHTML(dados.valor)}" style="font-weight: bold; color: #091521;" required>
                    </div>
                    <div class="inputs field-group" style="flex: 1;">
                        <label>Pagou Sinal?</label>
                        <select name="temSinal" class="modern-input">
                            <option value="nao" ${dados.temSinal === 'nao' ? 'selected' : ''}>Não</option>
                            <option value="sim" ${dados.temSinal === 'sim' ? 'selected' : ''}>Sim, adiantou valor</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- A CORREÇÃO ESTÁ AQUI: max-height: none; overflow: visible; -->
            <div class="box-sinal-expandivel" style="display: ${dados.temSinal === 'sim' ? 'block' : 'none'}; opacity: ${dados.temSinal === 'sim' ? '1' : '0'}; visibility: ${dados.temSinal === 'sim' ? 'visible' : 'hidden'}; transition: none; max-height: none; overflow: visible;">
                <div class="fields-row" style="margin-bottom: 0;">
                    <div class="inputs field-group">
                        <label>Valor do Sinal (R$):</label>
                        <input type="number" step="0.01" name="valorSinal" class="modern-input input-req" value="${Utils.escapeHTML(dados.valorSinal)}">
                    </div>
                    <div class="inputs field-group">
                        <label>Forma do Sinal:</label>
                        <select name="formaPgSinal" class="modern-input input-req">
                            <option value="" disabled ${!dados.formaPgSinal ? 'selected' : ''} hidden>Selecione...</option>
                            <option value="PIX" ${dados.formaPgSinal === 'PIX' ? 'selected' : ''}>Pix</option>
                            <option value="DINHEIRO" ${dados.formaPgSinal === 'DINHEIRO' ? 'selected' : ''}>Dinheiro</option>
                            <option value="CREDITO" ${dados.formaPgSinal === 'CREDITO' ? 'selected' : ''}>Crédito</option>
                            <option value="DEBITO" ${dados.formaPgSinal === 'DEBITO' ? 'selected' : ''}>Débito</option>
                        </select>
                    </div>
                    <div class="inputs field-group">
                        <label>Recebedor do Sinal:</label>
                        <select name="recebedorSinal" class="modern-input">
                            <option value="LOJA" ${dados.recebedorSinal === 'LOJA' ? 'selected' : ''}>Acqua World (Loja)</option>
                            <option value="VENDEDOR" ${dados.recebedorSinal === 'VENDEDOR' ? 'selected' : ''}>Comissário (Retido)</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <div class="inputs field-group" style="flex: 100%; margin-top: 10px;">
                <label>Observação Interna (Aparece na Planilha):</label>
                <input type="text" name="observacao" class="modern-input" value="${Utils.escapeHTML(dados.observacao)}">
            </div>
        </div>
    `;
}

// =====================================================================
// 7. INICIALIZAÇÃO E INTEGRAÇÃO COM BACKEND (DJANGO)
// =====================================================================

// 1. Carrega as atividades do Django
let atividades = [];
try {
    const rawData = document.getElementById('atividades-data').textContent;
    if (rawData.trim() !== '') {
        atividades = JSON.parse(rawData);
    }
} catch (e) {
    console.error("Nenhum dado de atividade encontrado.", e);
}

// 2. O Gatilho da Edição (Traduzido para a Arquitetura Nova)
document.addEventListener('DOMContentLoaded', () => {
    if (typeof DADOS_EDICAO !== 'undefined' && DADOS_EDICAO !== null) {
        
        // Preenche a capa da reserva
        document.getElementById('reserva-id-edicao').value = DADOS_EDICAO.reserva_id || '';
        document.querySelector('input[type="date"]').value = DADOS_EDICAO.data || '';
        document.querySelector('select[name="vendedor"]').value = DADOS_EDICAO.vendedor || '';
        
        const selectQtde = document.getElementById('quantidade-cliente');
        selectQtde.value = DADOS_EDICAO.quantidade;
        if (formActions) formActions.style.display = 'flex';

        // Passo 1: Diz para a Store criar as "caixinhas vazias" na quantidade certa
        ReservaStore.ajustarQuantidade(DADOS_EDICAO.quantidade);

        // Passo 2: Preenche cada caixinha com os dados que vieram do Banco de Dados
        DADOS_EDICAO.clientes.forEach((cli, index) => {
            // Pega o ID único (cr_...) que a Store acabou de gerar para esta posição
            const idNaStore = ReservaStore.state.allIds[index]; 
            
            // Injeta os dados cirurgicamente no Estado
            ReservaStore.atualizarCampo(idNaStore, 'cr_id', cli.cr_id || '');
            ReservaStore.atualizarCampo(idNaStore, 'nome', cli.nome || '');
            ReservaStore.atualizarCampo(idNaStore, 'status_checkin', cli.status_checkin || '');
            ReservaStore.atualizarCampo(idNaStore, 'telefone', cli.telefone || '');
            ReservaStore.atualizarCampo(idNaStore, 'documento', cli.documento || '');
            ReservaStore.atualizarCampo(idNaStore, 'peso', cli.peso || '');
            ReservaStore.atualizarCampo(idNaStore, 'altura', cli.altura || '');
            ReservaStore.atualizarCampo(idNaStore, 'atividade', cli.atividade || '');
            ReservaStore.atualizarCampo(idNaStore, 'valor', cli.valor || '');
            ReservaStore.atualizarCampo(idNaStore, 'temSinal', cli.tem_sinal || 'nao');
            ReservaStore.atualizarCampo(idNaStore, 'valorSinal', cli.valor_sinal || '');
            ReservaStore.atualizarCampo(idNaStore, 'formaPgSinal', cli.forma_pg_sinal || '');
            ReservaStore.atualizarCampo(idNaStore, 'recebedorSinal', cli.recebedor_sinal || 'LOJA');
            ReservaStore.atualizarCampo(idNaStore, 'observacao', cli.observacao || '');
        });
    }
});