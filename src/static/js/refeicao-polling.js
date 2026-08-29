/**
 * Polling dos números das refeições (vagas, reservas, status).
 * Usado nas telas de aluno, nutricionista e refeitório.
 *
 * Uma requisição por ciclo cobre todas as refeições da página: as telas
 * mostram a semana inteira, e uma requisição por refeição multiplicaria a
 * carga pelo tamanho do cardápio.
 *
 * O app `refeicoes` está montado na raiz do projeto (ver reservaif/urls.py),
 * por isso a URL da API não tem o prefixo /refeicoes/.
 */

const SELETORES_PADRAO = {
  vagas_disponiveis: 'data-vagas-disponiveis',
  vagas_ocupadas: 'data-vagas-ocupadas',
  reservas_ativas_count: 'data-reservas-count',
  reservas_validas_count: 'data-reservas-validas',
  presentes_count: 'data-presentes',
  limite_vagas: 'data-limite-vagas',
  status: 'data-status-reserva',
  vagas_display: 'data-vagas-display',
};

// Trava contra loop de recarregamento: servidor e API calculam
// `reserva_aberta` pela mesma propriedade do model, então não deveriam
// divergir de forma persistente — mas se divergirem, isto limita o estrago.
const INTERVALO_MIN_RELOAD_MS = 30000;
const CHAVE_ULTIMO_RELOAD = 'refeicao-polling:ultimo-reload';

class RefeicaoPolling {
  constructor(config = {}) {
    this.intervaloMs = config.intervaloMs || 5000;
    this.url = config.url || '/api/refeicoes/dados-atualizados/';
    this.pausarAbaInativa = config.pausarAbaInativa !== false;
    // Só as telas cujo HTML muda com a janela de reserva (o card do aluno)
    // precisam disto; nas demais o polling atualiza apenas números.
    this.recarregarSeEstadoMudou = config.recarregarSeEstadoMudou === true;
    this.ids = [];
    this.timer = null;
    this.ativo = true;

    if (this.pausarAbaInativa) {
      document.addEventListener('visibilitychange', () => {
        this.ativo = !document.hidden;
        // Ao voltar para a aba, atualiza na hora em vez de esperar o ciclo.
        if (this.ativo) this.atualizar();
      });
    }
  }

  iniciar(ids) {
    this.ids = Array.from(new Set(ids)).filter(Boolean);
    if (!this.ids.length || this.timer) return;
    this.timer = setInterval(() => {
      if (this.ativo) this.atualizar();
    }, this.intervaloMs);
  }

  parar() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  atualizar() {
    if (!this.ids.length) return;
    const url = `${this.url}?ids=${encodeURIComponent(this.ids.join(','))}`;

    fetch(url)
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        const refeicoes = payload && payload.refeicoes;
        if (!refeicoes) return;

        let precisaRecarregar = false;
        for (const [refeicaoId, dados] of Object.entries(refeicoes)) {
          this._aplicar(refeicaoId, dados);
          if (this._htmlEstaDesatualizado(refeicaoId, dados)) {
            precisaRecarregar = true;
          }
        }

        document.dispatchEvent(
          new CustomEvent('refeicoes:atualizadas', { detail: { refeicoes } })
        );

        if (precisaRecarregar) this._recarregar();
      })
      .catch(() => {
        // Falha de rede não deve quebrar a página; o próximo ciclo tenta de novo.
      });
  }

  /**
   * True quando o card foi renderizado com uma janela de reserva diferente da
   * atual — o aviso "Reservas abrem em..." e o botão RESERVAR são escolhidos no
   * template, então só um novo render troca um pelo outro.
   */
  _htmlEstaDesatualizado(refeicaoId, dados) {
    if (!this.recarregarSeEstadoMudou) return false;
    if (typeof dados.reserva_aberta !== 'boolean') return false;

    const card = document.querySelector(
      `[data-refeicao-id="${refeicaoId}"][data-reserva-aberta]`
    );
    if (!card) return false;

    return (card.getAttribute('data-reserva-aberta') === '1') !== dados.reserva_aberta;
  }

  _recarregar() {
    // A aba oculta não ganha nada recarregando; ao voltar, o polling refaz a
    // checagem e recarrega aí.
    if (document.hidden) return;

    const agora = Date.now();
    try {
      const ultimo = Number(sessionStorage.getItem(CHAVE_ULTIMO_RELOAD));
      if (ultimo && agora - ultimo < INTERVALO_MIN_RELOAD_MS) return;
      sessionStorage.setItem(CHAVE_ULTIMO_RELOAD, String(agora));
    } catch (e) {
      // sessionStorage indisponível (aba anônima, storage bloqueado): segue sem
      // a trava, que é só uma proteção contra loop.
    }

    this.parar();
    window.location.reload();
  }

  _aplicar(refeicaoId, dados) {
    for (const [campo, atributo] of Object.entries(SELETORES_PADRAO)) {
      if (dados[campo] === undefined) continue;
      document
        .querySelectorAll(`[${atributo}="${refeicaoId}"]`)
        .forEach((el) => {
          el.textContent = dados[campo];
        });
    }
  }
}

/**
 * Inicia o polling para toda refeição presente na página, identificada por
 * qualquer um dos atributos data-* conhecidos.
 */
function iniciarPollingDaPagina(config = {}) {
  const polling = new RefeicaoPolling(config);
  const ids = new Set();

  Object.values(SELETORES_PADRAO).forEach((atributo) => {
    document.querySelectorAll(`[${atributo}]`).forEach((el) => {
      ids.add(el.getAttribute(atributo));
    });
  });

  polling.iniciar(Array.from(ids));
  return polling;
}

window.RefeicaoPolling = RefeicaoPolling;
window.iniciarPollingDaPagina = iniciarPollingDaPagina;
