from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='headless',
      version='1.0.0',
      description='A suite of functions and classes useful for headless operation',
      url='https://github.com/gbrucepayne/headless',
      author='G Bruce Payne',
      author_email='gbrucepayne@hotmail.com',
      license='MIT',
      packages=['headless'],
      install_requires=[
            'pyserial',
            'netifaces',
      ],
      zip_safe=False)
