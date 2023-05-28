from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini")
API_KEY = parser['Keys']['api_key']
SECRET_KEY = parser['Keys']['secret_key']
