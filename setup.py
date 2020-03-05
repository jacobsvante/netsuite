from setuptools import setup

setup_kwargs = dict(
    name='netsuite',
    version='0.4.1',
    description='Wrapper around Netsuite SuiteTalk Web Services and Restlets',
    packages=['netsuite'],
    include_package_data=True,
    author='Stephen Opal',
    author_email='sno@merit.edu',
    url='https://github.com/merit-netsuite/netsuite',
    license='BSD',
    platforms='any',
    install_requires=[
        'requests-oauthlib',
        'zeep',
    ],
    extras_require={
        'cli': [
            'argh',
            'ipython',
        ],
        'test': {
            'coverage>=4.2',
            'flake8>=3.0.4',
            'mypy>=0.560',
            'pytest>=3.0.3',
            'responses>=0.5.1',
        },
    },
    entry_points={
        'console_scripts': [
            'netsuite = netsuite.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)

if __name__ == '__main__':
    setup(**setup_kwargs)
