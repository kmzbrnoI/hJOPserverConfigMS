#!/usr/bin/env python3

"""
Propagate status to kolejova deska - set of outputs.

This program is based on example AC "autojc.py".

Usage:
  kolejova_deska.py [options] <block-id> <password>
  kolejova_deska.py --version

Options:
  -s <servername>    Specify hJOPserver address [default: localhost]
  -p <port>          Specify hJOPserver port [default: 5896]
  -l <loglevel>      Specify loglevel (python logging package) [default: info]
  -h --help          Show this screen.
  --version          Show version.
"""

import logging
from docopt import docopt  # type: ignore
from typing import Any, Dict, List

import ac
import ac.blocks
from ac import ACs, AC
from ac import pt as pt
import utils.blocks

JC = Dict[str, Any]
base = 501
b_nav = {130:base+8,131:base+0,132:base+16,133:base+22,134:base+28,136:base+34,137:base+40,138:base+46} # seznam navestidel a XpressNET adres
nav_vjezd = [130,131] 
dn = [1,2,3,4,6,7] # navesti pro vlak dovolujici jizdu - maketa zelena

cesty_LK = {120:553,121:555,122:557,123:559}
cesty_SK = {110:561,111:563,112:565,113:567}

class JCAC(AC):
    """
    This AC is supposed to process entered JCs as soon as all their tracks
    are free.
    """

    def __init__(self, id_: str, password: str) -> None:
        AC.__init__(self, id_, password)
        self.uLK = False
        self.uSK = False

    def on_start(self) -> None:
        logging.info('Start')
        # Clear blocks state cache because blocks could have changed during "DONE" state
        utils.blocks.blocks_state = {}
        self.statestr = ''
        self.statestr_add(f'registrace zmen.')
        for _id in b_nav.keys():
            ac.blocks.register_change(self.on_block_change, _id) # navestidla
        ac.blocks.register_change(self.on_block_change, 105) # ul_LK
        ac.blocks.register_change(self.on_block_change, 111) # ul_SK

        self.statestr_add(f'zjisti aktualni stavy.') # init leds
        for id in b_nav.keys():
            aspect = ac.pt.get(f'/blockState/{id}')['blockState']['signal'] # get aspect from nav
            self.show_nav(id, aspect)
        for cesta_id in cesty_LK.keys():
            id1 = cesty_LK[cesta_id]
            id2 = id1 + 1
            sta1 = True # off
            sta2 = False
            result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': sta1, 'activeInput': False}})
            result = self.pt_put(f'/blockState/{id2}', {'blockState': {'enabled': True, 'activeOutput': sta2, 'activeInput': False}})
        for cesta_id in cesty_SK.keys():
            id1 = cesty_SK[cesta_id]
            id2 = id1 + 1
            sta1 = True # off
            sta2 = False
            result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': sta1, 'activeInput': False}})
            result = self.pt_put(f'/blockState/{id2}', {'blockState': {'enabled': True, 'activeOutput': sta2, 'activeInput': False}})

            
        #self.done() # ukonceni skryptu - zde nepotrebujeme
        logging.info(f'End of start seq.')

    def on_stop(self) -> None:
        if id in b_nav:
            self.show_nav(id,13) # zhasnout makety

    def on_resume(self) -> None:
        self.set_color(0xFFFF00)
        self.on_start()

    def on_block_change(self, block: ac.Block) -> None:
        if self.state == ac.State.RUNNING:
            #52 #su_U
            #logging.info(f'changed {block["name"]}...{block}')
            id = block['id']
            if id in b_nav:
                #aspect = ac.pt.get(f'/blockState/{id}')['blockState']['signal'] # get aspect from changed nav
                aspect = block['blockState']['signal']
                #logging.info(f'nav {block["name"]} aspect = {aspect}')
                self.show_nav(id, aspect)
            if id==105: # usek LK
                newstate = block['blockState']['state'] == "occupied"
                if (newstate != self.uLK): # test na zmenu obsazeni
                    self.uLK = newstate
                    for cesta_id in cesty_LK.keys():
                        cesta_stav = self.pt_get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                        id1 = cesty_LK[cesta_id]
                        id2 = id1 + 1
                        if cesta_stav and newstate:
                            print('LK obsaz v ceste '+str(cesta_id))
                            sta1 = False # on
                            sta2 = True
                        else:
                            print('neni cesta '+str(cesta_id))
                            sta1 = True # off
                            sta2 = False
                        result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': sta1, 'activeInput': False}})
                        result = self.pt_put(f'/blockState/{id2}', {'blockState': {'enabled': True, 'activeOutput': sta2, 'activeInput': False}})
            if id==111: # usek LK
                newstate = block['blockState']['state'] == "occupied"
                if (newstate != self.uSK): # test na zmenu obsazeni
                    self.uSK = newstate
                    for cesta_id in cesty_SK.keys():
                        cesta_stav = self.pt_get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                        id1 = cesty_SK[cesta_id]
                        id2 = id1 + 1
                        if cesta_stav and newstate:
                            print('SK obsaz v ceste '+str(cesta_id))
                            sta1 = False # on
                            sta2 = True
                        else:
                            print('neni cesta '+str(cesta_id))
                            sta1 = True # off
                            sta2 = False
                        result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': sta1, 'activeInput': False}})
                        result = self.pt_put(f'/blockState/{id2}', {'blockState': {'enabled': True, 'activeOutput': sta2, 'activeInput': False}})
                          

                

    def show_nav(self, id: int, state: int) -> None:
        if state<0:
            return
        if (id in nav_vjezd) : # L
            if (state in dn): # jizda vlaku
                aspect_out = [1,0,0,0] # zelena bila cervena kmit
            elif (state == 9): # posun dovolen
                aspect_out = [0,1,0,0] # zelena bila cervena kmit
            elif (state == 8): # PN
                aspect_out = [0,1,0,1] # zelena bila cervena kmit
            elif (state == 13): # zhas
                aspect_out = [0,0,0,0] # zelena bila cervena kmit

            else: # stuj
                aspect_out = [0,0,1,0] # zelena bila cervena kmit
        else:
            if (state in dn): # jizda vlaku
                aspect_out = [1,0,0] # zelena bila kmit
            elif (state == 9): # posun dovolen
                aspect_out = [0,1,0] # zelena bila kmit
            elif (state == 8): # PN
                aspect_out = [0,1,1] # zelena bila kmit
            else: # stuj
                aspect_out = [0,0,0] # zelena bila kmit
        logging.info(f'show nav {id} = {state} - {aspect_out}')
        self.show_nav_zarovky(b_nav[id], aspect_out) # navest na dane vystupy


    def show_nav_zarovky(self, firstid: int, state: list) -> None:
        id_ = firstid
        i = 0
        for sta in state:
            if sta:
              sta1 = False
              sta2 = True
            else:
              sta1 = True
              sta2 = False
            result = self.pt_put(f'/blockState/{id_}', {'blockState': {'enabled': True, 'activeOutput': sta1, 'activeInput': False}})
            id_ += 1
            result = self.pt_put(f'/blockState/{id_}', {'blockState': {'enabled': True, 'activeOutput': sta2, 'activeInput': False}})
            id_ += 1
            i   += 1

if __name__ == '__main__':
    args = docopt(__doc__)

    loglevel = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }.get(args['-l'], logging.INFO)

    logging.basicConfig(level=loglevel)
    ACs[args['<block-id>']] = JCAC(
        args['<block-id>'], args['<password>']
    )
    ac.init(args['-s'], int(args['-p']))
