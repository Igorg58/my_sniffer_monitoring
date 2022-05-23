import json


class SnifferParser(object):

    DEVICES_TYPE = {
        '31': 'PIR',        # Infrared motion detector
        '32': 'MAG',        # Magnetic contact
        '33': 'RMT',        # Pendant remote control
        '34': 'SMK',        # Smoke detector
        '35': 'GAS',        # Gas detector
        '36': 'GBD',        # Glass break detector
        '37': 'CAM',        # Camera PIR
        '38': 'FLD',        # Flood detector
        '39': 'VIB',        # Vibration sensor
        '3A': 'HAM',        # Home automation
        '3B': 'SPO',        # Heart & saturation monitor
        '3C': 'TFM',        # Temperature-flood-magnet detector
        '3D': 'AIRQ',       # Air Quality, Temperature, Pressure & Humidity Sensor
        '3E': 'RADON',      # Radon Gas Detector
        '3F': 'AIR_PRESS',  # Air Pressure Detector
        '45': 'SRN',        # Siren
        '46': 'SRN_SMART',  # Siren ISM +GIRA
        '51': 'BED_SENSOR', # Bed Sensor
        '52': 'PIR2',       # PIR based on ASIC CT2035
        '53': 'CAM_PIR2',   # PIR based on ASIC CT2035
        '54': 'OCCUPANCY',  # PIR based on ASIC CT2035
        '55': 'CAM-Verif',  # Camera only
        '57': 'OUT',        # IO module / AC Plug
        '58': 'OUT',        # IO module / AC Plug
        '59': 'IO2X2',      # 2 input, 2 output device
        '97': 'LED_KPD',    # LED (Icon) Keypad - TBD
        '98': 'KPD',        # Keypad (old)
        'B1': 'REPEATER',   # Repeater for GIRA
        # 'e7': 'SOC',        # AC Socket ?
    }

    # SYNC_DEVICES = [
    #     SDEVTYPE_CAM,
    #     SDEVTYPE_SRN,
    #     SDEVTYPE_OUT,
    #     SDEVTYPE_KPD,
    # ]

    SYNC_DEVICES = [
        '37',
        '45',
        '57',
        '98',
    ]

    # # General messages (commands)
    # WP_RESYNC = '94'
    # WP_SUPV = '98'
    # WP_OUTPUTS = '50'
    # WP_AREA_STATUS = '11'
    # WP_IO_STAT = '9A'
    # WP_DATA_STREAM = 'C4'
    # WP_COMMAND = 'CD'
    # WP_SABOTAGE = 'E1'
    # WP_CROW_BUSS = 'CB'

    # Redis keys
    REDIS_DEVICE_NAME_KEY = 'alias'
    REDIS_DEVICE_TYPE_ID_KEY = 'dev_type_id'

    def __init__(self, redis_obj):
        self.redis_obj = redis_obj
        self.dev_type_id = None
        self.command = None
        self.is_ack = None
        self.notApplicableStr = 'NA'  # ???

    @staticmethod
    def hexToBinList(byte_str, reverse=False):
        """
        # INPUTS:
        #     ByteStr - Byte Arr as string of Hex characters [ex: "312E3147332032342E302E3132"]
        #     reverse - True will inverse the bits order of each Byte
        # OUTPUTS:
        #     list of strings of characters [0 or 1] representing the bits of Bytes
        """

        try:
            if byte_str.strip():
                stringLen = len(byte_str) * 4
                binList = []
                binaryString = str(bin(int(byte_str, 16)))[2:]
                binaryString = binaryString.zfill(stringLen)

                for i in range(0, stringLen, 8):
                    binList.append(binaryString[i:i + 8])

                if reverse:
                    for i in range(0, len(binList), 1):
                        binList[i] = binList[i][::-1]

                return binList

        except ValueError, error:
            print(error.message)
            result = '%s That is an invalid hex value.', byte_str  # ??????????????????
            return []

    @staticmethod
    def getDeviceRssi(rssiRegisterStatus, rssiOffset):
        decimalRssi = int(str(rssiRegisterStatus), 16)
        if decimalRssi < 128:
            specificDeviceRssi = str(decimalRssi / 2 - rssiOffset)
        else:
            specificDeviceRssi = str((decimalRssi - 256) / 2 - rssiOffset)

        return specificDeviceRssi

    def statusData(self, payLoadStr):  # Appendix c
        result = []
        res_dict = {}
        payLoadStr = payLoadStr.strip()
        if not payLoadStr:
            result = [' Empty_payload ']  # obsolete
            return result, res_dict

        inverseBitList = []
        binaryNumber = self.hexToBinList(payLoadStr)
        secondByteBinRssi = 'Empty_byte_was_sent'
        emptyList = ['Empty_byte']
        index = 1
        rssiOffset = 71

        for Byte in binaryNumber:
            inverseBitList.append(Byte[::-1])

        if len(inverseBitList) > index:
            rssiOffset = 71
            rssiRegisterStatus = payLoadStr[2:4]
            RSSI = SnifferParser.getDeviceRssi(rssiRegisterStatus, rssiOffset)
            secondByteBinRssi = ['rssi: ' + RSSI]
            res_dict.update({'rssi': int(RSSI)})

        if len(inverseBitList) < 4:
            inverseBitList = inverseBitList + emptyList * (4 - len(inverseBitList))

        if self.dev_type_id == '31' or self.dev_type_id == '34' or self.dev_type_id == '37':  # PIR|SMK|CAM

            result, status_dict = self.statusDataPirSmkCam(inverseBitList[0])
            result += secondByteBinRssi
            res_dict.update(status_dict)

        elif self.dev_type_id == '3C' or self.dev_type_id == '32':  # TFM|MAG
            result, status_dict = self.statusDataTfmMag(inverseBitList[0], inverseBitList[3])
            result += secondByteBinRssi
            res_dict.update(status_dict)

        elif self.dev_type_id == '45' or self.dev_type_id == '46' or self.dev_type_id == '57':  # SRN
            result, status_dict = self.statusDataSrn(inverseBitList[0], inverseBitList[1], payLoadStr[4:5])
            res_dict.update(status_dict)

        elif self.dev_type_id == '98':
            # todo:check the correct rssi offset
            rssiRegisterStatus = payLoadStr[2:4]
            RSSI = SnifferParser.getDeviceRssi(rssiRegisterStatus, rssiOffset)
            thirdByteBinRSSi = ['rssi: ' + RSSI]
            result = thirdByteBinRSSi
            res_dict.update({'rssi': int(RSSI)})

        elif self.dev_type_id == '36':
            # todo:check the correct rssi offset#GBD
            RSSI = SnifferParser.getDeviceRssi(payLoadStr[4:6], rssiOffset)
            thirdByteBinRSSi = ['rssi: ' + RSSI]
            result = thirdByteBinRSSi
            res_dict.update({'rssi': int(RSSI)})

        elif self.dev_type_id == '33':  # '33': 'RMT/PANIC'
            # todo: fix this part because RMT&PANIC have the same devType, need to be a Distinguish between the detectors?
            context_dict ={}
            if inverseBitList[0][6] == '0':
                panic = 'Panic_on'
                context_dict.update({'panic': 'on'})
            else:
                panic = 'Panic_off'
                context_dict.update({'panic': 'off'})

            if inverseBitList[0][7] == '0':
                trouble = 'Trouble'
                context_dict.update({'trouble': 'yes'})
            else:
                trouble = 'No_trouble'
                context_dict.update({'trouble': 'no'})

            if inverseBitList[0][4] == '0':
                battery = 'Battery_low'
                context_dict.update({'battery': 'low'})
            else:
                battery = 'Battery_ok'
                context_dict.update({'battery': 'ok'})

            if inverseBitList[0][0] == '0':
                Key1Disarm = 'Key1_Disarm_released'
                context_dict.update({'key1_disarm': 'released'})
            else:
                Key1Disarm = 'Key1_Disarm_pressed'
                context_dict.update({'key1_disarm': 'pressed'})

            if inverseBitList[0][1] == '0':
                Key2Arm = 'Key2_Arm_released'
                context_dict.update({'key2_arm': 'released'})
            else:
                Key2Arm = 'Key2_Arm_pressed'
                context_dict.update({'key2_arm': 'pressed'})

            if inverseBitList[0][2] == '0':
                Key3StayArm = 'Key3_StayArm_released'
                context_dict.update({'key3_stayarm': 'released'})
            else:
                Key3StayArm = 'Key3_StayArm_pressed'
                context_dict.update({'key3_stayarm': 'pressed'})

            if inverseBitList[0][3] == '0':
                Key4Output = 'Key4_Output_released'
                context_dict.update({'key4_output': 'released'})
            else:
                Key4Output = 'Key4_Output_pressed'
                context_dict.update({'key4_output': 'pressed'})

            detector = [battery, trouble, panic, Key1Disarm, Key2Arm, Key3StayArm, Key4Output]
            result = detector
            res_dict.update(context_dict)

        return res_dict

    def statusDataPirSmkCam(self, firstByteBinId):
        res = {}
        context_dict = {}
        if firstByteBinId[0] == '0':
            superVision = 'SUPV'
            res.update({'supervision': 'yes'})
        else:
            superVision = 'No_SUPV'
            res.update({'supervision': 'no'})

        if firstByteBinId[2] == '0':
            alarm = 'Alarm'
            res.update({'alarm': 'yes'})
        else:
            alarm = 'No_alarm'
            res.update({'alarm': 'no'})

        if firstByteBinId[3] == '0':
            pictRdy = 'Pict_Rdy'
            context_dict.update({'picture_ready': {'picture_ready': 'yes'}})
        else:
            pictRdy = 'No_pic'
            context_dict.update({'picture_ready': {'picture_ready': 'no'}})

        if firstByteBinId[4] == '0':
            battery = 'Battery_low'
            res.update({'battery': 'low'})
        else:
            battery = 'Battery_ok'
            res.update({'battery': 'ok'})

        if firstByteBinId[5] == '0' and firstByteBinId[6] == '0':
            masking = 'Masking'
            context_dict.update({'masking': {'masking': 'yes'}})
        else:
            masking = 'No Masking'
            context_dict.update({'masking': {'masking': 'no'}})

        if firstByteBinId[6] == '0':
            tamper = 'Tamper_open'
            res.update({'tamper': 'open'})
        else:
            tamper = 'Tamper_close'
            res.update({'tamper': 'close'})

        if firstByteBinId[7] == '0':
            trouble = 'Trouble'
            res.update({'trouble': 'yes'})
        else:
            trouble = 'No_trouble'
            res.update({'trouble': 'no'})

        pirDetector = [superVision, alarm, self.notApplicableStr, battery, masking, tamper, trouble]
        smkDetector = [superVision, alarm, self.notApplicableStr, battery, tamper, trouble]
        camDetector = [superVision, alarm, pictRdy, battery, tamper, trouble]

        if self.dev_type_id == '31':
            result = pirDetector
            res.update(context_dict['masking'])

        elif self.dev_type_id == '34':
            result = smkDetector

        elif self.dev_type_id == '37':
            result = camDetector
            res.update(context_dict['picture_ready'])

        else:
            result = [str(self.dev_type_id) + " is unknown dev_type_id"]
            res = {}

        return result, res

    def statusDataTfmMag(self, firstByteBinId, fourthByteBin):
        res = {}
        if firstByteBinId[0] == '0':
            superVision = 'SUPV'
            res.update({'supervision': 'yes'})
        else:
            superVision = 'NO_SUPV'
            res.update({'supervision': 'no'})

        if firstByteBinId[2] == '0':
            alarm = 'Alarm'
            res.update({'alarm': 'yes'})
        else:
            alarm = 'NO_Alarm'
            res.update({'alarm': 'no'})

        if firstByteBinId[3] == '0':
            alarm2 = 'Alarm2'
            res.update({'alarm2': 'yes'})
        else:
            alarm2 = 'NO_Alarm2'
            res.update({'alarm2': 'no'})

        if firstByteBinId[4] == '0':
            battery = 'Battery_low'
            res.update({'battery': 'low'})
        else:
            battery = 'Battery_ok'
            res.update({'battery': 'ok'})

        if firstByteBinId[6] == '0':
            tamper = 'Tamper_open'
            res.update({'tamper': 'open'})
        else:
            tamper = 'Tamper_close'
            res.update({'tamper': 'close'})

        if firstByteBinId[7] == '0':
            trouble = 'Trouble'
            res.update({'trouble': 'yes'})
        else:
            trouble = 'NO_trouble'
            res.update({'trouble': 'no'})

        result = [superVision, alarm, alarm2, battery, tamper, trouble]

        if self.dev_type_id == '3C':  # TFM
            externalTemperature = 'Temperature: ' + fourthByteBin
            result = result + [externalTemperature]
            res.update({'temperature': fourthByteBin})

        return result, res

    def statusDataSrn(self, firstByteBinId, secondByteBinId, rSSIHexValue):
        res = {}
        if firstByteBinId[4] == '0':
            battery = 'Battery_low'
            res.update({'battery': 'low'})
        else:
            battery = 'Battery_ok'
            res.update({'battery': 'ok'})

        if firstByteBinId[6] == '0':
            tamper = 'Tamper_open'
            res.update({'tamper': 'open'})
        else:
            tamper = 'Tamper_close'
            res.update({'tamper': 'close'})

        if firstByteBinId[7] == '0':
            trouble = 'Trouble'
            res.update({'trouble': 'yes'})
        else:
            trouble = 'NO_trouble'
            res.update({'trouble': 'no'})

        if secondByteBinId[0] == '0':
            flasher = 'Flash_on'
            res.update({'flash': 'on'})
        else:
            flasher = 'Flash_off'
            res.update({'flash': 'off'})

        if secondByteBinId[1] == '0':
            sounder = 'Sound_on'
            res.update({'sound': 'on'})
        else:
            sounder = 'Sound-off'
        res.update({'sound': 'off'})

        # todo:check the correct rssi offset
        rssiOffset = 71
        RSSI = SnifferParser.getDeviceRssi(rSSIHexValue, rssiOffset)
        rssi = 'rssi: ' + RSSI
        result = [battery, tamper, trouble, flasher, sounder, rssi]
        res.update({'rssi': int(RSSI)})

        return result, res

    def configData(self, payLoadStr):
        res_dict = {}
        payLoadStr = payLoadStr.strip()
        if not payLoadStr:
            result = [' Empty_payload ']  # obsolete
            return res_dict

        binaryNumber = SnifferParser.hexToBinList(payLoadStr)
        inversBitList = []
        result = [] # To be del
        res = {}
        emptylist = ['Empty_byte']

        for Byte in binaryNumber:
            inversBitList.append(Byte[::-1])

        if len(inversBitList) < 4:  # initialize empty byte list
            inversBitList = inversBitList + emptylist * (4 - len(inversBitList))

        if self.dev_type_id == '31' or self.dev_type_id == '32' or self.dev_type_id == '34' or self.dev_type_id == '3C':  # PIR|MAG|SMK|TFM
            result, res_dict = self.configDataPirMagSmkTfm(inversBitList[0], inversBitList[1])

        elif self.dev_type_id == '45' or self.dev_type_id == '46' or self.dev_type_id == '57':  # SRN

            result, res_dict = self.configDataSrn(inversBitList[0], inversBitList[1])

        elif self.dev_type_id == '98':  # Keypad
            result, res_dict = self.configDataKPD(payLoadStr)

        elif self.dev_type_id == '57':  # Output
            result, res_dict = self.configDataOutput(inversBitList[0], inversBitList[1], inversBitList[2], inversBitList[3])

        elif self.dev_type_id == '36':  # GBD
            result, res_dict = self.configDataGbd(inversBitList[0], inversBitList[1])

        elif self.dev_type_id == '37':  # CAMPIR
            if 'WP_AREA_STATUS' in self.command:
                result, res_dict = self.configDataCamPir(inversBitList[1], inversBitList[0], inversBitList[2],
                                               inversBitList[3])
            else:
                result, res_dict = self.configDataCamPir(inversBitList[0], inversBitList[1], inversBitList[2],
                                               inversBitList[3])
        return res_dict

    def configDataPirMagSmkTfm(self, firstByteBinId, secondByteBinId):
        res = {} #IG
        timeDict = {'000': '7 min',
                    '100': '1 min',
                    '010': '2 min',
                    '110': '4 min',
                    '001': '10 min',
                    '101': '15 min',
                    '011': '20 min',
                    '111': '30 min'}

        pulsesDict = {'00': '1 pulse',
                      '10': '2 pulse',
                      '01': '3 pulse',
                      '11': '1 pulse no filtering'}

        extTfmDict = {'00': 'ext disabled',
                      '01': 'ext reed SW enabled',
                      '10': 'ext temp probe enabled',
                      '11': 'ext flood probe enabled'}

        time = ''
        externalTfm = ''
        pulses = ''
        context_dict = {} #IG

        if firstByteBinId != 'Empty_byte':
            time = "TX:" + timeDict[firstByteBinId[1:4]]
            res.update({'tx_time': timeDict[firstByteBinId[1:4]]}) #IG

        if secondByteBinId != 'Empty_byte':
            externalTfm = 'ext_Tfm:' + extTfmDict[secondByteBinId[4:6]]
            pulses = pulsesDict[secondByteBinId[4:6]]
            context_dict.update({'ext_tfm': {'ext_tfm': extTfmDict[secondByteBinId[4:6]]}})
            context_dict.update({'pulses': {'pulses': pulsesDict[secondByteBinId[4:6]]}})

        if firstByteBinId[4] == '1':
            mute = 'Mute_on'
            res.update({'mute': 'on'})
        else:
            mute = 'Mute_off'
            res.update({'mute': 'off'})

        if firstByteBinId[5] == '1':
            indication = 'Indication_active'
            res.update({'indication': 'active'})
        else:
            indication = 'No_indication'
            res.update({'indication': 'no'})

        if firstByteBinId[6] == '1':
            walkTest = 'Walk_test_active'
            res.update({'walk_test': 'active'})
        else:
            walkTest = 'No_walk_test'
            res.update({'walk_test': 'no'})

        if firstByteBinId[7] == '1':
            armed = 'Armed'
            res.update({'armed': 'yes'})
        else:
            armed = 'Not_armed'
            res.update({'armed': 'no'})

        gainControl = int(secondByteBinId[::-1][5:], 2)
        if gainControl > 4:
            gainControl = 'Wrong_gain_ctrl-->' + str(gainControl)
            context_dict.update({'gain_ctrl': {'gain_ctrl': '{} (wrong)'.format(gainControl)}})
        else:
            gainControl = 'Gain_ctrl:' + 'Level_' + str(gainControl)
            context_dict.update({'gain_ctrl': {'gain_ctrl': '{}'.format(gainControl)}})

        if secondByteBinId[3] == '1':  # HPF-high pass filter cutoff freq
            hpf = 'HPF_on'
            context_dict.update({'hpf': {'hpf': 'on'}})
        else:
            hpf = 'HPF_off'
            context_dict.update({'hpf': {'hpf': 'off'}})

        if secondByteBinId[6] == '1':
            localConfig = 'Device_config'
            context_dict.update({'local_config': {'local_config': 'device'}})
        else:
            localConfig = 'Host_config'
            context_dict.update({'local_config': {'local_config': 'host'}})

        if secondByteBinId[7] == '1':
            stayArmed = 'Stay_armed'
            context_dict.update({'stay_armed': {'armed': 'yes'}})
        else:
            stayArmed = 'Not_stay_armed'
            context_dict.update({'stay_armed': {'armed': 'no'}})

        if secondByteBinId[1] == '1':
            externalMag = 'Ext_mag_enable'
            context_dict.update({'ext_mag': {'ext_mag': 'enable'}})
        else:
            externalMag = 'Ext_mag_disable'
            context_dict.update({'ext_mag': {'ext_mag': 'disable'}})

        if secondByteBinId[2] == '1':
            internalMag = 'Int_mag_enable'
            context_dict.update({'int_mag': {'int_mag': 'enable'}})
        else:
            internalMag = 'Int_mag_disable'
            context_dict.update({'int_mag': {'int_mag': 'disable'}})

        if secondByteBinId[0] == '1':
            sensorsDetects = 'Logic<AND>'
            context_dict.update({'sensor_detects': {'sensor_detects': 'logic <AND>'}})
        else:
            sensorsDetects = 'Logic<OR>'
            context_dict.update({'sensor_detects': {'sensor_detects': 'logic <OR>'}})

        if secondByteBinId[1] == '1':
            heat = 'Heat_on'
            context_dict.update({'heat': {'heat': 'on'}})
        else:
            heat = 'Heat_off'
            context_dict.update({'heat': {'heat': 'off'}})

        if secondByteBinId[2] == '1':
            smoke = 'Smoke_on'
            context_dict.update({'smoke': {'smoke': 'off'}})

        else:
            smoke = 'Smoke_off'
            context_dict.update({'smoke': {'smoke': 'off'}})

        result = [time, mute, indication, walkTest, armed]
        pirDetector = result + [gainControl, hpf, pulses, localConfig, stayArmed]
        magDetector = result + [sensorsDetects, externalMag, internalMag, localConfig, stayArmed]
        smkDetector = result + [sensorsDetects, heat, smoke, localConfig, stayArmed]
        tfmDetector = result + [sensorsDetects, internalMag, externalTfm, localConfig, stayArmed]

        if self.dev_type_id == '31':
            result = pirDetector
            res.update(context_dict['gain_ctrl'])
            res.update(context_dict['hpf'])
            res.update(context_dict['pulses'])
            res.update(context_dict['local_config'])
            res.update(context_dict['stay_armed'])

        elif self.dev_type_id == '32':
            result = magDetector
            res.update(context_dict['sensor_detects'])
            res.update(context_dict['ext_mag'])
            res.update(context_dict['int_mag'])
            res.update(context_dict['local_config'])
            res.update(context_dict['stay_armed'])

        elif self.dev_type_id == '34':
            result = smkDetector
            res.update(context_dict['sensor_detects'])
            res.update(context_dict['heat'])
            res.update(context_dict['smoke'])
            res.update(context_dict['local_config'])
            res.update(context_dict['stay_armed'])

        elif self.dev_type_id == '3C':
            result = tfmDetector
            res.update(context_dict['sensor_detects'])
            res.update(context_dict['int_mag'])
            res.update(context_dict['ext_tfm'])
            res.update(context_dict['local_config'])
            res.update(context_dict['stay_armed'])

        else:
            result = [str(self.dev_type_id) + " is unknown_dev_type_id"]
            res = {}

        return result, res

    def configDataSrn(self, firstByteBinId, secondByteBinId):
        res = {}
        ledTimeOutDict = {'00': 'Equals Sound',
                          '01': 'Sound timeout +5 min',
                          '10': 'Sound_timeout +15 min',
                          '11': 'No timeout'}

        sounderLoudnessDict = {'00': 'level 1',
                               '01': 'level 2',
                               '10': 'level 3',
                               '11': 'level 4'}

        sounderActivaionTimeOutDict = {'00': '1 min',
                                       '01': '2 min',
                                       '10': '10 min',
                                       '11': '15 min'}

        ledTimeOut = ''
        souderLoudness = ''
        souderActivationTimeOut = ''

        if firstByteBinId != 'Empty_byte':
            ledTimeOut = 'Led_timeOut:' + ledTimeOutDict[firstByteBinId[0:2]]
            souderLoudness = 'Sound_loudness:' + sounderLoudnessDict[firstByteBinId[2:4]]
            souderActivationTimeOut = 'Sound_activaion_timeOut:' + sounderActivaionTimeOutDict[firstByteBinId[4:6]]

            res.update({'led_timeout': ledTimeOutDict[firstByteBinId[0:2]]})
            res.update({'sound_loudness': sounderLoudnessDict[firstByteBinId[2:4]]})
            res.update({'sound_activation_timeout': sounderActivaionTimeOutDict[firstByteBinId[4:6]]})

        if secondByteBinId[0] == '0':
            sounderOnMode = 'Sound_on_mode_disable'
            res.update({'sound_on': 'disable'})
        else:
            sounderOnMode = 'Sound_on_mode_enable'  #???
            res.update({'sound_on': 'enable'})  #???

        if secondByteBinId[1] == '0':
            sounderArmDisarm = 'Sound_arm/disarm_off'
            res.update({'sound_arm_disarm': 'off'})
        else:
            sounderArmDisarm = 'Sound_arm/disarm_on'
            res.update({'sound_arm_disarm': 'on'})

        if secondByteBinId[2] == '0':
            ledOnMode = 'Led_on_mode_disable'
            res.update({'led_on_mode': 'disable'})
        else:
            ledOnMode = 'Led_off_mode_enable'
            res.update({'led_off_mode': 'enable'})

        if secondByteBinId[3] == '0':
            ledArmDisarm = 'Led_arm/disarm_off'
            res.update({'led_arm_disarm': 'off'})
        else:
            ledArmDisarm = 'Led_arm/disarm_on'
            res.update({'led_arm_disarm': 'on'})

        if secondByteBinId[5] == '0':
            flashLeds = 'leds_disable'
            res.update({'leds': 'disable'})
        else:
            flashLeds = 'leds_enable'
            res.update({'leds': 'enable'})

        if secondByteBinId[6] == '0':
            systemStat = 'Sys_normal_stat'
            res.update({'system_status': 'normal'})
        else:
            systemStat = 'Sys_WalkTest_stat'
            res.update({'system_status': 'walk test'})

        if secondByteBinId[6] == '0':
            systemActiveStat = 'Sys_in_stand_by_stat'
            res.update({'system_active': 'stand-by'})
        else:
            systemActiveStat = 'Sys_in_active_stat'
            res.update({'system_active': 'active'})

        result = [ledTimeOut, souderLoudness, souderActivationTimeOut, sounderOnMode
            , sounderArmDisarm, ledOnMode, ledArmDisarm, flashLeds, systemStat, systemActiveStat]

        if firstByteBinId[6] == '1':
            factoryDefaultConfig = 'Reset_to_factory_default'
            result = result + [factoryDefaultConfig]
            res.update({'reset': 'factory_default'})
        # else:
        #     result = result

        return result, res

    def configDataKPD(self, payload):
        result = []
        res = {}

        if 'WP_SUPV' in self.command:
            if payload[0:]:  # TBD ????????????
                configSessionCounter = 'Config_counter: ' + payload[0:]
                result.append(configSessionCounter)
                res.update({'config_counter': payload[0:]})  # TBD ????????????

            if payload[7] == '1':  # TBD ????????????
                supervision = 'Power up supervision'
                result.append(supervision)
                res.update({'power_up_supervision': 'yes'})  # TBD ????????????

        if 'WP_RESYNC' in self.command:
            if payload[4:6]:
                kpdIndex = 'Number of KPD index: ' + str(int(payload[4:6], 16))
                result.append(kpdIndex)
                res.update({'kpd_index': int(payload[4:6], 16)})

            if payload[6:8]:
                numberOfSentConfiguration = 'Number of sent CFG: ' + str(int(payload[6:8], 16))
                result.append(numberOfSentConfiguration)
                res.update({'number_sent_CFG': int(payload[6:8], 16)})

        return result, res

    def configDataOutput(self, firstByteBinId, secondByteBinId, thirdByteBinId, fourthByteBinId):
        res = {}
        activationTimeoutDict = {'000': 'No timeout',
                                 '001': '1 min',
                                 '010': '2 min',
                                 '011': '10 min',
                                 '100': '15 min',
                                 '101': '30 min',
                                 '110': '45 min',
                                 '111': '60 min'}

        systemStateDict = {'00': 'Disarm state',
                           '01': 'Walk test state',
                           '10': 'Arm state',
                           '11': 'NOT SUPPORTED'}

        result = []

        if firstByteBinId != 'Empty_byte':
            activationTimeout = 'Activation_timeout:' + activationTimeoutDict[firstByteBinId[3:6]]
            result.append(activationTimeout)
            res.update({'activation_timeout': [firstByteBinId[3:6]]})

        if firstByteBinId[6] == '0':
            maintenanceMode = 'Maintenance_mode_disable'
            res.update({'maintenance_mode': 'disable'})
        else:
            maintenanceMode = 'Maintenance_mode_enable'
            res.update({'maintenance_mode': 'enable'})

        if secondByteBinId[5] == '0':
            led = 'Leds_disable'
            res.update({'leds': 'disable'})
        else:
            led = 'Leds_enable'
            res.update({'leds': 'enable'})

        if secondByteBinId != 'Empty_byte':
            systemState = systemStateDict[secondByteBinId[6:]]
            result.append(systemState)
            res.update({'system_state': systemStateDict[secondByteBinId[6:]]})

        if thirdByteBinId[0:] != 'Empty_byte':
            pulseOnTime = 'Pulse_on=' + str(int(thirdByteBinId[0:], 2) * 0.1) + ' sec'
            res.update({'pulse_on_time': str(int(thirdByteBinId[0:], 2) * 0.1)})
        else:
            pulseOnTime = 'No_pulse_on_time'
            res.update({'pulse_on_time': 'no'})

        if fourthByteBinId[0:] != 'Empty_byte':
            pulseOffTime = 'Pulse_off:' + str(int(fourthByteBinId[0:], 2) * 0.1) + ' sec'
            res.update({'pulse_off_time': str(int(fourthByteBinId[0:], 2) * 0.1)})
        else:
            pulseOffTime = 'No_pulse_off_time'
            res.update({'pulse_off_time': 'no'})

        result.append(maintenanceMode)
        result.append(led)
        result.append(pulseOnTime)
        result.append(pulseOffTime)

        return result, res

    def configDataGbd(self, firstByteBinId, secondByteBinId):
        res = {}
        sensitivityDict = {'00': 'Disable',
                           '01': 'Low sensitivity',
                           '10': 'Mid sensitivity',
                           '11': 'High sensitivity'}

        gbdSensorAutoGainCtrlDict = {'00': '0% ',
                                     '01': '25%',
                                     '10': '50%(default)',
                                     '11': '75%'}

        supervisiontimeDict = {'000': '7 min',
                               '001': '1 min',
                               '010': '2 min',
                               '011': '4 min',
                               '100': '10 min',
                               '101': '15 min',
                               '110': '20 min',
                               '111': '30 min'}

        systemStateDict = {'00': 'Disarm state',
                           '01': 'Walk test state',
                           '10': 'Arm_state',
                           '11': 'Not supported'}

        result = []

        if firstByteBinId != 'Empty_byte':
            gbdSensorl = 'GBD_sensor:' + sensitivityDict[firstByteBinId[1:3]]
            result.append(gbdSensorl)
            gbdSensorAutoGainCtrl = 'GBD_sensor_auto_gain_ctrl:' + gbdSensorAutoGainCtrlDict[firstByteBinId[3:5]]
            result.append(gbdSensorAutoGainCtrl)
            fallSensor = 'Fall_sensor' + sensitivityDict[firstByteBinId[5:7]]
            result.append(fallSensor)
            res.update({
                'gbd_sensor': sensitivityDict[firstByteBinId[1:3]],
                'gbd_sensor_auto_gain_ctrl': gbdSensorAutoGainCtrlDict[firstByteBinId[3:5]],
                'fall_sensor': sensitivityDict[firstByteBinId[5:7]]
            })

        if firstByteBinId != 'Empty_byte' and secondByteBinId != 'Empty_byte':
            vibrationSensor = 'Vibration_sensor:' + sensitivityDict[firstByteBinId[7] + secondByteBinId[0]]
            result.append(vibrationSensor)
            res.update({'vibration_sensor': sensitivityDict[firstByteBinId[7] + secondByteBinId[0]]})

        if firstByteBinId[0] == '0':
            sensorsDetectionLogic = 'Sensors_Logic=OR'
            res.update({'sensors_logic': 'OR'})
        else:
            sensorsDetectionLogic = 'Sensors_Logic=AND'
            res.update({'sensors_logic': 'AND'})
        result.append(sensorsDetectionLogic)

        if secondByteBinId != 'Empty_byte':
            supervision = 'SUPV:' + supervisiontimeDict[secondByteBinId[1:4]]
            result.append(supervision)
            systemState = systemStateDict[secondByteBinId[6:]]
            result.append(systemState)
            res.update({
                'supervision': supervisiontimeDict[secondByteBinId[1:4]],
                'system_state': systemStateDict[secondByteBinId[6:]]
            })

        if secondByteBinId[4] == '0':
            mute = 'Mute_enabled'
            res.update({'mute': 'enabled'})  # ???
        else:
            mute = 'Mute_disabled'
            res.update({'mute': 'disabled'})  # ???

        if secondByteBinId[5] == '0':
            leds = 'Leds_disabled'
            res.update({'leds': 'disabled'})
        else:
            leds = 'Leds_enabled'
            res.update({'leds': 'enabled'})

        result.append(mute)
        result.append(leds)

        return result, res

    def configDataCamPir(self, firstByteBinId, secondByteBinId, thirdByteBinId, fourthByteBinId):
        res = {}
        pulsesDict = {'00': '1 pulse',
                      '01': '2 pulse',
                      '10': '3 pulse',
                      '11': '1 pulse no filtering'}

        numOfPicInOneSetDict = {'000': '1 pic',
                                '001': '2 pic',
                                '010': '3 pic',
                                '011': '4 pic',
                                '100': '5 pic',
                                '101': 'Wrong number of pic config',
                                '110': 'Wrong number of pic config',
                                '111': 'Wrong number of pic config',}

        systemStateDict = {'00': 'Disarm state',
                           '01': 'Walk test state',
                           '10': 'Arm state',
                           '11': 'Not supported'}

        pictureColorAndResolutionDict = {'00': 'QVGA B&W(320x240)',
                                         '01': 'VGA B&W(640x480)',
                                         '10': 'QVGA Color(320x240)',
                                         '11': 'VGA Color(640x480)'}

        pictureRateDict = {'000': '0.3 sec',
                           '001': '0.5 sec',
                           '010': '1 sec',
                           '011': '1.4 sec',
                           '100': '2 sec',
                           '101': '5 sec(regular mode JPEG only)',
                           '110': '15 sec(regular mode JPEG only)',
                           '111': '30 sec(regular mode JPEG only)'}

        holdOffTimeDict = {'000': '30 sec',
                           '001': '45 sec',
                           '010': '60 sec',
                           '011': '75 sec',
                           '100': '90 sec',
                           '101': '105 sec',
                           '110': '120 sec',
                           '111': 'T.B.D'}

        pictureQualityDict = {'000': '20%',
                              '001': '30%',
                              '010': '40%',
                              '011': '50%',
                              '100': '60%',
                              '101': '70%',
                              '110': '80%',
                              '111': '90%'}

        result = []

        if secondByteBinId != 'Empty_byte':
            secondByteBinId = secondByteBinId[::-1]
            pirSensorPulsesFilterConfig = pulsesDict[secondByteBinId[2:4]]
            result.append(pirSensorPulsesFilterConfig)
            res.update({'pulses_filter': pirSensorPulsesFilterConfig})

        if firstByteBinId != 'Empty_byte':
            firstByteBinId = firstByteBinId[::-1]
            systemState = systemStateDict[firstByteBinId[0:2]]
            result.append(systemState)
            numOfPicInOneSet = numOfPicInOneSetDict[firstByteBinId[5:8]]
            result.append(numOfPicInOneSet)
            res.update({
                'system_state': systemState,
                'pic_in_one_set': numOfPicInOneSet
            })

        if thirdByteBinId != 'Empty_byte':
            thirdByteBinId = thirdByteBinId[::-1]
            holdOffTime = 'Hold_off:' + holdOffTimeDict[thirdByteBinId[0:3]]
            result.append(holdOffTime)
            pictureRate = 'Pic_rate:' + pictureRateDict[thirdByteBinId[3:6]]
            result.append(pictureRate)
            pictureColorAndResolution = pictureColorAndResolutionDict[thirdByteBinId[6:8]]
            result.append(pictureColorAndResolution)
            res.update({
                'hold_off': holdOffTimeDict[thirdByteBinId[0:3]],
                'pic_rate': pictureRateDict[thirdByteBinId[3:6]],
                'pic_color_and_resolution': pictureColorAndResolutionDict[thirdByteBinId[6:8]]
            })

        if fourthByteBinId != 'Empty_byte':
            fourthByteBinId = fourthByteBinId[::-1]
            pictureQuality = 'Pic_quality' + pictureQualityDict[fourthByteBinId[0:3]]
            result.append(pictureQuality)
            res.update({'pic_quality': pictureQualityDict[fourthByteBinId[0:3]]})

        if secondByteBinId != 'Empty_byte':
            gainControl = int(secondByteBinId[5:8], 2)
            if gainControl > 4:
                gainControl = 'Wrong_Gain_ctrl-->' + str(gainControl)
                res.update({'gain_ctrl': 'wrong {}'.format(gainControl)})
            else:
                gainControl = 'Gain_Ctrl: ' + 'Level_' + str(gainControl)
                res.update({'gain_ctrl': 'level {}'.format(gainControl)})
            result.append(gainControl)

        if secondByteBinId[4] == '0':
            petImmuneFilter = 'PetImmune:Disabled'
            res.update({'pet_immune': 'disable'})
        else:
            petImmuneFilter = 'PetImmune:Enabled'
            res.update({'pet_immune': 'enable'})

        if secondByteBinId[0] == '0':
            camEnabling = 'CAM:Disable'
            res.update({'cam': 'disable'})
        else:
            camEnabling = 'CAM:Enable'
            res.update({'cam': 'enable'})

        if firstByteBinId[3] == '0':
            mute = 'Mute_disabled'
            res.update({'mute': 'disable'})
        else:
            mute = 'Mute_enabled'
            res.update({'mute': 'enable'})

        if firstByteBinId[2] == '0':
            leds = "Leds_disabled"
            res.update({'leds': 'disable'})
        else:
            leds = "Leds_enabled"
            res.update({'leds': 'enable'})

        if fourthByteBinId[7] == '0':
            diffJpeg = 'Diff_JPEG_low'
            res.update({'diff_jpeg': 'low'})
        else:
            diffJpeg = 'Diff_JPEG_high'
            res.update({'diff_jpeg': 'high'})

        if fourthByteBinId[6] == '0':
            jpegMode = 'Regular_JPEG'
            res.update({'jpeg': 'regular'})
        else:
            jpegMode = 'Differential_JPEG'
            res.update({'jpeg': 'differential'})

        if fourthByteBinId[5] == '0':
            contrastEnhancement = 'Contrast_disable'
            res.update({'contrast': 'disable'})
        else:
            contrastEnhancement = 'Contrast_enable(auto)'
            res.update({'contrast': 'enable(auto)'})

        if fourthByteBinId[4] == '0':
            sharpnessEnhancement = 'Sharpness_disable'
            res.update({'sharpness': 'disable'})
        else:
            sharpnessEnhancement = 'Sharpness_enable'
            res.update({'sharpness': 'enable'})

        result.append(petImmuneFilter)
        result.append(camEnabling)
        result.append(mute)
        result.append(leds)
        result.append(diffJpeg)
        result.append(jpegMode)
        result.append(contrastEnhancement)
        result.append(sharpnessEnhancement)

        return result, res

    def control_parser(self, ctl):
        ctl_bin = bin(ctl)[2:].zfill(8)
        ctl_bin_rev = ctl_bin[::-1]
        ctl_num_rev = int(ctl_bin_rev, 2)
        mask_seq = 0b11000000
        seq = (ctl_num_rev & mask_seq) >> 6

        mask_ack = 0b00100000
        # ack = "ack" if (ctl_num_rev & mask_ack) >> 5 == 1 else "msg"
        if (ctl_num_rev & mask_ack) >> 5 == 1:
            ack = "ack"
            self.is_ack = True
        else:
            ack = "msg"
            self.is_ack = False

        mask_one_way = 0b00000010
        one_way = "one_way" if (ctl_num_rev & mask_one_way) >> 1 == 1 else "two_way"

        mask_repeater = 0b00000001
        repeater = "yes" if ctl_num_rev & mask_repeater else 'no'

        res = {
            "value": ctl,
            "seq": seq,
            "ack-msg": ack,
            "way": one_way,
            "repeater": repeater
        }
        # print res
        return res

    def payload_parse(self, sn_src, sn_dest, cmd, payload):
        res = {"value": payload}
        type_id_src = self.redis_obj.hget(sn_src, SnifferParser.REDIS_DEVICE_TYPE_ID_KEY)
        type_id_dest = self.redis_obj.hget(sn_dest, SnifferParser.REDIS_DEVICE_TYPE_ID_KEY)
        if type_id_src is None and type_id_dest is None and not 'WP_RESYNC' in cmd:
            return res
        else:
            f = lambda x, y: x if x is not None else y
            self.dev_type_id = f(type_id_src, type_id_dest)

        self.command = cmd
        if 'WP_RESYNC' in cmd:
            if self.is_ack:  # ACK
                if self.dev_type_id in SnifferParser.SYNC_DEVICES:
                    conf_data = self.configData(payload)
                    res.update(conf_data)
            #         result = [timeSlot, timeSlotNumber] + configResult
                    res.update({"time_slot": int(payload[:2], 16),
                                "time_slot_number": int(payload[3], 16)
                                })
                else:
                    conf_data = self.configData(payload)
                    res.update(conf_data)
            else:  # MSG
                self.dev_type_id = payload[:2]
                self.redis_obj.hset(sn_src, SnifferParser.REDIS_DEVICE_TYPE_ID_KEY, self.dev_type_id)
                res.update({
                    "rfm_sw_ver": payload[2:4],
                    "rfm_hw_ver": payload[4:8]
                })

        elif 'WP_CROW_BUSS' in cmd:  # CB = WP_CROW_BUSS
            if self.dev_type_id == '98':  # KPD
                parse = self.parseCrowBusMsgKpd(payload)
                res.update(parse)

        elif 'WP_SUPV' in cmd:  # 98 = WP_SUPV
            if self.is_ack:  # ACK
                data = self.statusData(payload)
                res.update(data)
            else:
                if payload[0:2] != '1E':
                    payLoadFirstByte = 'Wrong_SUPV_period '
                    # result = [payLoadFirstByte] + self.configData(payload[2:])[0]
                    res.update({'surv_period': 'wrong'})
                else:
                    payLoadFirstByte = 'SUPV_period_60_sec'
                    # result = [payLoadFirstByte] + self.configData(payload[2:])[0]
                    res.update({'surv_period': '60 sec'})

        elif 'WP_OUTPUTS' in cmd:  # 50 = OUTPUTS
            if self.is_ack:  # ACK
                data = self.statusData(payload)
                res.update(data)
            else:
                if payload[0:2] == '00':
                    # result = 'Pulses_off'
                    res.update({'pulses': 'off'})
                else:
                    # result = 'Pulses_ON,Pulses=' + payload[0:2]
                    res.update({'pulses': 'on {}'.format(payload[0:2])})

        elif 'WP_AREA_STATUS' in cmd:  # 11 = AREA_STATUS
            if self.is_ack:  # ACK
                data = self.statusData(payload)
                res.update(data)
            else:
                conf_data = self.configData(payload)
                res.update(conf_data)

        elif 'WP_COMMAND' in cmd:  # CD = COMMAND
            if self.is_ack:  # ACK
                # result = [' Empty_payload']
                pass
            else:
                opCodeDict = {'00': 'NOP',
                              '01': 'ARM',
                              '02': 'DISARM',
                              '03': 'STAY',
                              '04': 'MUTE',
                              '05': 'WALK_TEST',
                              '11': 'BEEP',
                              '50': 'OUTPUT',
                              '51': 'GET_PIC',
                              '52': 'TAKE_PIC',
                              '53': 'CANCEL_PIC_SESSION',
                              '54': 'DELETE_PIC_SESSION',
                              '55': 'DELETE_TAKE_PIC'}

                opCode = opCodeDict[payload[0:2]]
                sessionPrefix = 'Session_prefix:0x' + payload[2:4]
                # result = [opCode, sessionPrefix]
                res.update({
                    'operation_code': opCodeDict[payload[0:2]],
                    'session_prefix': payload[2:4]
                })

        elif 'WP_IO_STAT' in cmd:  # 9A = IO_STAT
            if self.is_ack:  # ACK
                data = self.configData(payload)
            else:  # Message
                data = self.statusData(payload)
            res.update(data)

        res.update({"device_type": SnifferParser.DEVICES_TYPE.get(self.dev_type_id, 'NOT supported')})
        res.update({"parsed": json.dumps(res, sort_keys=True, indent=1, separators=('', ': ')).strip('{}\n\r')})
        return res

    def parseCrowBusMsgKpd(self, payloadStr):
        # result = []
        res = {}

        if len(payloadStr) > 56:
            if payloadStr == '310384002C000000000022000000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000':
                isError = 'kpd status ok'
                res.update({'kpd_error': 'status OK'})
            else:
                isError = ['*                      ***** Error - RFM !!!*****']
                res.update({'kpd_error': 'error RFM'})
            result = isError

        if payloadStr[0:2] == '0D' and payloadStr[4:8] == '0411':  # update date & time
            dayDict = {'01': 'Sunday',
                       '02': 'Monday',
                       '03': 'Tuesday',
                       '04': 'Wednesday',
                       '05': 'Thursday',
                       '06': 'Friday',
                       '07': 'Saturday'}

            day = dayDict[payloadStr[12:14]]
            date = payloadStr[26:28] + "/" + payloadStr[14:16] + "/" + payloadStr[18:20] + payloadStr[16:18]
            time = payloadStr[24:26] + ':' + payloadStr[22:24] + ':' + payloadStr[20:22]
            dateTimeUpdated = ['Date & time updated: ' + day + ' ' + date + ' ' + time]

            # result = dateTimeUpdated
            res.update({'kpd_date_time': '{} {} {}'.format(day, date, time)})

        if payloadStr[0:2] == '09':
            structureIndex = 'kpd structure index: ' + payloadStr[2:4]
            structureOffset = 'Offset in serenity structure: ' + payloadStr[6:8] + payloadStr[4:6]
            res.update({
                'kpd_structure_index': payloadStr[2:4],
                'serenity_structure_offset': payloadStr[6:8] + payloadStr[4:6]
            })

            if payloadStr[12:]:
                sentBit = payloadStr[12:]
            else:
                sentBit = 'None'

            if payloadStr[8:12] == 'FFFF':
                bit = 'sent Reset bit ' + sentBit
                res.update({'kpd_reset_bit': sentBit})
            else:
                bit = 'sent Set bit: ' + sentBit
                res.update({'kpd_set_bit': sentBit})

            # result = [structureIndex, structureOffset, bit]

        return res

