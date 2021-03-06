import time, datetime
import httplib, urllib

# Thingspeak's configuration
THINGSPEAK_HOST = "api.thingspeak.com:80"
THINGSPEAK_ENDPOINT = "/update"
THINGSPEAK_API_KEY = 'XNW4XHFCW603AM20'
THINGSPEAK_HEADERS = \
    {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}


# Pins being used to select (in binary) a soil humidity sensor
SENSOR_SELECTOR_PINS = [23, 24]

# GPIO pin where the weather sensor is connected
WEATHER_PIN = 25

# Take several readings and average them
SENSOR_READINGS = 9

# Number of times to attempt to send the result to the server before failing
HTTP_TRYS = 4


def initialise():
    """Initialise output pins and devices"""
    if SENSORS:
        global SPI, spidev, GPIO, DHT
        import spidev
        import RPi.GPIO as GPIO
        import Adafruit_DHT as DHT

        SPI = spidev.SpiDev()
        SPI.open(0, 0)
        GPIO.setmode(GPIO.BCM)  # Broadcom pin-numbering scheme
        for pin in SENSOR_SELECTOR_PINS:
            GPIO.setup(pin, GPIO.OUT)  # LED pin set as output


def finalise():
    """Closes resources opened by initialise()"""
    if SENSORS:
        SPI.close()
        GPIO.cleanup()  # cleanup all GPIO and set all to input


def read_adc(channel):
    """read SPI data from MCP3002 chip"""
    # Send start bit(S), sgl/diff(D), odd/sign(C), MSBF(M)
    # Command format: 0000 000S DCM0 0000 0000 0000
    # channel0:       0000 0001 1000 0000 0000 0000
    # channel1:       0000 0001 1100 0000 0000 0000
    # Start bit = 1
    # sgl/diff = 1 (Single Ended Mode); odd/sign = channel (0/1); MSBF = 0
    #
    # 2 + channel shifted 6 to left
    # channel 0: 1000 0000
    # channel 1: 1100 0000
    command = [1, (2 + channel) << 6, 0]
    reply = SPI.xfer2(command)

    # spi.xfer2 returns 24 bit data (3*8 bit)
    # We only need data from bit 13 to 22 (10 bit - MCP3002 resolution)
    # XXXX XXXX XXXX DDDD DDDD DDXX
    # Mask data with 31 (0001 1111) to ensure we have all data from XXXX DDDD and nothing more.
    # 0001 is for signed in next operation.
    data = reply[1] & 31
    # Shift data 6 bits to left.
    # 000D DDDD << 6 = 0DDD DD00 0000
    data = data << 6

    # Now we get the last set of data from reply[2] and discard last two bits
    # DDDD DDXXX >> 2 = 00DD DDDD
    # 0DDD DD00 0000 + 00DD DDDD = 0DDD DDDD DDDD
    data += (reply[2] >> 2)

    return data


def read_a2d(i):
    if SENSORS:
        assert 0 <= i < 4
        GPIO.output(SENSOR_SELECTOR_PINS[0], i % 2)
        GPIO.output(SENSOR_SELECTOR_PINS[1], i / 2)

        # allow time for the sensor to settle
        time.sleep(0.5)
        # Read the sensor several times
        values = []
        for j in range(SENSOR_READINGS):
            values.append(read_adc(0))
            # print("    Sensor {} reading #{}: {}".format(i, j, values[-1]))
            time.sleep(0.1)

        # Now produce the average of the readings, removing the highest and lowest
        # values (attempting to remove outliers)
        sum = 0
        count = 0
        value_min = min(values)
        value_max = max(values)
        for value in values:
            if value == value_min:
                # We found the minimum, so ignore it and 'switch off' the min value
                value_min = None
            elif value == value_max:
                # We found the maximum, so ignore it and 'switch off' the max value
                value_max = None
            else:
                count += 1
                sum += value

        # Return the average
        return sum / count
    else:
        return 500


def post_thingspeak(temperature, humidity, soil1, soil2, soil3, soil4):
    if not SENSORS:
        return

    params = urllib.urlencode({
        'key': THINGSPEAK_API_KEY,
        'field1': temperature,
        'field2': humidity,
        'field3': soil1,
        'field4': soil2,
        'field5': soil3,
        'field6': soil4
    })
    conn = httplib.HTTPConnection(THINGSPEAK_HOST)

    for i in range(HTTP_TRYS):
        try:
            # print ("  About to post to ThingSpeak")
            conn.request("POST", THINGSPEAK_ENDPOINT, params, THINGSPEAK_HEADERS)
            response = conn.getresponse()
            response.read()
            conn.close()
            if response.status == 200:
                return
            else:
                print ("  Post to ThingSpeak failed: Response {}: {}".
                       format(response.status, response.reason))
        except Exception as exception:
            print("connection to ThingSpeak.com failed")
            print(exception)

        if i < (HTTP_TRYS - 1):
            # wait a while and try again
            time.sleep(9 + 10 ^ i)

def read_dht():
    if SENSORS:
        return DHT.read_retry(DHT.DHT11, WEATHER_PIN)
    else:
        return 69.3, 32.1

def read_and_post():
    print("Reading at {}".format(datetime.datetime.now()))
    humidity, temp = read_dht()

    soils = []
    for sensor in range(4):
        value = read_a2d(sensor)
        # print("  Sensor {}: {}".format(sensor, value))
        soils.append(value)

    print("  Temp={:0.1f}*C  Humidity={:0.1f}%  Soils={}".
          format(temp, humidity, soils))
    post_thingspeak(temp, humidity, *soils)


def read_command_line():
    import argparse
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-n', action="store_const", const=False, default=True,
                        help='Flag indicates no sensors are connected to the Python VM')
    args = parser.parse_args()
    global SENSORS
    SENSORS = args.n
    if not SENSORS:
        print("Not using sensors")

if __name__ == "__main__":
    read_command_line()
    initialise()
    try:
        read_and_post()
    finally:
        finalise()

