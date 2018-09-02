
""" Script to test CySmart.py file
"""

# standard libraries
import time
# local files
import CySmart

__author__ = 'Kyle Vitautas Lopin'


cy = CySmart.CySmart()
print(cy)

cy.start(cy.Flag_API_RETURN)

count = 0


while True:
    cyd = cy.send_command(cy.Commands['CMD_START_SCAN'], wait_for_payload=False, wait_for_complete=False)

    print('count: ', count)
    print(cyd)
    count += 1
    time.sleep(2)
