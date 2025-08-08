import time
import os
from config import UNITREE_GO1_ENABLED, AGILEX_SCOUT_MINI_ENABLED
import can

UNITREE_HIGHLEVEL = 0xee
UNITREE_LOWLEVEL = 0xff

# sys.path.append(os.path.expanduser('~/unitree_legged_sdk/lib/python/arm64'))
# import robot_interface as go1_sdk

class RobotController:
    def __init__(self):
        pass

    def start(self):
        raise NotImplementedError

    def send_velocity(self, vx_robot, vy_robot=0.0):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

class UnitreeGo1Controller(RobotController):
    def __init__(self):
        super().__init__()
        self.udp = go1_sdk.UDP(UNITREE_HIGHLEVEL, 8080, "192.168.123.161", 8082)
        self.cmd = go1_sdk.HighCmd()
        self.state = go1_sdk.HighState()
        self.udp.InitCmdData(self.cmd)

    def start(self):
        print("Initializing Unitree Go1...")

    def send_velocity(self, vx_robot, vy_robot=0.0):
        self.udp.Recv()
        self.udp.GetRecv(self.state)
        self.cmd.mode = 2
        self.cmd.gaitType = 1
        self.cmd.velocity = [vx_robot, 0]
        self.cmd.yawSpeed = 0.0
        self.cmd.bodyHeight = 0
        self.udp.SetSend(self.cmd)
        self.udp.Send()
        print(f"Sending velocity {vx_robot} to Unitree Go1")

    def stop(self):
        self.udp.Recv()
        self.udp.GetRecv(self.state)
        self.cmd.mode = 0  # Set to idle mode
        self.cmd.gaitType = 0
        self.cmd.velocity = [0, 0]
        self.udp.SetSend(self.cmd)
        self.udp.Send()
        print("Stopping Unitree Go1...")


class AgileXScoutMiniController(RobotController):
    def __init__(self):
        super().__init__()
        self.bus = None

    def start(self):
        print("Initializing AgileX Scout MINI...")
        password = "kat354"
        os.system(f"echo {password} | sudo -S ip link set can0 up type can bitrate 500000")
        time.sleep(1)
        self.bus = can.interface.Bus(channel='can0', bustype='socketcan')
        self._send_can_message(0x421, bytes([0x01]))
        time.sleep(1)

    def _send_can_message(self, can_id, data):
        msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
        try:
            self.bus.send(msg)
            print(f"Sent CAN message: ID={hex(can_id)}, Data={data.hex()}")
        except can.CanError:
            print("CAN message send failed")

    def send_velocity(self, vx_robot, vy_robot=0.0):
        linear_speed = int(vx_robot * 1000)
        linear_speed_bytes = linear_speed.to_bytes(2, byteorder='big', signed=True)
        command_data = linear_speed_bytes + b'\x00\x00\x00\x00\x00\x00'
        self._send_can_message(0x111, command_data)
        print(f"Sending velocity {vx_robot} to AgileX Scout MINI")

    def stop(self):
        self.send_velocity(0.0)
        print("Stopping AgileX Scout MINI...")

def create_robot_controller():
    if UNITREE_GO1_ENABLED:
        return UnitreeGo1Controller()
    elif AGILEX_SCOUT_MINI_ENABLED:
        return AgileXScoutMiniController()
    else:
        return None