from glob import glob
from setuptools import find_packages, setup

package_name = 'pug_mcu'

setup(
    name=package_name,
    version='0.2.2',
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
    description='IMU and battery voltage from teh adators board MCU link',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mcu_bridge = pug_mcu.mcu_bridge:main'
        ],
    },
)
