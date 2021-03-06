#!/usr/bin/env python3

import os
from time import time
import yaml

import Adafruit_BNO055.BNO055

from derp.component import Component

class BNO055(Component):

    def __init__(self, config, state):
        super(BNO055, self).__init__(config, state)

        self.bno = None
        self.ready = self.__connect()
        if not self.ready:
            return
        
        self.sensors = (('calibration', ('system', 'gyro', 'accel', 'mag'),
                         self.bno.get_calibration_status),
                        ('quaternion', 'wxyz', self.bno.read_quaternion),
                        ('euler', 'hrp', self.bno.read_euler),
                        ('gravity', 'xyz', self.bno.read_gravity),
                        ('magneto', 'xyz', self.bno.read_magnetometer),
                        ('gyro', 'xyz', self.bno.read_gyroscope),
                        ('accel', 'xyz', self.bno.read_linear_acceleration))

    def __is_calibrated(self):
        try:
            return self.bno.get_calibration_status() == (3, 3, 3, 3)
        except:
            self.ready = False
            return False

    def __connect(self):
        if self.bno:
            del self.bno
            self.bno = None
        try:
            self.bno = Adafruit_BNO055.BNO055.BNO055(busnum=self.config['busnum'])
            self.ready = self.bno.begin()

            # Remap Axes to match camera's principle axes
            self.bno.set_axis_remap(x = Adafruit_BNO055.BNO055.AXIS_REMAP_Y,
                                    y = Adafruit_BNO055.BNO055.AXIS_REMAP_Z,
                                    z = Adafruit_BNO055.BNO055.AXIS_REMAP_X,
                                    x_sign = Adafruit_BNO055.BNO055.AXIS_REMAP_POSITIVE,
                                    y_sign = Adafruit_BNO055.BNO055.AXIS_REMAP_NEGATIVE,
                                    z_sign = Adafruit_BNO055.BNO055.AXIS_REMAP_NEGATIVE)

            self.calibration_saved = False
            if os.path.exists(self.config['calibration_path']):
                print("Existing:", self.bno.get_calibration(), self.bno.get_calibration_status())
                with open(self.config['calibration_path']) as f:
                    calibration = yaml.load(f)
                self.bno.set_calibration(calibration)
                print("Loaded:", self.bno.get_calibration(), self.bno.get_calibration_status())
                self.calibration_saved = self.__is_calibrated()

            print("BNO055 status: %s self_test: %s error: %s" % self.bno.get_system_status() )
            print("BNO055 sw: %s bl: %s accel: %s mag: %s gyro: %s" % self.bno.get_revision())
            return True
        except Exception as e:
            print("BNO055 connect", e)
            return False
        
    def sense(self):
        """ Reinitialize IMU if it's failed to get data at any point. 
        Otherwise get data from the IMU to update state variable.
        """
        if not self.ready:
            self.ready = self.__connect()
        for name, subnames, func in self.sensors:
            try:
                values = func()
            except:
                self.ready = False
                values = [None for _ in subnames]
            self.state.update_multipart(name, subnames, values)
        try:
            self.state['temp'] = self.bno.read_temp()
        except:
            self.read = False
            self.state['temp'] = None

        # Decide if this data is good
        name, subnames = self.sensors[0][:2]
        total = 0
        for subname in subnames:
            field_name = "%s_%s" % (name, subname)
            total += 0 if self.state[field_name] is None else self.state[field_name]
        self.state['warn'] = (1 - total / 12) / 4

        # Store 22 bytes of calibration data to a pre-set file, as according to the config.
        if self.calibration_saved or not self.__is_calibrated():
            return True
        try:
            calibration = self.bno.get_calibration()
        except:
            self.ready = False
            return False
        with open(self.config['calibration_path'], 'w') as yaml_file:
            yaml.dump(calibration, yaml_file, default_flow_style=False)
        self.calibration_saved = True
        return True
        

