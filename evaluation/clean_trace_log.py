import os
import re
import sys
import subprocess

btd_data_dir = '/home/BTD-data/'


def clean_trace():
    for subdir, dirs, files in os.walk(btd_data_dir):
        for file in files:
            if mat := re.match(r"\d{4,4}(_rev)?\.log", file):
                #print os.path.join(subdir, file)
                filepath = os.path.join(subdir, file)
                print(f"rm {filepath}")
                status, output = subprocess.getstatusoutput(f"rm {filepath}")
                if status:
                    print(output)

if __name__ == '__main__':
    clean_trace()
