from setuptools import setup

extras_require = {
    "rest_api": [
        "authlib",
        # NOTE: authlib doesn't work with httpx 0.12.1 So we're locking the httpx
        #       version to one that is compatible. See:
        #       https://github.com/lepture/authlib/issues/210#issuecomment-612311003
        # TODO: Remove version lock once fixed upstream.
        "httpx==0.12.0",
    ],
    "cli": ["ipython"],
    "test": ["pytest>=3.0.3", "coverage>=4.2",],
    "lint": ["pre-commit>=1.21.0", "flake8>=3.0.4", "black>=19.10b0", "isort>=4.3.21",],
}
extras_require["all"] = [
    dep
    for name, lst in extras_require.items()
    if name not in ("test", "lint")
    for dep in lst
]

setup_kwargs = dict(
    name="netsuite",
    version="0.5.3",
    description="Wrapper around Netsuite SuiteTalk SOAP/REST Web Services and Restlets",
    packages=["netsuite"],
    include_package_data=True,
    author="Jacob Magnusson",
    author_email="m@jacobian.se",
    url="https://github.com/jmagnusson/netsuite",
    license="BSD",
    platforms="any",
    install_requires=["requests-oauthlib", "zeep", "orjson",],
    extras_require=extras_require,
    entry_points={"console_scripts": ["netsuite = netsuite.__main__:main",],},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)

if __name__ == "__main__":
    setup(**setup_kwargs)
