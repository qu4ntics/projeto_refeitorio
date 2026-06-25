classDiagram
    class Usuario {
        +UUID id
        +String username
        +String email
        +String perfil
        +Boolean bloqueado
        +ForeignKey turma
        +clean()
        +save()
    }

    class Turma {
        +UUID id
        +String nome
        +String turno
        +JSONField dias_contraturno
        +Boolean ativo
    }

    class Refeicao {
        +UUID id
        +Date data
        +String tipo
        +Integer limite_vagas
        +Boolean exige_reserva
        +Boolean chamada_finalizada
        +ManyToMany pratos
        +vagas_disponiveis()
        +get_janela_reserva()
    }

    class Prato {
        +UUID id
        +String nome
        +String descricao
        +String categoria
        +Boolean ativo
    }

    class RefeicaoPrato {
        +ForeignKey refeicao
        +ForeignKey prato
    }

    class Reserva {
        +UUID id
        +ForeignKey aluno
        +ForeignKey refeicao
        +String status
        +DateTime reservado_em
        +DateTime cancelado_em
    }

    class Presenca {
        +UUID id
        +OneToOne reserva
        +ForeignKey confirmado_por
        +Boolean compareceu
        +DateTime confirmado_em
    }

    class Strike {
        +UUID id
        +ForeignKey aluno
        +OneToOne presenca
        +DateTime aplicado_em
        +DateTime expira_em
        +save() (gera bloqueio automático)
    }

    class Notificacao {
        +UUID id
        +ForeignKey usuario
        +String titulo
        +String mensagem
        +Boolean lida
        +DateTime criada_em
    }

    class JanelaReserva {
        +UUID id
        +ForeignKey tipo_refeicao
        +Time horario_abertura
        +Time horario_fechamento
    }

    Usuario "1" --> "0..*" Turma
    Usuario "1" --> "0..*" Reserva
    Refeicao "1" --> "0..*" Reserva
    Refeicao "1" --> "0..*" RefeicaoPrato
    Prato "1" --> "0..*" RefeicaoPrato
    Reserva "1" --> "0..1" Presenca
    Presenca "1" --> "0..1" Strike
    Usuario "1" --> "0..*" Strike
    JanelaReserva "1" --> "1" TipoRefeicao (implícito)