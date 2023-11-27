import RvrServer
# Initialize the PiServoHat object
servo = pi_servo_hat.PiServoHat()
servo.restart()
server = RvrServer.RvrServer("10.25.46.172", 12395)
server.run()
