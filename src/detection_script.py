"""
    detection_script.py
    Marcus Abate | 16.30
    12/7/18

    Detection drone takes off, flies vertically until it finds the orange
    target, makes a note of the current position and then flies away and lands
    safely away from the origin.
    Saves location of target to file.
"""

from Drone import Drone
from PositionController import MamboPositionController
from KalmanFilter import MamboKalman
from ColorSegmentation import cd_color_segmentation
import csv

filename = 'shoot_here.csv'

class DetectionDrone(Drone):
    """
    Handles the detection drone's flight and callbacks.
    """

    def __init__(self, mambo_addr):
        super().__init__(True, mambo_addr, True, True) # WiFi enabled drone
        self.controller = MamboPositionController()
        self.kalmanfilter = MamboKalman([0,0,0],[0,0,0])
        self.current_vels = []
        self.current_state = []
        self.desired_state = []
        self.eps = 0.08
        self.max_alt = 3 # maximum altitude (m)
        self.max_dist = 3 # maximum distance from target accepted (m)
        self.start_measure = False
        self.target_acquired = False
        self.firing_position = []

        self.bb = [0, 0, 0, 0]
        self.bb_threshold = 62648

    def sensor_cb(self, args):
        """
        Throw sensor readings into state estimator and then save the
        current state. Then update the controller with this current state.
        """
        if self.start_measure:
            self.current_measurement = [self.mambo.sensors.sensors_dict['DronePosition_posx']/100,
                                        self.mambo.sensors.sensors_dict['DronePosition_posy']/100,
                                        self.mambo.sensors.sensors_dict['DronePosition_posz']/-100]
            self.current_vels = [self.mambo.sensors.speed_x,
                                 self.mambo.sensors.speed_y,
                                 self.mambo.sensors.speed_z]
            self.current_state = self.kalmanfilter.get_state_estimate(self.current_measurement,
                                                                        self.current_vels)
            self.controller.set_current_state(self.current_state)

    def vision_cb(self, args):
        """
        Check each vision frame for the correct bounding box size of orange.
        """
        img = self.mamboVision.get_latest_valid_picture()

        if img is not None and not self.target_acquired:
            [((x1, y1), (x2, y2)), ln_color] = cd_color_segmentation(img)
            self.bb = [x1, y1, x2, y2]

            bb_size = (self.bb[2] - self.bb[0])*(self.bb[3] - self.bb[1])
            # print('bb_size:',bb_size)
            if bb_size >= self.bb_threshold:
                print('orange detected')
                self.target_acquired = True
                self.firing_position = self.current_state
                file = open(filename, 'w')
                with file:
                    writer = csv.writer(file)
                    writer.writerows([self.firing_position])
        else:
            pass

    def go_to_xyz(self, desired_state):
        """
        Use position controller to execute flight command to go to a desired
        xyz position from origin (defined at takeoff).

        Returns True if position reached within tolerance self.eps
        Returns False if maximum altitude is reached/exceeded or distance gets
            too large.
        """
        self.desired_state = desired_state
        self.controller.set_desired_state(self.desired_state)
        # print('flying to position ', self.desired_state)

        dist = ((self.current_state[0] - self.desired_state[0])**2 +
                (self.current_state[1] - self.desired_state[1])**2 +
                (self.current_state[2] - self.desired_state[2])**2 )**0.5

        while dist > self.eps:
            cmd = self.controller.calculate_cmd_input()
            # print('current state:',self.current_state)
            # print('desired state:', self.desired_state)
            # print('cmd:          ',cmd)

            self.mambo.fly_direct(roll=cmd[1],
                                    pitch=cmd[0],
                                    yaw=cmd[2],
                                    vertical_movement=cmd[3],
                                    duration=None)
            dist = ((self.current_state[0] - self.desired_state[0])**2 +
                    (self.current_state[1] - self.desired_state[1])**2 +
                    (self.current_state[2] - self.desired_state[2])**2 )**0.5

            if self.current_state[2] >= self.max_alt or dist >= self.max_dist:
                return False
        return True

    def controlled_fly_up(self):
        """
        Fly up using the go_to_xyz() command, which makes use of the
        PositionController class.
        """
        while not self.target_acquired and self.current_state[2] <= self.max_alt:
            desired_state = [0, 0, self.desired_state[2] + 0.1] # jump 10cm
            self.go_to_xyz(desired_state)
        if self.target_acquired:
            return True
        return False

    def dumb_fly_up(self):
        """
        Use direct power command to fly up without control or estimation.
        This works for the detection drone because it can still grab its
        current state during sensor_cb when vision_cb detects the target.
        """
        while not self.target_acquired and self.current_state[2] <= self.max_alt:
            self.mambo.fly_direct(roll=0, pitch=0, yaw=0, vertical_movement=30, duration=None)
        if self.target_acquired:
            return True
        return False

    def fly_away(self):
        """
        Drone flies back and left facing the target for a safe landing.
        """
        self.mambo.fly_direct(roll=30, pitch=-30, yaw=0, vertical_movement=0, duration=3)

    def flight_func(self, mamboVision, args):
        """
        Takeoff, slowly climb altitude until the vision_cb triggers detection
        of the target. Save that position, fly away a bit in the xy plane and
        land safely.

        Can choose between doing the trajectory using PositonController and
        KalmanFilter, or just as a dumb "fly up" trajectory.
        """
        print('taking off')
        self.mambo.safe_takeoff(5)

        if self.mambo.sensors.flying_state != 'emergency':

            print('sensor calib:')
            while self.mambo.sensors.speed_ts == 0:
                continue
            self.start_measure = True

            print('getting first state')
            while self.current_state == []:
                continue

            # set first desired state:
            self.desired_state = self.current_state

            # dumb fly option:
            while not self.target_acquired:
                jump = self.dumb_fly_up()
                if not jump:
                    print('failure')
                    break
                elif jump:
                    break

            self.mambo.smart_sleep(2)

        self.fly_away()
        print('landing')
        self.mambo.safe_land(5)
        self.mamboVision.close_video()
        self.mambo.disconnect()

    def execute(self):
        super().execute()

        print('done closing')

        return self.firing_position

detec_addr = "e0:14:ad:f6:3d:fc"

if __name__ == "__main__":
    detecDrone = DetectionDrone(detec_addr)
    firing_pos = detecDrone.execute()
