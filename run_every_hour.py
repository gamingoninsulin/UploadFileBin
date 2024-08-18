import os
import subprocess
import time
import logging

# Set up logging
logging.basicConfig(filename='console.log', level=logging.INFO, format='%(asctime)s - %(message)s')


def check_and_install_requirements():
    if os.path.isfile('requirements.txt'):
        logging.info('requirements.txt found. Installing requirements...')
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        logging.info('Requirements installed successfully.')
    else:
        logging.warning('requirements.txt not found.')


def run_upload_script():
    if os.path.isfile('upload_to_filebin.py'):
        logging.info('upload_to_filebin.py found. Running script...')
        try:
            subprocess.run(['python', 'upload_to_filebin.py'], check=True)
            logging.info('upload_to_filebin.py ran successfully.')
        except subprocess.CalledProcessError as e:
            logging.error(f'Error running upload_to_filebin.py: {e}')
    else:
        logging.warning('upload_to_filebin.py not found.')


if __name__ == "__main__":
    while True:
        check_and_install_requirements()
        run_upload_script()
        logging.info('Waiting for the next hour...')
        time.sleep(3600)  # Wait for 1 hour (3600 seconds)
