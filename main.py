"""
# NamePlate.py
# Controller coordinating Employees, LCDDisplay, Buttons, LightStrip, and PassiveBuzzer
# Author: jessiqveen-dotcom
"""

import time
from Log import *
from Employee import Employee, Administrator


class NamePlate:
    """
    Controller class for the NamePlate system.
    Manages navigation, status updating, LCD rendering, LED color indications, and audio tones.
    """

    # Tone frequencies in Hz
    TONE_NAV = 523     # C5 for previous / next navigation
    TONE_AVAIL = 659   # E5 for changing availability

    def __init__(self, employees=None, display=None, buttons=None, lightstrip=None, buzzer=None):
        Log.i("NamePlate: initializing controller")

        # 1. Employee list management
        if employees is None or len(employees) == 0:
            self.employees = [
                Employee("Alice Smith", "305-348-0001", "Professor", "asmith@uni.edu", "Available"),
                Employee("Bob Jones", "305-348-0002", "Lecturer", "bjones@uni.edu", "Away"),
                Administrator("Carol White", "305-348-0003", "Dean", "cwhite@uni.edu", "Exec Committee", "Busy"),
            ]
        else:
            self.employees = list(employees)

        self._currentEmployeeIndex = 0

        # 2. LCD Display handle (I2C on GP0=SDA, GP1=SCL by default)
        if display is None:
            from Displays import LCDDisplay
            self.display = LCDDisplay(sda=0, scl=1)
        else:
            self.display = display

        # 3. LightStrip handle (GP2, 8 LEDs by default)
        if lightstrip is None:
            from LightStrip import LightStrip
            self.lightstrip = LightStrip(pin=2, name="StatusStrip", numleds=8, brightness=0.5)
        else:
            self.lightstrip = lightstrip

        # 4. PassiveBuzzer handle (GP16 by default)
        if buzzer is None:
            from Buzzer import PassiveBuzzer
            self.buzzer = PassiveBuzzer(pin=16, name="NamePlateBuzzer")
        else:
            self.buzzer = buzzer

        # 5. Buttons list [prev, next, avail]
        if buttons is None:
            from Button import Button
            self.buttons = [
                Button(18, "Previous", handler=self),
                Button(19, "Next", handler=self),
                Button(20, "Availability", handler=self),
            ]
        else:
            self.buttons = list(buttons)
            for btn in self.buttons:
                if hasattr(btn, "setHandler"):
                    btn.setHandler(self)

        # Initial render
        self.updateDisplay()

    def currentEmployee(self) -> Employee:
        """Returns the currently active Employee or Administrator instance."""
        return self.employees[self._currentEmployeeIndex]

    def nextEmployee(self) -> Employee:
        """Advances to the next employee in the list and updates the displays."""
        self._currentEmployeeIndex = (self._currentEmployeeIndex + 1) % len(self.employees)
        emp = self.currentEmployee()
        Log.i(f"NamePlate: nextEmployee -> {emp.name} (index {self._currentEmployeeIndex})")
        if self.buzzer:
            self.buzzer.beep(self.TONE_NAV, 60)
        self.updateDisplay()
        return emp

    def previousEmployee(self) -> Employee:
        """Moves to the previous employee in the list and updates the displays."""
        self._currentEmployeeIndex = (self._currentEmployeeIndex - 1) % len(self.employees)
        emp = self.currentEmployee()
        Log.i(f"NamePlate: previousEmployee -> {emp.name} (index {self._currentEmployeeIndex})")
        if self.buzzer:
            self.buzzer.beep(self.TONE_NAV, 60)
        self.updateDisplay()
        return emp

    def changeAvailability(self) -> str:
        """Cycles availability for the active person and refreshes the displays."""
        emp = self.currentEmployee()
        new_status = emp.cycleAvailability()
        Log.i(f"NamePlate: changeAvailability -> {emp.name} is now {new_status}")
        if self.buzzer:
            self.buzzer.beep(self.TONE_AVAIL, 80)
        self.updateDisplay()
        return new_status

    def updateDisplay(self) -> None:
        """
        Updates the LCD Display text and illuminates the LightStrip
        with the appropriate status color:
          - 'Available' -> Green
          - 'Away'      -> Yellow
          - 'Busy'      -> Red
        """
        emp = self.currentEmployee()
        display_str = emp.getDisplay()
        lines = display_str.split("\n")
        line0 = lines[0] if len(lines) > 0 else ""
        line1 = lines[1] if len(lines) > 1 else ""

        # Update LCD
        if self.display:
            if hasattr(self.display, "_working"):
                self.display._working = False
            self.display.clear()
            self.display.showText(line0[:16], 0, 0)
            self.display.showText(line1[:16], 1, 0)

        # Update NeoPixel LightStrip
        if self.lightstrip:
            try:
                from Lights import GREEN, YELLOW, RED
            except ImportError:
                GREEN = (0, 255, 0)
                YELLOW = (255, 200, 0)
                RED = (255, 0, 0)

            avail = emp.getAvailability().lower()
            if avail == "available":
                self.lightstrip.setColor(GREEN)
            elif avail == "away":
                self.lightstrip.setColor(YELLOW)
            else:
                self.lightstrip.setColor(RED)

    def buttonPressed(self, name: str) -> None:
        """Callback triggered by Button interrupt handler."""
        Log.i(f"NamePlate: buttonPressed('{name}')")
        norm = str(name).strip().lower()
        if "next" in norm or norm in ("button2", "btn2", "right"):
            self.nextEmployee()
        elif "prev" in norm or norm in ("button1", "btn1", "left"):
            self.previousEmployee()
        elif "avail" in norm or norm in ("button3", "btn3"):
            self.changeAvailability()

    def buttonReleased(self, name: str) -> None:
        """Callback triggered when a button is released."""
        Log.i(f"NamePlate: buttonReleased('{name}')")
        if self.buzzer:
            self.buzzer.stop()