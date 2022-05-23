from sniffer_parser import SnifferParser


def test_parser(byte_str):
    rc_lst = SnifferParser.hexToBinList(byte_str)
    print rc_lst


def main():
    payload = 'FE4800C30B'
    parser = SnifferParser(None)
    parser.dev_type_id = '31'
    parser.payload_parse(None, None, 'WP_IO_STAT', payload)
    # test_parser(s)

if __name__ == '__main__':
    main()
