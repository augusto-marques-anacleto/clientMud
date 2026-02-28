import logging

# Configuração básica de log apontando para o arquivo erros.log na raiz
logging.basicConfig(filename='erros.log', level=logging.ERROR, format='%(levelname)s:%(message)s')

def gravaErro(ex):
    """
    Registra uma exceção no arquivo de log.
    """
    if isinstance(ex, BaseException):
        logging.error("Erro ocorrido: ", exc_info=ex)
    else: 
        logging.error(f'Erro ocorrido: {ex}')