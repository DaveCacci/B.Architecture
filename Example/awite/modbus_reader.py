from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import logging
import struct

# IP address and port of the Modbus server (Awite)
host = '192.168.0.101'  # IP address of the Awite device
port = 502  # Port for Modbus TCP (according to the manual)

# Logging configuration to see process details
logging.basicConfig(level=logging.DEBUG)

def read_modbus_registers(start_register, num_registers, keys, word_types, byte_order='big'):
    # Connect to the Modbus server
    client = ModbusClient(host, port)
    try:
        # Connect to the server
        connection = client.connect()
        if connection:
            logging.info(f"Connected to the Modbus server at {host}:{port}")

            # Read the specified input registers
            result = client.read_input_registers(start_register, num_registers, unit=1)

            if result.isError():
                logging.error(f"Error reading registers: {result}")
                return None
            else:
                registers = result.registers
                register_dict = dict(zip(keys,registers))
                logging.info(f"Registers read: {register_dict}")

                # Create a dictionary with the keys and register values
                register_dict = {}
                i = 0
                for key, word_type in zip(keys, word_types):
                    if word_type == 'single':
                        register_dict[key] = registers[i]
                        i += 1
                    elif word_type == 'double':
                        high = registers[i]
                        low = registers[i + 1]
                        if byte_order == 'big':
                            combined = (high << 16) | low
                        else:
                            combined = (low << 16) | high
                        register_dict[key] = struct.unpack('!f' if byte_order == 'big' else '<f', struct.pack('!I' if byte_order == 'big' else '<I', combined))[0]
                        i += 2
                return register_dict
        else:
            logging.error(f"Could not connect to the Modbus server at {host}:{port}")
            return None
    except Exception as e:
        logging.error(f"Connection error: {e}")
        return None
    finally:
        # Close the connection
        client.close()
        logging.info("Connection closed")

# ------------------------------------------------------------- #

def read_modbus_registers_basic(start_register, num_registers, keys):
    # Connect to the Modbus server
    client = ModbusClient(host, port)
    try:
        # Connect to the server
        connection = client.connect()
        if connection:
            logging.info(f"Connected to the Modbus server at {host}:{port}")

            # Read the specified input registers
            result = client.read_input_registers(start_register, num_registers, unit=1)

            if result.isError():
                logging.error(f"Error reading registers: {result}")
                return None
            else:
                registers = result.registers
                register_dict = dict(zip(keys,registers))
                logging.info(f"Registers read: {register_dict}")

                # Create a dictionary with the keys and register values
                register_dict = {keys[i]: registers[i] for i in range(num_registers)}
                return register_dict
        else:
            logging.error(f"Could not connect to the Modbus server at {host}:{port}")
            return None
    except Exception as e:
        logging.error(f"Connection error: {e}")
        return None
    finally:
        # Close the connection
        client.close()
        logging.info("Connection closed")
