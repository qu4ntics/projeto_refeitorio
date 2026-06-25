graph TD
    subgraph Sistema
        UC1[Reservar Refeição]
        UC2[Cancelar Reserva]
        UC3[Visualizar Cardápio]
        UC4[Gerenciar Refeições]
        UC5[Configurar Janela de Reserva]
        UC6[Realizar Chamada]
        UC7[Aplicar Strike]
        UC8[Desbloquear Aluno]
        UC9[Gerenciar Pratos]
        UC10[Visualizar Lista de Reservados]
    end

    Aluno --> UC1
    Aluno --> UC2
    Aluno --> UC3

    Nutricionista --> UC4
    Nutricionista --> UC5
    Nutricionista --> UC8
    Nutricionista --> UC9
    Nutricionista --> UC10

    Refeitorio --> UC6
    Refeitorio --> UC7
    Refeitorio --> UC10

    UC7 -.->|inclui| BloqueioAuto[Bloqueio Automático]