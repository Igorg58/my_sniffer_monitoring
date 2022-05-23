# import time
# import argparse
# import sys
import random
import string
from check_zone_connection import *
# from Drivers import SnifferCrow
# from Logger import TestLogger
# from Logger import ElasticSearchLogger
from threading import *
from Queue import *


class MonitoringConnections(ZoneConnection):
    def __init__(self, device_sn, sniffers_num, logger=None):
        super(MonitoringConnections, self).__init__(device_sn, sniffers_num, logger),
        self.random_str = ''.join(random.choice(string.lowercase+string.digits) for _ in xrange(5))

    def monitoring(self):
        msg = 'Monitoring is starting...'
        print msg
        # self.logger.add_row({'msg': msg})

        cps_all_serials = []
        config_funcs = [
            'switch_filter1',
            'switch_filter2',
            'switch_filter3',
            'set_channel',
            'set_data_packets',
            'set_error_packets',
            'set_random',
        ]

        channels_list = SNIFFERS_NUM2CHANNELS[self.sniffers_num]
        queue = Queue()
        for idx in xrange(self.sniffers_num):
            thrd = Thread(target=self.config_sniffer_and_read,
                          args=(self.sniffers[idx], config_funcs, channels_list[idx], queue))
            thrd.daemon = True
            self.threads.append(thrd)
            thrd.start()

        for thrd in self.threads:
            while thrd.isAlive():
                thrd.join(1)

        for sniffer in self.sniffers:
            sniffer.stop()

        # print 'Queue size: {}'.format(queue.qsize())
        while not queue.empty():
            serials_from_one_sniffer = queue.get()
            print 'Serial numbers from one sniffer', serials_from_one_sniffer
            cps_all_serials += serials_from_one_sniffer

        return cps_all_serials

    # Thread function
    def config_sniffer_and_read(self, sniffer, config_funcs, channels, queue):
        # print 'In thread', 'Sniffer is open', sniffer.is_open()
        cps_serials_lst = list()
        for frequency in channels:
            sniffer.configure_sniffer(config_funcs, frequency=frequency,
                                      filter1='OFF', filter2='OFF', filter3='OFF',
                                      data_packets='OFF', error_packets='OFF', random_str=self.random_str)
            cps_serials, thread_exit_mode = sniffer.read_all_transmissions(frequency)
            if len(cps_serials):
                cps_serials_lst += list(cps_serials)
            if not thread_exit_mode:
                self.exit_normal = False
        if len(cps_serials_lst):
            queue.put(cps_serials_lst, block=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sn', help='Device SN', type=int)
    parser.add_argument('num', help='Sniffers number', type=int)
    # print parser
    args = parser.parse_args()
    # print 'Args:', args
    device_sn = args.sn if 0 != args.sn else None
    devices_sn = SnifferCrow.read_config_data()['devices_sn']
    device_name = str(devices_sn.get(str(device_sn), 'Unknown'))

    # logger = TestLogger('Sniffer')
    logger = ElasticSearchLogger(index='sniffer', dock_type='packet')
    connections = MonitoringConnections(args.sn, args.num, logger)
    cps_sn = connections.monitoring()
    if device_sn is not None:
        if len(cps_sn):
            d_cps = {}
            for cp_sn in cps_sn:
                cp_name = str(devices_sn.get(str(cp_sn), 'Unknown'))
                d_cps.update({cp_sn: cp_name})
            msg = 'Device {} is connected to CP {}'.format({device_sn: device_name}, d_cps)
        else:
            msg = 'Device {} does not connected to any CP'.format({device_sn: device_name})
    else:
        msg = ''

    connections.close_sniffers()

    if msg:
        print msg
        # logger.add_row({'msg': msg})

    if not connections.is_exit_normal:
        sys.exit(1)

if __name__ == '__main__':
    main()
