from setuptools import setup, find_packages
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schematool'))
from constants import Constants

# from subprocess import Popen, PIPE
# import sys
# def call_git_describe(abbrev=0):
#     try:
#         p = Popen(['git', 'describe', '--abbrev=%d' % abbrev],
#                   stdout=PIPE, stderr=PIPE)
#         p.stderr.close()
#         line = p.stdout.readlines()[0]
#         return line.strip()
#     except:
#         print 'Cannot get version.'
#         sys.exit(1)

setup(
    name='schema-tool',
    author='AppNexus',
    author_email='engineering@appnexus.com',
    url='http://appnexus.com',
    description='A schema tool to manage alters and migrations.',
    version=Constants.VERSION,
    packages=find_packages(),
    entry_points = {
        'console_scripts': ['schema=schematool.schema:main'],
    }
)
