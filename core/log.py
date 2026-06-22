import logging

logging.basicConfig(filename='erros.log', level=logging.ERROR, format='%(levelname)s:%(message)s')

def gravaErro(ex):
    if isinstance(ex, BaseException):
        logging.error("Erro ocorrido: ", exc_info=ex)
    else:
        logging.error(f'Erro ocorrido: {ex}')
