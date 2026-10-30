#!/usr/bin/env python3
"""Compatibility entry for the shared application-range inspection helper."""
from application_range_inspect import main

if __name__=='__main__':
    main(default_mangled='_ZN8Presonus4DICE9Dice3Uart13assembleSYSEXEPhi',
         default_role='client',evidence_group='dice-uart-static')
