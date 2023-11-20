import smbus
import time
import automationhat

bus = smbus.SMBus(1)
addr = 0x40

# Enable the chip
bus.write_byte_data(addr, 0, 0x20)
time.sleep(0.1)

# Enable Prescale change as noted in the datasheet
bus.write_byte_data(addr, 0, 0x10)
time.sleep(0.1)

# Delay for reset
time.sleep(0.1)

# Changes the Prescale register value for 50 Hz
bus.write_byte_data(addr, 0xfe, 0x79)

# Enable the chip
bus.write_byte_data(addr, 0, 0x20)
time.sleep(0.1)

# Set initial position (0 degrees)
bus.write_word_data(addr, 0x08, 209)
time.sleep(0.5)

try:
    while True:
        # Move to 45 degrees
        bus.write_word_data(addr, 0x08, 312)
        time.sleep(0.5)

        # Move to 0 degrees
        bus.write_word_data(addr, 0x08, 209)
        time.sleep(0.5)

        # Move to 90 degrees
        bus.write_word_data(addr, 0x08, 416)
        time.sleep(0.5)

except KeyboardInterrupt:
    # Handle keyboard interrupt (Ctrl+C)
    pass
finally:
    # Cleanup
    bus.write_word_data(addr, 0x08, 0)
    time.sleep(0.5)
    bus.write_byte_data(addr, 0, 0x00)  # Disable the chip
