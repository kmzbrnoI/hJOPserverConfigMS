#!/usr/bin/env python3

"""
Propagate status to kolejova deska - set of outputs.

This program is based on example AC "autojc.py".

Usage:
  kolejova_deska.py [options]
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

import ac.blocks as blocks
import ac.panel_client as panel_client
import ac.events as events
from ac import pt as pt


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


B_NAV = {131:502, 130:510, 136:536, 137:542, 138:548, 132:516, 133:522, 134:528} # seznam navestidel a maket na kolejove desce
B_PREDV = {131:572, 130:570}
NAV_VJEZD = [130, 131]
DN = [SC.VOLNO, SC.VYSTRAHA, SC.OCEK40, SC.VOLNO40, SC.VYSTRAHA40, SC.OCEK4040] # navesti pro vlak dovolujici jizdu - maketa zelena
PT_USERNAME = 'kolejovadeska'
PT_PASSWORD = 'autobusikarus'

CESTY_SK = {120:554, 121:556, 122:558, 123:560}
CESTY_LK = {110:562, 111:564, 112:566, 113:568}

uSK = False
uLK = False

def pt_put(path: str, req_data: Dict[str, Any]) -> Dict[str, Any]:
    return pt.put(path, req_data, PT_USERNAME, PT_PASSWORD)


def on_block_change(block) -> None:
    global uSK, uLK

    logging.debug(f'changed {block["name"]}...{block}')
    id = block['id']
    if id in B_NAV:
        aspect = block['blockState']['signal']
        logging.debug(f'nav {block["name"]} aspect = {aspect}')
        show_nav(id, aspect)

    if id == 105: # usek LK
        newstate = block['blockState']['state'] == "occupied"
        if newstate != uLK: # test na zmenu obsazeni
            uLK = newstate
            for cesta_id in CESTY_LK.keys():
                cesta_stav = pt.get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                pt_put(f'/blockState/{CESTY_LK[cesta_id]}', {'blockState': {'activeOutput': cesta_stav and newstate}})

    if id == 111: # usek SK
        newstate = block['blockState']['state'] == "occupied"
        if newstate != uSK: # test na zmenu obsazeni
            uSK = newstate
            for cesta_id in CESTY_SK.keys():
                cesta_stav = pt.get(f'/jc/{cesta_id}/?state=True')['jc']['state']['active']
                pt_put(f'/blockState/{CESTY_SK[cesta_id]}', {'blockState': {'activeOutput': cesta_stav and newstate}})

    if id == 600: # tl PrS
        logging.debug('PrS')
        # pt_put(f'/blockState/130', {'blockState': {'signal': 8 if block['blockState']['activeInput'] else 0}})


def show_nav(id: int, aspect: int) -> None:
    if aspect < 0:
        return
    if id in NAV_VJEZD : # L / S
        if aspect in DN: # jizda vlaku
            aspect_out = [1,0,0,0] # zelena bila cervena kmit
        elif aspect == SC.POSUN_ZAJ or aspect == SC.POSUN_NEZAJ:
            aspect_out = [0,1,0,0] # zelena bila cervena kmit
        elif aspect == SC.PRIVOL:
            aspect_out = [0,1,1,1] # zelena bila cervena kmit
        elif aspect == SC.ZHASNUTO:
            aspect_out = [0,0,0,0] # zelena bila cervena kmit
        else: # stuj
            aspect_out = [0,0,1,0] # zelena bila cervena kmit

        show_zarovka(B_PREDV[id], aspect in DN)
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
    show_nav_zarovky(B_NAV[id], aspect_out) # navest na dane vystupy


def show_nav_zarovky(firstid: int, states: List[int]) -> None:
    id_ = firstid
    for sta in states:
        pt_put(f'/blockState/{id_}', {'blockState': {'activeOutput': sta}})
        id_ += 2


def show_zarovka(id: int, sta: bool) -> None:
    logging.debug(f'set id {id} state {sta}')
    pt_put(f'/blockState/{id}', {'blockState': {'activeOutput': sta}})


@events.on_connect
def on_connect():
    blocks.register_change(on_block_change, *list(B_NAV.keys())) # navestidla
    blocks.register_change(on_block_change, 105) # ul_LK
    blocks.register_change(on_block_change, 111) # ul_SK
    blocks.register_change(on_block_change, 600) # tl_PrS

    for id in B_NAV.keys():
        aspect = pt.get(f'/blockState/{id}')['blockState']['signal'] # get aspect from nav
        show_nav(id, aspect)
    for blkid in CESTY_LK.values():
        pt_put(f'/blockState/{blkid}', {'blockState': {'activeOutput': False}})
    for blkid in CESTY_SK.values():
        pt_put(f'/blockState/{blkid}', {'blockState': {'activeOutput': False}})

    logging.info(f'End of start seq.')


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
    panel_client.init(args['-s'], int(args['-p']))
