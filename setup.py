# !/usr/bin/env python

from distutils.core import setup


with open("requirements_dev.txt") as fp:
    dev_requirements = fp.readlines()


setup(
    name='qbackup',
    packages=['qbackup'],
    entry_points={
        'console_scripts': ['qbackup = qbackup.cli:main'],
    },
    install_requires=[], # no external libs ;)
    extras_require={
        'dev': dev_requirements,
    },
    version='0.1.0',
    description='An automated backup service for qubes',
    author='Yan Marques',
    license='MIT',
    author_email='marques_yan@outlook.com',
    url='https://github.com/yanmarques/qbackup',
    keywords=['Qubes Os', 'backup', 'automation', ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development',
    ],
)
