
from typing import Tuple
from src.controls.exg.ble_server import BLEServer
from src.controls.exg.exg_client import EXGClient
import numpy as np
import pygame

BLE_ENABLED = False

class Controls:
    """Reusable input helper for players utilizing BLE connections."""
    
    def __init__(self) -> None:
        if BLE_ENABLED:
            self.server = BLEServer()
            self.server.start()
            self.client = EXGClient()
            self.P1_RELAX = 0.0
            self.P1_FLEX = 1.0
            self.P2_RELAX = 0.0
            self.P2_FLEX = 1.0
            self.last_p1 = 0.0
            self.last_p2 = 0.0
        
    # def __del__(self) -> None:
    #     self.server.stop()
    #     self.server.join()
        
    @staticmethod
    def get_keyboard_inputs(inputs) -> Tuple[float, float]:
        """Default to moving down unless the Up key is held.

        Player 1 uses W for up. Down (S) is ignored because down is the default.
        Returns:
            -1 when W is held (move up), otherwise +1 (move down by default).
        """
        player1_up = 0.0
        player2_up = 0.0
        
        if inputs[pygame.K_w]:
            player1_up = 1.0
        if inputs[pygame.K_UP]:
            player2_up = 1.0

        return (player1_up, player2_up)

    def get_data(self, threshold=0.5) -> Tuple[float, float]:
        """Get latest BLE channel averages for both players.

        Returns:
            Tuple of two floats representing normalized BLE values for Player 1 and Player 2.
        """
        ch1, ch2 = self.client.get_data()
        if ch1 is None or ch2 is None:
            return self.last_p1, self.last_p2
        avg1 = float(np.mean(ch1))
        avg2 = float(np.mean(ch2))
        
        p1_threshold = (self.P1_FLEX + self.P1_RELAX) * threshold
        p2_threshold = (self.P2_FLEX + self.P2_RELAX) * threshold
        avg1 = 1.0 if avg1 >= p1_threshold else 0.
        avg2 = 1.0 if avg2 >= p2_threshold else 0.
        self.last_p1 = avg1
        self.last_p2 = avg2
        return avg1, avg2

    def calibrate_relax(self) -> None:
        """Calibrate EMG relax levels for both players."""
        # Grab last 3 seconds of data
        ch1, ch2 = self.client.get_data(seconds=3.0)
        if ch1 is not None and len(ch1) > 0:
            self.P1_RELAX = float(np.mean(ch1))
        if ch2 is not None and len(ch2) > 0:
            self.P2_RELAX = float(np.mean(ch2))
            
    def calibrate_flex(self) -> None:
        """Calibrate EMG flex levels for both players."""
        ch1, ch2 = self.client.get_data(seconds=3.0)
        if ch1 is not None and len(ch1) > 0:
            self.P1_FLEX = float(np.mean(ch1))
        if ch2 is not None and len(ch2) > 0:
            self.P2_FLEX = float(np.mean(ch2))

    def get_inputs(self, inputs, threshold=0.5) -> Tuple[float, float]:
        """Get combined BLE and keyboard inputs for both players.

        Args:
            p1_input: Keyboard input state for Player 1.
            p2_input: Keyboard input state for Player 2.
            threshold: Threshold for BLE activation.

        Returns:
            A tuple containing the combined input states for Player 1 and Player 2.
        """
        if BLE_ENABLED:
            ble_inputs = self.get_data(threshold=threshold)
            return ble_inputs
        else:
            keyboard_inputs = self.get_keyboard_inputs(inputs)
            return keyboard_inputs