# import time
# import argparse
# import sys
# from Drivers import SnifferCrow
# from Logger import TestLogger
# from Logger import ElasticSearchLogger
from monitoring_connections import *


# from threading import *
# from Queue import *

class ContinuousMonitoring(MonitoringConnections):
    def __init__(self, logger=None):
        super(ContinuousMonitoring, self).__init__(device_sn=0, sniffers_num=5, logger=logger)

    # Thread function
    def config_sniffer_and_read(self, sniffer, config_funcs, channels, queue):
        # print 'In thread', 'Sniffer is open', sniffer.is_open()
        # cps_serials_lst = list()
        for frequency in channels:
            sniffer.configure_sniffer(config_funcs, frequency=frequency,
                                      filter1='OFF', filter2='OFF', filter3='OFF',
                                      data_packets='OFF', error_packets='OFF', random_str=self.random_str)
            cps_serials, thread_exit_mode = sniffer.read_all_transmissions(frequency, timeout=sys.maxint, event=self.event)
            if not thread_exit_mode:
                self.exit_normal = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", type=int, help="delay before the program starts")
    args = parser.parse_args()
    print 'Delay start:', args.verbosity, 'sec.'
    if args.verbosity:
        time.sleep(args.verbosity)

    logger = ElasticSearchLogger(index='beta', dock_type='packet')
    connections = ContinuousMonitoring(logger)

    try:
        connections.monitoring()
    except KeyboardInterrupt, err:
        # print err
        print '\nUser interrupt: CTRL C\n'  # , 'C' * 40
        connections.set_event()
    except SerialException, e:
        print e
        raise
    except Exception, e:
        print e
    finally:
        connections.close_sniffers()
        if not connections.is_exit_normal:
            sys.exit(1)


if __name__ == '__main__':
    main()
