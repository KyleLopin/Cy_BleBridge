
""" Script to test CySmart.py file
"""

# standard libraries
import sys
import time
# local files
import CySmart

__author__ = 'Kyle Vitautas Lopin'


cy = CySmart.CySmart()
print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print(cy)
print("=============================================")
cy.start(cy.Flag_API_RETURN)

count = 0

print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
cyd = cy.send_command(cy.Commands['CMD_START_SCAN'], wait_for_payload=True, wait_for_complete=True)
print("=============================================")
print('count: ', count)
print(cyd)
print(";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;")
cy.send_command(cy.Commands['CMD_STOP_SCAN'])

if isinstance(cyd, dict) and cy.EVT_SCAN_PROGRESS_RESULT in cyd:
    clients = cy.get_scan_data(cyd)
    print('clients: ', clients)
    for client in clients:
        print('client: ', client)
        if b"NU Sensor" in client['name']:

            print(b'name: '+client['name'])
            print('ad', cy.hex_array(client['BD_Address']))
            print('address: ' + str(cy.hex_array(client['BD_Address'])))

            print("=====   START CONNECTION   ============")
            sys.stdout.flush()
            cy.open_connection(client['BD_Address'])
            cir = cy.read_characteristic_value(0x000E)
            print('cir = ', cir)
