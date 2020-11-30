from setuptools import setup
from pathlib import Path

setup(
    name='yamap',
    description='YAML to Python data mapper and a schema definition DSL and validator.',
    long_description=(Path(__file__).parent / 'README.md').read_text(),
    long_description_content_type='text/markdown',
    version='1.0',
    author='Florian Wagner',
    author_email='florian@wagner-flo.net',
    url='https://github.com/wagnerflo/yamap',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Text Processing',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    license_files=['LICENSE'],
    python_requires='>=3.8',
    install_requires=['ruamel.yaml'],
    packages=['yamap'],
)
