import serial
import time
import os
import json
import socket
import redis
from serial.serialutil import SerialException
from sniffer_parser import SnifferParser


def config_mode(func):
    def wrap(self, *argc, **kwargs):
        self.enter_config()
        res = func(self, *argc, **kwargs)
        self.exit_config()
        return res
    return wrap


class SnifferCrow(object):
    # ##################################################################################
    # ###                       Init / close region                                  ###
    # ##################################################################################

    def __init__(self, port, serial_number, logger):
        """Constructor: port is a COM port address in string """
        self.port = port
        self.logger = logger
        self.sSerial = serial.Serial()
        self.serial_number = self.convert_sn2hex_rev(serial_number)
        self.config = SnifferCrow.read_config_data()
        self.random_str = ''
        # self.host_name = ''  # socket.gethostname() + ''.join(random.choice(string.lowercase) for _ in xrange(5))

    def start(self):
        """Init and open serial port.
           return: True or False"""
        self.sSerial.port = self.port
        self.sSerial.baudrate = 115200
        self.sSerial.timeout = 5

        try:
            self.sSerial.open()
        except SerialException, err:
            self.sSerial.close()
            raise
        return self.sSerial.isOpen()

    def stop(self):
        """Close the port"""
        if not self.is_open():
            return

        self.sSerial.close()
        msg = 'Sniffer COM-Port {} is closed'.format(self.port)
        print msg
        # self.logger.add_row({'msg': msg})

    def is_open(self):
        return self.sSerial.isOpen()

    @staticmethod
    def reverse_sn_hex(sn):
        """
        Prepares serial number for set sn command in reverse order by byte
        :param sn: serial number hex string
        :type sn: str
        :return: serial number in reverse order
        :rtype: str
        """
        lst = [sn[i:i+2] for i in range(0, len(sn), 2)]
        rev_lst = lst[::-1]
        return "".join(rev_lst)

    @staticmethod
    def read_config_data():
        working_dir = os.getcwd()
        config_file = os.path.join(working_dir, 'config.json')
        with open(config_file) as data_file:
            return json.load(data_file)

    @staticmethod
    def convert_sn2hex_rev(sn_dec):
        """
        Convert and set decimal SN to HEX upper representation without leading '0x'
        :param sn_dec: decimal serial number; int
        """
        if sn_dec is not None:
            sn_hex = '{:06x}'.format(sn_dec).upper()
            sn_hex_rev = SnifferCrow.reverse_sn_hex(sn_hex)
        else:
            sn_hex_rev = None

        return sn_hex_rev

    @staticmethod
    def convert_hex_rev2sn(sn_hex_rev):
        """
        Convert and set decimal SN to HEX upper representation without leading '0x'
        :param sn_hex_rev: decimal serial number; int
        """
        if sn_hex_rev is not None:
            sn_hex = SnifferCrow.reverse_sn_hex(sn_hex_rev)
            sn_dec = int(sn_hex, 16)
        else:
            sn_dec = None

        return sn_dec

    def _command_write_read(self, cmd):
        print "cmd: '{}'".format(cmd)
        self.sSerial.write(cmd)
        time.sleep(0.1)
        res = self.sSerial.read(1)
        res += self.sSerial.read(self.sSerial.inWaiting())
        print "\nresponse '{}': {}".format(cmd, res)

    # ##################################################################################
    # ###                           Public functions                                 ###
    # ##################################################################################

    def enter_config(self):
        # self.sSerial.write(':CONFIG;')
        # time.sleep(0.01)
        # print 'Entering config...'
        self._command_write_read(':CONFIG;')

    def exit_config(self):
        # self.sSerial.write(':EXIT;')
        # time.sleep(0.5)
        # print 'Exiting config...'
        self._command_write_read(':EXIT;')

    def set_filter1_cam2all(self, *args, **kwargs):
        # msg = 'Set FILTER 1'
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':FILTER:1:ON:{}:000000:00;'.format(self.serial_number))
        # time.sleep(0.1)
        cmd = ':FILTER:1:ON:{}:000000:00;'.format(self.serial_number)
        self._command_write_read(cmd)

    def set_filter2_all2cam(self, *args, **kwargs):
        # msg = 'Set FILTER 2'
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':FILTER:2:ON:000000:{}:00;'.format(self.serial_number))
        # time.sleep(0.1)
        cmd = ':FILTER:2:ON:000000:{}:00;'.format(self.serial_number)
        self._command_write_read(cmd)

    def set_filter3_cam2broadcast(self, *args, **kwargs):
        # msg = 'Set FILTER 3'
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':FILTER:3:ON:{}:FFFFFF:00;'.format(self.serial_number))
        # time.sleep(0.1)
        cmd = ':FILTER:3:ON:{}:FFFFFF:00;'.format(self.serial_number)
        self._command_write_read(cmd)

    def switch_filter1(self, *args, **kwargs):
        mode = kwargs['filter1']
        # msg = 'FILTER 1 {}'.format(mode)
        # print msg
        # self.logger.add_row({'msg': msg})

        # self.sSerial.write(':FILTER:1:{};'.format(mode))
        # time.sleep(0.25)
        cmd = ':FILTER:1:{};'.format(mode)
        self._command_write_read(cmd)

        # self.sSerial.write(':FILTER:1:?;')
        # time.sleep(0.1)
        # f = self.sSerial.read(1)
        # f += self.sSerial.read(self.sSerial.inWaiting())
        # print 'Filter 1 status', f

    def switch_filter2(self, *args, **kwargs):
        mode = kwargs['filter2']
        # msg = 'FILTER 2 {}'.format(mode)
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':FILTER:2:{};'.format(mode))
        # time.sleep(0.25)
        cmd = ':FILTER:2:{};'.format(mode)
        self._command_write_read(cmd)


        # self.sSerial.write(':FILTER:2:?;')
        # f = self.sSerial.read(1)
        # f += self.sSerial.read(self.sSerial.inWaiting())
        # print 'Filter 2 status', f

    def switch_filter3(self, *args, **kwargs):
        mode = kwargs['filter3']
        # msg = 'FILTER 3 {}'.format(mode)
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':FILTER:3:{};'.format(mode))
        # time.sleep(0.25)
        cmd = ':FILTER:3:{};'.format(mode)
        self._command_write_read(cmd)


        # self.sSerial.write(':FILTER:3:?;')
        # f = self.sSerial.read(1)
        # f += self.sSerial.read(self.sSerial.inWaiting())
        # print 'Filter 3 status', f

    def set_channel(self, *args, **kwargs):
        frequency = kwargs['frequency']
        # msg = 'Set CHANNEL {}'.format(frequency)
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':CHANNEL:{};'.format(frequency))
        # time.sleep(0.25)
        cmd = ':CHANNEL:{};'.format(frequency)
        self._command_write_read(cmd)

    def set_data_packets(self, *args, **kwargs):
        mode = kwargs['data_packets']
        # msg = 'Set DATA PACKETS {}'.format(mode)
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':DATAPACKETS:{};'.format(mode))
        # time.sleep(0.1)
        cmd = ':DATAPACKETS:{};'.format(mode)
        self._command_write_read(cmd)

    def set_error_packets(self, *args, **kwargs):
        mode = kwargs['error_packets']
        # msg = 'Set ERROR PACKETS {}'.format(mode)
        # print msg
        # self.logger.add_row({'msg': msg})
        # self.sSerial.write(':ERRORPACKETS:{};'.format(mode))
        # time.sleep(0.1)
        cmd = ':ERRORPACKETS:{};'.format(mode)
        self._command_write_read(cmd)

    def set_random(self, *args, **kwargs):
        self.random_str = kwargs['random_str']

    @config_mode
    def configure_sniffer(self, config_funcs, *args, **kwargs):
        for f_name in config_funcs:
            f = getattr(self, f_name)
            f(*args, **kwargs)

    def clear_content(self):
        time.sleep(1)
        buf = self.sSerial.read()
        msg = 'Cleared: {}'.format(buf)
        print msg
        # self.logger.add_row({'msg': msg})

    def read_content(self, frequency, event, break_on_found=True):
        cp_serials = set()
        sn_dec = self.convert_hex_rev2sn(self.serial_number)
        time_start = time.time()
        timeout = self.config.get('timeout_read', 60)
        devices_sn = self.config['devices_sn']
        while not event.is_set() and time.time() - time_start < timeout:
            time.sleep(timeout / 100.0)
            lines = self.sSerial.readlines()
            msg = '{} '.format(frequency) + str(lines) if lines else '{} Empty -> PRESS-RELEASE TAMPER'.format(frequency)
            print msg
            # self.logger.add_row({'msg': msg})
            d = {'frequency': frequency}
            device_name = str(devices_sn.get(str(sn_dec), 'Unknown'))
            for line in lines:
                lst = line.split()
                if len(lst) < 5:
                    continue
                if lst[2] == self.serial_number:
                    cp_hex = lst[3]
                    cp_sn = self.convert_hex_rev2sn(cp_hex)
                    cp_name = str(devices_sn.get(str(cp_sn), 'Unknown'))
                    d.update({'from': device_name if 'Unknown' not in device_name else sn_dec,
                              'to': cp_name if 'Unknown' not in cp_name else cp_sn,
                              'msg': line
                              })
                    print '{}'.format(d)
                    self.logger.add_row(d)
                    if 'FFFFFF' in lst[3]:  # Broadcast
                        # d.update({'from': device_name if 'Unknown' not in device_name else sn_dec, 'To': 'FFFFFF'})
                        # print '{}'.format(d)
                        pass
                    else:
                        cp_serials.add(cp_sn)
                        if break_on_found:
                            break
                elif lst[3] == self.serial_number:
                    cp_hex = lst[2]
                    cp_sn = self.convert_hex_rev2sn(cp_hex)
                    cp_serials.add(cp_sn)
                    cp_name = str(devices_sn.get(str(cp_sn), 'Unknown'))
                    d.update({'from': cp_name if 'Unknown' not in cp_name else cp_sn,
                              'to': device_name if 'Unknown' not in device_name else sn_dec,
                              'msg': line
                              }),

                    print '{}'.format(d)
                    self.logger.add_row(d)
                    if break_on_found:
                        break
            if break_on_found and len(cp_serials):
                break

        return cp_serials

    def read_all_transmissions(self, frequency, timeout=None, event=None):
        exit_normal = True
        cp_serials = set()
        time_start = time.time()
        if timeout is None:
            timeout = self.config.get('timeout_read', 60)
        # is_event_set = event.is_set() if event is not None else False
        # sampling = min(timeout / 10.0, 0.5)
        r = redis.StrictRedis(host='sniffer0', port=6379, db=0)
        parser = SnifferParser(r)
        host_name = socket.gethostname()  # + '_' + self.random_str - next usage, if need distinguish between a lot of hosts
        while time.time() - time_start < timeout:
            if event and event.is_set():
                break
            try:
                # time.sleep(sampling)
                # lines = self.sSerial.readlines()
                d = {'frequency': frequency, 'sniffer_host': host_name}
                # for line in lines:
                # one_byte = self.sSerial.read(1)  # this will block until one more char or Serial timeout
                # line = one_byte + self.sSerial.readline()
                line = self.sSerial.readline()
                connections = []
                lst = line.split()
                if len(lst) < 5:
                    continue
                else:
                    msg = '<{}> '.format(frequency) + line.strip()
                    print msg
                    connections.append(line)

                # Parse list of connections
                for connection_str in connections:
                    lst = connection_str.split()
                    sz = int(lst[0], 16)
                    ctl = int(lst[1], 16)
                    src_sn = self.convert_hex_rev2sn(lst[2])
                    # src_name = str(devices_sn.get(str(src_sn), 'Unknown'))
                    src_name = r.hget(src_sn, 'alias')
                    dest_sn = self.convert_hex_rev2sn(lst[3])
                    # dest_name = str(devices_sn.get(str(dest_sn), 'Unknown'))
                    dest_name = r.hget(dest_sn, 'alias')
                    # d.update({'from': src_name if 'Unknown' not in src_name else src_sn,
                    #           'to': dest_name if 'Unknown' not in dest_name else dest_sn,
                    #           'msg': connection_str
                    #           })
                    cmd_code = str(self.config['commands_code'].get(str(lst[4]), 'Unknown'))
                    payload = lst[5] if len(lst) > 6 else ''
                    msg = ' '.join(lst[:-1])
                    ctl_parse = parser.control_parser(ctl)
                    payload_parse = parser.payload_parse(src_sn, dest_sn, cmd_code, payload)
                    d.update({
                        'size': sz,
                        'ctl': ctl_parse,
                        # 'control parse': ctl_parse,
                        'from': src_name if src_name is not None else str(src_sn),
                        'to': dest_name if dest_name is not None else str(dest_sn),
                        'command': cmd_code,
                        'payload': payload_parse,
                        'msg': msg,
                        'timestamp_offset': int(lst[-1][1:-1])
                    })
                    print '{}'.format(d), '\n'
                    self.logger.add_row(d)

                    if lst[2] == self.serial_number and 'FFFFFF' not in lst[3]:
                        cp_serials.add(dest_sn)
                    elif lst[3] == self.serial_number:
                        cp_serials.add(src_sn)

            except SerialException, e:
                if event is not None:
                    print 'Set event'
                    event.set()
                exit_normal = False
                print e
                break

            except Exception, e:
                print e

        self.stop()
        return cp_serials, exit_normal


def main():
    logger = None  # TestLogger('Sniffer')
    sn = SnifferCrow('/dev/ttyUSB0', 1111111, logger)
    sn.start()
    print 'Port is open'
    sn.stop()
    print 'Port is closed'


if __name__ == '__main__':
    main()
