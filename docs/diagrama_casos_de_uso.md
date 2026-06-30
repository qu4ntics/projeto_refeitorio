# Diagrama de Casos de Uso

```mermaid
graph TD
    subgraph "Sistema de Reservas"
        uc_reservar("RF02: Reservar Refeição")
        uc_cancelar("RF04: Cancelar Reserva")
        uc_visualizar("RF01: Visualizar Cardápio")
        uc_historico("RF07: Ver Histórico")
        
        uc_gerenciar_refeicao("RF08: Gerenciar Refeições")
        uc_configurar_janela("RF10: Configurar Janela de Reserva")
        uc_desbloquear("RF12: Desbloquear Aluno")
        
        uc_chamada("RF15: Realizar Chamada")
        uc_finalizar_chamada("RF17: Finalizar Chamada")
    end

    aluno(Aluno)
    nutricionista(Nutricionista)
    refeitorio(Refeitório)

    aluno --> uc_visualizar
    aluno --> uc_reservar
    aluno --> uc_cancelar
    aluno --> uc_historico
    
    nutricionista --> uc_gerenciar_refeicao
    nutricionista --> uc_configurar_janela
    nutricionista --> uc_desbloquear
    
    refeitorio --> uc_chamada
    refeitorio --> uc_finalizar_chamada
```