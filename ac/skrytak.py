#!/usr/bin/env python3

"""
Automatically process JCs in Skrytak.

This program is based on example AC "autojc.py".

Usage:
  skrytak.py [options] <block-id> <password>
  skrytak.py --version

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
import utils.blocks

JC = Dict[str, Any]

JCs = [
    350, 351,
    360, 361, 362, 363, 364, 365, 366, 367
]


class JCAC(AC):
    """
    This AC is supposed to process entered JCs as soon as all their tracks
    are free.
    """

    def __init__(self, id_: str, password: str, to_process: List[int]) -> None:
        AC.__init__(self, id_, password)
        self.to_process = to_process
        self.jcs_remaining: Dict[int, JC] = {}

    def on_start(self) -> None:
        logging.info('Start')
        self.jcs_remaining = jcs(self.to_process)
        self.statestr = ''

        self.filter_done_jcs()
        self.process_free_jcs()

        for jc in self.jcs_remaining.values():
            ac.blocks.register_change(self.on_block_change, *jc['tracks'])

    def on_resume(self) -> None:
        self.set_color(0xFFFF00)
        self.on_start()

    def filter_done_jcs(self) -> None:
        remaining = {}
        for jc in self.jcs_remaining.values():
            if not jc['state']['active']:
                remaining[jc['id']] = jc
            else:
                self.statestr_add(f'JC {jc["name"]} již postavena, nestavím.')
        self.statestr_send()
        self.jcs_remaining = remaining

    def process_free_jcs(self) -> None:
        self.process_jcs(free_jcs(list(self.jcs_remaining.values())))

        if not self.jcs_remaining:
            self.done()
            logging.info(f'All JCs processed.')

    def process_jcs(self, jcs: List[JC]) -> None:
        for jc in jcs:
            logging.info(f'Processing JC {jc["name"]}...')
            result = self.pt_put(f'/jc/{jc["id"]}/activate', {'ab': True})
            if result['success']:
                self.statestr_add(f'Postavena JC {jc["name"]}.')
                logging.info('ok')
                ac.blocks.unregister_change(self.on_block_change, *jc['tracks'])
            else:
                self.statestr_add(f'Nelze postavit JC {jc["name"]}.')
                self.disp_error(f'Nelze postavit JC {jc["name"]}')
                if 'barriers' in result:
                    logging.error(f'Unable to process JC {jc["name"]}: ' +
                                  str(result['barriers']))
                self.set_color(0xFF0000)

            del self.jcs_remaining[jc['id']]
            self.statestr_send()

    def on_block_change(self, block: ac.Block) -> None:
        self.process_free_jcs()


def jcs(ids: List[int]) -> Dict[int, JC]:
    return {jc_id: ac.pt.get(f'/jc/{jc_id}?state=true')['jc'] for jc_id in ids}


def free_jcs(jcs: List[JC]) -> List[JC]:
    result = []
    for jc in jcs:
        free = all([utils.blocks.state(track_id)['state'] == 'free'
                    for track_id in jc['tracks']])
        if free:
            result.append(jc)

    return result


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
        args['<block-id>'], args['<password>'], JCs
    )
    ac.init(args['-s'], int(args['-p']))
