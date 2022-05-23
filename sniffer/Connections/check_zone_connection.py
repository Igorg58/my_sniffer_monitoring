import time
import argparse
import sys
from Drivers import SnifferCrow
from Logger import TestLogger
from Logger import ElasticSearchLogger
from serial.serialutil import SerialException
from threading import *
from Queue import *

COM_PORTS = [
    '/dev/ttyUSB0',
    '/dev/ttyUSB1',
    '/dev/ttyUSB2',
    '/dev/ttyUSB3',
    '/dev/ttyUSB4',
]

SNIFFERS_NUM2CHANNELS = {
    1: [(868350, 869070, 868130, 868850, 868480)],
    2: [(868350, 869070, 868130), (868850, 868480)],
    3: [(868350, 869070), (868130,  868850), (868480,)],
    4: [(868350, 869070,), (868130,), (868850,), (868480,)],
    5: [(868350,), (869070,), (868130,), (868850,), (868480,)],
}


class ZoneConnection(object):
    def __init__(self, device_sn, sniffers_num, logger=None):
        if logger is None:
            self.logger = TestLogger('Sniffer')
        else:
            self.logger = logger

        self.sniffers_num = sniffers_num
        self.sniffers = []
        self.threads = []
        self.event = Event()
        self.exit_normal = True
        for idx in xrange(sniffers_num):
            sn = SnifferCrow(COM_PORTS[idx], device_sn, self.logger)
            # self.sniffers.append(sn)
            try:
                sn.start()
                msg = 'Sniffer COM-Port {} is open'.format(COM_PORTS[idx])
                self.sniffers.append(sn)
            except SerialException:
                msg = 'Open COM-Port {} is failed'.format(COM_PORTS[idx])
                raise
            finally:
                print msg
                # self.logger.add_row({'msg': msg})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if type(self.logger) == TestLogger:
            self.logger.remove_handler()

    @property
    def is_exit_normal(self):
        return self.exit_normal

    def set_event(self):
        self.event.set()

    def monitoring(self):
        msg = 'Monitoring is starting...'
        print msg
        # self.logger.debug(msg)
        self.logger.add_row({'msg': msg})

        cps_all_serials = []
        config_funcs = [
            'set_filter1_cam2all',
            'set_filter2_all2cam',
            'set_filter3_cam2broadcast',
            'set_channel',
            'set_data_packets',
            'set_error_packets',
        ]

        channels_list = SNIFFERS_NUM2CHANNELS[self.sniffers_num]
        queue = Queue()
        for idx in xrange(self.sniffers_num):
            thrd = Thread(target=self.config_sniffer_and_read,
                          args=(self.sniffers[idx], config_funcs, channels_list[idx], queue))
            self.threads.append(thrd)
            thrd.start()

        for thrd in self.threads:
            thrd.join()

        print 'Queue size: {}'.format(queue.qsize())
        while not queue.empty():
            serials_from_one_sniffer = queue.get()
            print 'Serial numbers from one sniffer', serials_from_one_sniffer
            cps_all_serials += serials_from_one_sniffer

        return cps_all_serials

    def config_sniffer_and_read(self, sniffer, config_funcs, channels, queue):
        # print 'In thread', 'Sniffer is open', sniffer.is_open()
        cps_serials_lst = list()
        for frequency in channels:
            sniffer.configure_sniffer(config_funcs, frequency=frequency,
                                      data_packets='OFF', error_packets='OFF')
            break_on_found = True
            # break_on_found = False
            cps_serials = sniffer.read_content(frequency, self.event, break_on_found=break_on_found)
            if len(cps_serials):
                cps_serials_lst += list(cps_serials)
                self.event.set()
                if break_on_found:
                    break
        if len(cps_serials_lst):
            queue.put(cps_serials_lst, block=True)

    def close_sniffers(self):
        for sniffer in self.sniffers:
            sniffer.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sn', help='Device SN', type=int)
    parser.add_argument('num', help='Sniffers number', type=int)
    # print parser
    args = parser.parse_args()
    # print 'Args:', args
    device_sn = args.sn
    devices_sn = SnifferCrow.read_config_data()['devices_sn']
    device_name = str(devices_sn.get(str(device_sn), 'Unknown'))

    # logger = TestLogger('Sniffer')
    logger = ElasticSearchLogger(index='sniffer', dock_type='packet')
    connection = ZoneConnection(args.sn, args.num, logger)
    cps_sn = connection.monitoring()
    if len(cps_sn):
        d_cps = {}
        for cp_sn in cps_sn:
            cp_name = str(devices_sn.get(str(cp_sn), 'Unknown'))
            d_cps.update({cp_sn: cp_name})
        msg = 'Device {} is connected to CP {}'.format({device_sn: device_name}, d_cps)
    else:
        msg = 'Device {} does not connected to any CP'.format({device_sn: device_name})

    connection.close_sniffers()

    print msg
    # logger.debug(msg)
    logger.add_row({'msg': msg})


if __name__ == '__main__':
    main()
