sequenceDiagram
    actor Aluno
    Aluno->>+ViewReservar: POST /reservas/criar/<id>/
    ViewReservar->>ViewReservar: verifica login e perfil
    ViewReservar->>+Refeicao: select_for_update() e valida vagas
    Refeicao-->>-ViewReservar: objeto Refeicao
    ViewReservar->>ViewReservar: valida bloqueio, janela, vagas, duplicidade
    ViewReservar->>+Reserva: create(aluno, refeicao, status='ativa')
    Reserva->>+Banco: INSERT tbReserva
    Banco-->>-Reserva: ok
    Reserva-->>-ViewReservar: nova reserva
    ViewReservar->>ViewReservar: verifica se vagas esgotaram e notifica nutricionistas
    ViewReservar-->>-Aluno: redirect para homepage com mensagem de sucesso