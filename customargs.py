# Taken verbatim from https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
import argparse
import sys

class ArgumentParser(argparse.ArgumentParser):    
    def exit(self, status=0, message=None):
        raise IOError(message)
        pass
