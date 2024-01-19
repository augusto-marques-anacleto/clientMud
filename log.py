import logging
logging.basicConfig(filename='erros.log', level=logging.ERROR, format='%(levelname)s:%(message)s')

def gravaErro(ex):
	"""
	Registra uma exceção no arquivo de log.
	"""
	if isinstance(ex, BaseException):
		logging.error("erro ocorrido: ", exc_info=ex)
	else: 
		logging.error(f'erro ocorrido: {ex}')
