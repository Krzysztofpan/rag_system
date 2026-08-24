PROMPT_ATTACK_MESSAGE = "This message was blocked for security reasons."


class PromptAttackError(Exception):
    code = "prompt_attack"

    def __init__(self) -> None:
        super().__init__(PROMPT_ATTACK_MESSAGE)
