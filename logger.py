import sys
from datetime import datetime
 
class Logger:
 
    def __init__(self, filename):
        self.console = sys.stdout
        self.file = open(filename, 'w+')
 
    def write(self, message):
        self.console.write(message)
        self.file.write(message)
 
    def flush(self):
        self.console.flush()
        self.file.flush()
 
 
now = datetime.now()
dt_start = now.strftime('%Y%m%d%H%M%S')
log_file = f'exp_log_{dt_start}.txt'
path = log_file
sys.stdout = Logger(path)