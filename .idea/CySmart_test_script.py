
""" Script to test CySmart.py file
"""


import CySmart

__author__ = 'Kyle Vitautas Lopin'


cy = CySmart.CySmart()
print(cy)

cy.start(cy.Flag_API_RETURN, com_port='\\.\COM8')

cyd = cy.send_command(cy.Commands['CMD_START_SCAN'], wait_for_payload=True, wait_for_complete=False)

print('check')
print(cyd)