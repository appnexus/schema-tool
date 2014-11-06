from setuptools import setup, find_packages

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
    version='0.2.18',
    packages=find_packages(),
    entry_points = {
        'console_scripts': ['schema=schematool.schema:main'],
    }
)
