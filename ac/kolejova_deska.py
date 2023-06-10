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


out_state_cache: Dict[int, bool] = {}

B_NAV = {131:502, 130:510, 136:536, 137:542, 138:548, 132:518, 133:524, 134:530, 148:574} # seznam navestidel a maket na kolejove desce
B_PREDV = {131:572, 130:570}
NAV_VJEZD = [130, 131]
NAV_SE = [148]
DN = [SC.VOLNO, SC.VYSTRAHA, SC.OCEK40, SC.VOLNO40, SC.VYSTRAHA40, SC.OCEK4040] # navesti pro vlak dovolujici jizdu - maketa zelena
PT_USERNAME = 'kolejovadeska'
PT_PASSWORD = 'autobusikarus'


class Railway:
    def __init__(self, block: int, outfree: int, outdir1: int, outdir2: int):
        self.block = block
        self.outfree = outfree
        self.outdir1 = outdir1
        self.outdir2 = outdir2

RAILWAYS = {
    50: Railway(50, 582, 584, 580), # Smycka -> Ulanka
    60: Railway(60, 588, 586, 590), # Ulanka -> Harmanec
}

class IK:  # Izolovana kolejnice
    """
    Pokud je pri obsazeni KO `blockid` aktivni alespon jedna z jizdnich cest
    `paths`, dojde k rozsvieni indikace izolovane kolejnice.
    Indikace je zrusena v momente uvolneni kolejoveho obvodu.
    """
    def __init__(self, indid: int, trackid: int, paths: List[int]):
        self.indid = indid
        self.trackid = trackid
        self.paths = paths
        self.output = False


IKs = {
    111: [IK(554, 111, [110, 111, 112, 113])],  # IK1
    108: [IK(556, 108, [102]), IK(558, 108, [100])],  # IK2, IK3
    107: [IK(558, 107, [101])],  # IK4
    106: [IK(562, 106, [131]), IK(564, 106, [130]), IK(566, 106, [132])],  # IK5, IK6, IK7
    105: [IK(568, 105, [120, 121, 122, 123])],  # IK8
}


def pt_put(path: str, req_data: Dict[str, Any]) -> Dict[str, Any]:
    return pt.put(path, req_data, PT_USERNAME, PT_PASSWORD)


def set_output(blockid: int, state: bool) -> None:
    if out_state_cache.get(blockid, None) == state:
        return
    out_state_cache[blockid] = state
    pt_put(f'/blockState/{blockid}', {'blockState': {'activeOutput': state}})


def on_signal_change(block) -> None:
    logging.debug(f'Changed {block["name"]}...{block}')
    id = block['id']
    if id in B_NAV:
        aspect = block['blockState']['signal']
        logging.info(f'nav {block["name"]} aspect = {aspect}')
        show_nav(id, aspect)


def any_path_active(pathids: List[int]) -> bool:
    for pathid in pathids:
        if pt.get(f'/jc/{pathid}/?state=True')['jc']['state']['active']:
            return True
    return False


def on_ik_change(block) -> None:
    if block['id'] not in IKs.keys():
        return

    for ik in IKs[block['id']]:
        if block['blockState']['state'] == 'occupied':
            if any_path_active(ik.paths) and not ik.output:
                set_output(ik.indid, True)
                ik.output = True
        else:
            if ik.output:
                set_output(ik.indid, False)
                ik.output = False


def on_railway_change(block) -> None:
    state = block['blockState']
    railway = RAILWAYS[block['id']]
    set_output(railway.outfree, state['free'])
    set_output(railway.outdir1, state['direction'] == 1)
    set_output(railway.outdir2, state['direction'] == 2)


def on_button_change(block) -> None:
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
    elif id in NAV_SE:
        aspect_out = [1 if aspect == SC.POSUN_ZAJ or aspect == SC.POSUN_NEZAJ else 0]
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
        set_output(id_, sta)
        id_ += 2


def show_zarovka(id: int, sta: bool) -> None:
    logging.debug(f'set id {id} state {sta}')
    set_output(id, sta)


@events.on_connect
def on_connect():
    for signal in B_NAV.keys():
        on_signal_change(pt.get(f'/blocks/{signal}?state=true')['block'])
    blocks.register_change(on_signal_change, *list(B_NAV.keys())) # navestidla
    blocks.register_change(on_button_change, 600) # tl_PrS

    for railway in RAILWAYS.values():
        on_railway_change(pt.get(f'/blocks/{railway.block}?state=true')['block'])
        blocks.register_change(on_railway_change, railway.block)
    for id in B_NAV.keys():
        aspect = pt.get(f'/blockState/{id}')['blockState']['signal'] # get aspect from nav
        show_nav(id, aspect)
    for iks in IKs.values():
        for ik in iks:
            on_ik_change(pt.get(f'/blocks/{ik.trackid}?state=true')['block'])
            blocks.register_change(on_ik_change, ik.trackid)

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
