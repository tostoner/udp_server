import pi_servo_hat
import time
import sys

def runExample():

	print("\nSparkFun Pi Servo Hat Demo\n")
	mySensor = pi_servo_hat.PiServoHat()

	if mySensor.isConnected() == False:
		print("The Qwiic PCA9685 device isn't connected to the system. Please check your connection", \
			file=sys.stderr)
		return

	mySensor.restart()
  
	# Test Run
	#########################################
	# Moves servo position to 0 degrees (1ms), Channel 0
	mySensor.move_servo_position(0, 0)

	# Pause 1 sec
	time.sleep(1)

	# Moves servo position to 90 degrees (2ms), Channel 0
	mySensor.move_servo_position(0, 90)
