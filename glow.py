# glow.py
# This program uses PWM output to change the brightness of
# each of the R, G and B color of the RGB LED.
# Colour is chosen randomly and the PWM is modified over a series of steps
# to change from the current colour to the new colour

# Import Python library
import RPi.GPIO as GPIO
import time
import random
import math

DUTY_CYCLE = 100
BLACK = [0.0, 0.0, 0.0]

# Pin Setup:
GPIO.setmode(GPIO.BCM)       # Broadcom pin-numbering scheme

PWMS = []
# Pin Definitions, R=GPIO023, G=GPIO024, B=GPIO025:
for pin in [23, 24, 25]:
    GPIO.setup(pin, GPIO.OUT) # LED pin set as output

    # Initialize PWM on all pins at 100Hz frequency
    pwm = GPIO.PWM(pin, DUTY_CYCLE)
    pwm.start(0)
    PWMS.append(pwm)

print("Press CTRL+C to terminate program")
try:
    last_colour = BLACK

    while 1:
        # Create a new colour (need 3 channels - R, G and B)
        new_colour = [float(random.randint(0, DUTY_CYCLE) * random.randint(0, 1)) for _ in range(3)]

        scale = max(new_colour)
        if not scale:
            # We ignore black - it's boring
            continue

        # Make it maximally bright by scaling to the max duty cycle
        target_colour = [DUTY_CYCLE * channel / scale for channel in new_colour]

        # Find the distance between this colour and the previous to make the
        # shade change appear event no matter what colours we move between
        sum_squares = 0.0
        for a, b in zip(last_colour, target_colour):
            sum_squares += math.pow(a - b, 2)
        steps = int(math.sqrt(sum_squares))

        if not steps:
            # There is no meaningful difference in colour, so pick a new one
            continue

        # Create a list containing how big each step in for each colour channel is
        # We also include the PWM itself to make the call easier later
        interpolate = [(pwm, base, (target - base) / steps)
                       for pwm, base, target in zip(PWMS, last_colour, target_colour)]

        for i in range(steps):
            for pwm, base, gradient in interpolate:
                pwm.ChangeDutyCycle(int(base + i * gradient))
            time.sleep(0.1) #delay 0.1 second
        time.sleep(0.2) # slight pause at the peak colour
        last_colour = target_colour

except KeyboardInterrupt: # Exit program if CTRL+C is pressed
    for pwm in PWMS:
        pwm.stop()
    GPIO.cleanup()        # cleanup all GPIO and set all to input