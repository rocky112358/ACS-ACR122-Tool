from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.ATR import ATR
import sys

def print_help():
    print("Usage: python nfctool.py <command>")
    print("List of available commands:")
    print("    help                Show this help page")
    print("    mute                Disable beep sound when card is tagged")
    print("    unmute              Enable beep sound when card is tagged")
    print("    getuid              Print UID of the tagged card")
    print("    info                Print card type and available protocols")
    print("    loadkey <key>       Load key <key> (6-byte hex string) for authentication")
    print("    read <sector>       Read sector <sector> with loaded key")
    print("    write <sector> <data>   Write data to sector <sector>")
    print("    firmver             Print the firmware version of the reader")
    sys.exit()

def get_card_reader():
    r = readers()
    if len(r) < 1:
        print("Error: No readers available!")
        sys.exit()
    return r[0]

def send_command(connection, command):
    data, sw1, sw2 = connection.transmit(command)
    return data, sw1, sw2

def write_sector(connection, sector, data):
    # Check if the data length is appropriate (16 bytes per block)
    if len(data) != 16 * 4:
        print("Error: Data length must be 16 bytes per block")
        return

    # Authenticate with key A
    command_auth = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, sector * 4, 0x60, 0x00]
    _, sw1, sw2 = send_command(connection, command_auth)
    if (sw1, sw2) != (0x90, 0x00):
        # Authentication failed
        print("Error: Authentication failed for sector", sector)
        return

    # Write data to each block in the sector
    for block in range(sector * 4, sector * 4 + 4):
        command_write = [0xFF, 0xD6, 0x00, block, 16] + data[block * 16:block * 16 + 16]
        _, sw1, sw2 = send_command(connection, command_write)
        if (sw1, sw2) != (0x90, 0x00):
            # Writing failed
            print("Error: Writing failed for block", block)
            return

    print("Data written successfully to sector", sector)

def main():
    if len(sys.argv) < 2:
        print_help()

    command = sys.argv[1]
    reader = get_card_reader()
    connection = reader.createConnection()
    connection.connect()

    if command == "help":
        print_help()

    if command == "getuid":
        data, _, _ = send_command(connection, [0xFF, 0xCA, 0x00, 0x00, 0x00])
        print("UID:", toHexString(data))

    elif command == "info":
        atr = ATR(connection.getATR())
        print("Card Info:")
        print("    Historical Bytes:", toHexString(atr.getHistoricalBytes()))
        print("    T0 Supported:", atr.isT0Supported())
        print("    T1 Supported:", atr.isT1Supported())
        print("    T15 Supported:", atr.isT15Supported())

    elif command == "loadkey":
        if len(sys.argv) < 3:
            print("Usage: python nfctool.py loadkey <key>")
            sys.exit()
        key = [int(sys.argv[2][i:i+2], 16) for i in range(0, len(sys.argv[2]), 2)]
        command = [0xFF, 0x82, 0x00, 0x00, 0x06] + key
        _, sw1, sw2 = send_command(connection, command)
        if (sw1, sw2) == (0x90, 0x00):
            print("Status: Key loaded successfully to key #0.")
        else:
            print("Status: Failed to load key.")

    elif command == "read":
        if len(sys.argv) < 3:
            print("Usage: python nfctool.py read <sector>")
            sys.exit()
        sector = int(sys.argv[2])
        command = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, sector * 4, 0x60, 0x00]
        data, sw1, sw2 = send_command(connection, command)
        if (sw1, sw2) == (0x90, 0x00):
            print("Sector", sector, "Data:", toHexString(data))
        else:
            print("Failed to read sector", sector)

    elif command == "write":
        if len(sys.argv) < 4:
            print("Usage: python nfctool.py write <sector> <data>")
            sys.exit()
        sector = int(sys.argv[2])
        data = bytearray.fromhex(sys.argv[3])
        write_sector(connection, sector, data)

    elif command == "firmver":
        data, _, _ = send_command(connection, [0xFF, 0x00, 0x48, 0x00, 0x00])
        print("Firmware Version:", ''.join(chr(i) for i in data))

    else:
        print("Error: Unknown command. Use 'help' for command list.")

if __name__ == "__main__":
    main()
