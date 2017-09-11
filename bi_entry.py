import datetime
import logging.config

logging.config.fileConfig('config.ini')
log = logging.getLogger('root')





def main():
	# Switch between Reason, Scrap, and Transaction
	while True:  # Core Loop
		dt = datetime.datetime.now()

if __name__ == '__main__':
    main()
