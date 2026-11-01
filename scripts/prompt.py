"""El prompt del modelo base: el mismo al entrenar y al medir.

Una sola instrucción corta para los tres formatos. El modelo debe ver por sí
mismo si el texto trae HTML o Markdown y conservarlo.
"""

INSTRUCTION = ('Translate the following text from English into Spanish. '
               'Keep any HTML tags and Markdown formatting exactly as they are. '
               'Reply with the translation only.')


def user_message(text):
    return '%s\n\n%s' % (INSTRUCTION, text)
