# Seconds waiting, and the message shown from then on. The wording stays generic because it
# depends only on time, so it must not claim the agent is doing something specific.
WAITING_MESSAGES = (
    (0, "Preparando sua resposta..."),
    (5, "Ainda estou verificando as informações..."),
    (15, "Organizando os detalhes da resposta..."),
    (30, "Está levando um pouco mais que o normal, só mais um instante..."),
    (45, "Ainda estou trabalhando nisso, obrigado pela paciência..."),
)


def waiting_message(elapsed_seconds: float) -> str:
    message = WAITING_MESSAGES[0][1]
    for start, candidate in WAITING_MESSAGES:
        if elapsed_seconds >= start:
            message = candidate
    return message
