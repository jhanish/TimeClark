from setuptools import setup
# https://twine.readthedocs.io/en/latest/
# python setup.py sdist bdist_wheel
# python -m twine upload dist/*

def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='micropython-tinydb',
      version='4.4.1',
      description='TinyDB',
      long_description=readme(),
      url='https://tinydb.readthedocs.io/en/latest/',
      author='Ahmad Sadiq',
      author_email='sadiq.a.ahmad@gmail.com',
      license='MIT',
      packages=['tinydb'],
      scripts=[],
      install_requires=[
      ],
      zip_safe=False)