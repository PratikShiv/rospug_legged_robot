from glob import glob
from setuptools import find_packages, setup

package_name = 'pug_monitoring'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Pratik Shiveshwar',
    maintainer_email='pratikshiv@gmail.com',
    description='Jetson Power, temperature and fan monitoring on /diagnostics using jtop',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'jetson_monitor = pug_monitoring.jetson_monitor:main'
        ],
    },
)
