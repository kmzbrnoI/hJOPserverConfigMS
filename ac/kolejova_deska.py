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


class SC: # SignalCode
    STUJ = 0
    VOLNO = 1
    VYSTRAHA = 2
    OCEK40 = 3
    VOLNO40 = 4
    VSE = 5
    VYSTRAHA40 = 6
    OCEK4040 = 7
    PRIVOL = 8
    POSUN_ZAJ = 9
    POSUN_NEZAJ = 10
    OPAK_VOLNO = 11
    OPAK_VYSTRAHA = 12
    ZHASNUTO = 13
    OPAK_OCEK40 = 14
    OPAK_VYSTRAHA_40 = 15
    OPAK_40OCEK40 = 16


base = 501
b_nav = {131:501, 130:509, 136:535, 137:541, 138:547, 132:517, 133:523, 134:529} # seznam navestidel a maket na kolejove desce
b_predv = {131:571, 130:569}
NAV_VJEZD = [130, 131]
DN = [SC.VOLNO, SC.VYSTRAHA, SC.OCEK40, SC.VOLNO40, SC.VYSTRAHA40, SC.OCEK4040] # navesti pro vlak dovolujici jizdu - maketa zelena

cesty_SK = {120:553,121:555,122:557,123:559}
cesty_LK = {110:561,111:563,112:565,113:567}

class KDAC(AC):
    """
    Komunikace s kolejovou deskou
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

        ac.blocks.register_change(self.on_block_change, 600) # tl_PrS

        self.statestr_add(f'zjisti aktualni stavy.') # init leds
        for id in b_nav.keys():
            aspect = ac.pt.get(f'/blockState/{id}')['blockState']['signal'] # get aspect from nav
            self.show_nav(id, aspect)
        for cesta_id in cesty_LK.keys():
            id1 = cesty_LK[cesta_id]
            result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': False, 'activeInput': False}})
        for cesta_id in cesty_SK.keys():
            id1 = cesty_SK[cesta_id]
            result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': False, 'activeInput': False}})

        #self.done() # ukonceni skryptu - zde nepotrebujeme
        logging.info(f'End of start seq.')

    def on_stop(self) -> None:
        if id in b_nav:
            self.show_nav(id, 13) # zhasnout makety

    def on_resume(self) -> None:
        self.set_color(0xFFFF00)
        self.on_start()

    def on_block_change(self, block: ac.Block) -> None:
        if self.state == ac.State.RUNNING:
            #52 #su_U
            logging.debug(f'changed {block["name"]}...{block}')
            id = block['id']
            if id in b_nav:
                aspect = block['blockState']['signal']
                logging.debug(f'nav {block["name"]} aspect = {aspect}')
                self.show_nav(id, aspect)
            if id == 105: # usek LK
                newstate = block['blockState']['state'] == "occupied"
                if (newstate != self.uLK): # test na zmenu obsazeni
                    self.uLK = newstate
                    for cesta_id in cesty_LK.keys():
                        cesta_stav = self.pt_get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                        id1 = cesty_LK[cesta_id]
                        result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': cesta_stav and newstate, 'activeInput': False}})
            if id == 111: # usek SK
                newstate = block['blockState']['state'] == "occupied"
                if (newstate != self.uSK): # test na zmenu obsazeni
                    self.uSK = newstate
                    for cesta_id in cesty_SK.keys():
                        cesta_stav = self.pt_get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                        id1 = cesty_SK[cesta_id]
                        result = self.pt_put(f'/blockState/{id1}', {'blockState': {'enabled': True, 'activeOutput': cesta_stav and newstate, 'activeInput': False}})
            if id == 600: # tl PrS
                logging.debug('PrS')
                # self.pt_put(f'/blockState/130', {'blockState': {'signal': 8 if block['blockState']['activeInput'] else 0}})

    def show_nav(self, id: int, aspect: int) -> None:
        if aspect < 0:
            return
        if id in NAV_VJEZD : # L / S
            pr_out = 0
            if aspect in DN: # jizda vlaku
                aspect_out = [1,0,0,0] # zelena bila cervena kmit
                pr_out = 1
            elif aspect == SC.POSUN_ZAJ or aspect == SC.POSUN_NEZAJ:
                aspect_out = [0,1,0,0] # zelena bila cervena kmit
            elif aspect == SC.PRIVOL:
                aspect_out = [0,1,1,1] # zelena bila cervena kmit
            elif aspect == SC.ZHASNUTO:
                aspect_out = [0,0,0,0] # zelena bila cervena kmit
            else: # stuj
                aspect_out = [0,0,1,0] # zelena bila cervena kmit
            idd = b_predv[id]
            logging.debug(f'predv id {idd} state {pr_out}')
            self.show_zarovka(idd,pr_out)
        else:
            if aspect in DN: # jizda vlaku
                aspect_out = [1,0,0] # zelena bila kmit
            elif aspect == SC.POSUN_ZAJ or aspect == SC.POSUN_NEZAJ:
                aspect_out = [0,1,0] # zelena bila kmit
            elif aspect == SC.PRIVOL:
                aspect_out = [0,1,1] # zelena bila kmit
            else: # stuj
                aspect_out = [0,0,0] # zelena bila kmit
        logging.debug(f'show nav {id} = {aspect} - {aspect_out}')
        self.show_nav_zarovky(b_nav[id], aspect_out) # navest na dane vystupy

    def show_nav_zarovky(self, firstid: int, states: List[int]) -> None:
        id_ = firstid
        for sta in states:
            self.pt_put(f'/blockState/{id_}', {'blockState': {'activeOutput': sta}})
            id_ += 2

    def show_zarovka(self, id: int, sta: bool) -> None:
        logging.debug(f'set id {id} state {sta}')
        result = self.pt_put(f'/blockState/{id}', {'blockState': {'activeOutput': sta}})


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
    ACs[args['<block-id>']] = KDAC(
        args['<block-id>'], args['<password>']
    )
    ac.init(args['-s'], int(args['-p']))
