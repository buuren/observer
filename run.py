import logging
import platform
from utils.help_functions import json_reader, bin_verify


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s] <%(levelname)s> - %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %I:%M:%S'
    )

    bin_data = json_reader('config/centos7.json')

    bin_verify(bin_data)