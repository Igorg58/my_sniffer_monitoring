import time
import json

deviceTypeDict = {'31': 'PIR/CURTAIN/EDS',
                  '32': 'MAG',
                  '34': 'SMK',
                  '35': 'GAS',
                  '36': 'GBD',
                  '37': 'CAM',
                  '38': 'FLD',
                  '3C': 'TEMP',
                  '45': 'SRN',
                  '46': 'EXT_SRN',
                  '57': 'IO',
                  '98': 'KPD',
                  '33': 'RMTC'}




asyncDeviceTypeDict = {'31': 'PIR/CURTAIN/EDS',
                       '32': 'MAG',
                       '34': 'SMK',
                       '35': 'GAS',
                       '36': 'GBD',
                       '38': 'FLD',
                       '3C': 'TFM',
                       '33': 'RMTC'}

def getAsyncDeviceType(deviceTypHexString):

    if asyncDeviceTypeDict.has_key(deviceTypHexString):
        deviceTypeName = asyncDeviceTypeDict[deviceTypHexString]
    else:
        deviceTypeName = '%s is NA' % deviceTypHexString

    result = deviceTypeName
    return result


def getDeviceType(deviceTypHexString):

        isValidDevice = False

        try:

            deviceTypHexString = deviceTypHexString.replace('0x', '')

        except AttributeError:
            pass

        if deviceTypeDict.has_key(deviceTypHexString):

            deviceTypeName = deviceTypeDict[deviceTypHexString]
            isValidDevice = True

        else:

            deviceTypeName = 'Device_type %s is NA' % deviceTypHexString

        result = [isValidDevice, deviceTypeName]

        return result

def getDeviceRssi(rssiRegisterStatus, rssiOffset):

    decimalRssi = int(str(rssiRegisterStatus), 16)

    if decimalRssi < 128:
        specificDeviceRssi = str(decimalRssi/2 - rssiOffset)
    else:
        specificDeviceRssi = str((decimalRssi-256)/2 - rssiOffset)

    return specificDeviceRssi


def hexToBinList(ByteStr, reverse=False):
    """
    INPUTS:
        ByteStr - Byte Arr as string of Hex characters [ex: "312E3147332032342E302E3132"]
        reverse - True will inverse the bits order of each Byte
    OUTPUTS:
        list of strings of characters [0 or 1] representing the bits of Bytes
    """

    try:

        if ByteStr.strip():

            stringLen = len(ByteStr) * 4
            binList = []
            binaryString = str(bin(int(ByteStr, 16)))[2:]
            binaryString = binaryString.zfill(stringLen)

            for i in range(0, stringLen, 8):

                binList.append(binaryString[i:i + 8])

            if reverse:

                for i in range(0, len(binList), 1):

                    binList[i] = binList[i][::-1]

            return binList

    except ValueError, error:

        print(error.message)
        result = '%s That is an invalid hex value.',ByteStr

        return result



class SnifferParser(object):

    def __init__(self):  #, communicationString, ):

        # self.comPort = communicationString
        self.__setupSnifferVariables()

    def __setupSnifferVariables(self):

        # self.setIncludeUnparsedMessage()
        # self.setIncludeParsedMessage()
        self.notApplicableStr = 'NA'
        self.messageReady = False
        self.lastMessageTime = 0
        self.lagBetweenLastMessage = u'  \u1403' + 'ms-0'
        self.index = 0
        self.messageLength = 0
        self.state = 'WAIT_FOR_START'
        self.timeStampKey = 'TimeStamp'
        self.millisecondsKey = 'Milliseconds'
        self.sourceKey = 'Source Device'
        self.destinationKey = 'Destination Device'
        self.generalMessageKey = 'General Message'
        self.messageLengthKey = 'Message Length'
        self.controlKey = 'Control'
        self.opCodeKey = 'OpCode'
        self.parsedDataKey = 'Parsed Data'
        self.rowDataKey = 'Row Data'

        # self.options = {'WAIT_FOR_START': self.wait_for_start,
        #                 'WAIT_FOR_LENGTH': self.wait_for_length,
        #                 'WAIT_FOR_MSG_END': self.wait_for_msg_end,
        #                 'WAIT_FOR_CLOSER': self.wait_for_closer}

        self.messageAfterParser = {self.timeStampKey: '',
                                   self.millisecondsKey: '',
                                   self.sourceKey: '',
                                   self.destinationKey: '',
                                   self.generalMessageKey: '',
                                   self.messageLengthKey: '',
                                   self.controlKey: '',
                                   self.opCodeKey: '',
                                   self.parsedDataKey: '',
                                   self.rowDataKey: ''}

        self.headerListOrder = [self.timeStampKey, self.millisecondsKey, self.sourceKey, self.destinationKey,
                                self.generalMessageKey, self.messageLengthKey, self.controlKey, self.opCodeKey,
                                self.parsedDataKey, self.rowDataKey]
        self.resultDict = {}
        self.gotTamperMsg = False
        self.gotSupvMsg = False
        self.gotConnectedMsg = False
        self.gotTimeOut = False
        self.devTypeId = ''
        self.generalMsg = ''
        self.csvObj = None #ClassCSV(logObj=self.logObj)
        self.generalFilePath = ''
        self.userPath = ''
        self.timeStampAndFileName = ''
        self.filePathChanged = False
        self.serialsFilePath = None # getFilesPath() + "SNIFFER_WSCP_serialFile/serials.csv"
        self.id = 1
        self.deviceHeaderOrder = ['id', 'serial', 'deviceTypeId']
        self.savedDeviceTypeDict = {'id': '', 'serial': '', 'deviceTypeId': ''}
        self.deviceTypeWorkModeFlag = True
        self.savedDevicesTypeListOfDict = [{'id': '', 'serial': '', 'deviceTypeId': ''}]
        self.addDeviceIdToSerials()
        self.readingFlag = False
        self.ackOrMessage = ''
        self.sourceId = ''
        self.identification = 'CROW-RF_SNIFFER'
        self.packetLengthHeader = 'Packet Length'
        self.controlHeader = 'Control'
        self.sourceAddressHeader = 'Source Address'
        self.destinationAddressHeader = 'Dest.  Address'
        self.msgTypeHeader = 'Msg Type'
        self.msgTypeHeaderLength = len(self.msgTypeHeader)
        self.payloadHeader = 'Payload'
        self.hexHeaderStr = '0x'
        self.sourceAddressHeaderLength = len(self.sourceAddressHeader)
        self.destinationAddressHeaderLength = len(self.destinationAddressHeader)

    def payloadParser(self, fullMessage, payloadStr, controlHexID):
        result = 'Empty_payload '
        binId = ''

        try:

            if controlHexID.strip():

                binaryNum = hexToBinList(controlHexID)
                binId = binaryNum[0][::-1]

            else:

                result = 'Empty_control'

        except ValueError, error:

            result = ['That is an invalid control value: ' + str(error)]
            self.PrintError(result)

            return result

        try:

            self.sessionControlCmd, self.opCode, payLoadFirstByte = self.notApplicableStr, self.notApplicableStr, ''

            if payloadStr.strip() and controlHexID.strip():

                if self.generalMsg == 'WP_CROW_BUSS':  # CB = WP_CROW_BUSS

                    if self.devTypeId == '98':  # KPD

                        result = self.parseCrowBusMsgKpd(payloadStr)

                elif len(payloadStr[4:]) > 44:  # Wrong message

                    packet = '*                      ***** Error - RFM !!!*****'
                    result = [packet]
                    # raise Exception

                elif self.generalMsg == 'IO_STAT':  # 9A = IO_STAT

                    if binId[2] == '1':  # Ack

                        result = self.configData(payloadStr)

                    else:  # Message

                        result = self.statusData(payloadStr)

                elif self.generalMsg == 'SUPV':  # 98 = SUPV

                    if binId[2] == '1':

                        result = self.statusData(payloadStr)

                    else:

                        if payloadStr[0:2] != '1E':

                            payLoadFirstByte = 'Wrong_SUPV_period '
                            result = [payLoadFirstByte] + self.configData(payloadStr[2:])

                        else:

                            if payloadStr[0:2] == '1E':
                                payLoadFirstByte = 'SUPV_period_60_sec'

                            result = [payLoadFirstByte] + self.configData(payloadStr[2:])

                elif self.generalMsg == 'OUTPUTS':  # 50 = OUTPUTS

                    if binId[2] == '1':

                        result = self.statusData(payloadStr)

                    else:

                        if payloadStr[0:2] == '00':

                            result = 'Pulses_off'

                        else:

                            result = 'Pulses_ON,Pulses=' + payloadStr[0:2]

                elif self.generalMsg == 'WP_AREA_STATUS':  # 11 = AREA_STATUS

                    if binId[2] == '1':

                        result = self.statusData(payloadStr)

                    else:

                        result = self.configData(payloadStr)

                elif self.generalMsg == 'RESYNC':  # 94 = RESYNC

                    if binId[2] == '1':  # CAMPIR
                        # TODO: full parse INT_SRN type 46 and Type 98
                        if self.devTypeId == '37' or self.devTypeId == '45' or self.devTypeId == '46' or \
                                        self.devTypeId == '57' or self.devTypeId == '98':  # SYNCHRONOUS NODES

                            timeSlot = 'Time_within time slot: ' + str(int(payloadStr[:2], 16)) + ' microseconds'
                            timeSlotNumber = 'Number of time slot assigned: ' + str(int(payloadStr[3], 16))
                            configResult = self.configData(payloadStr)
                            result = [timeSlot, timeSlotNumber] + configResult

                        elif getDeviceType(self.devTypeId)[1] == getAsyncDeviceType(
                                self.devTypeId):  # ASYNCHRONOUS NODES

                            result = self.configData(payloadStr)

                        else:

                            result = str(self.devTypeId) + " is Unknown_dev_type_id"

                    else:

                        device = 'dev_type:' + getDeviceType(payloadStr[:2])[1]
                        hwVersion = 'RFM_SW_VER: ' + str(int(payloadStr[2:4], 16))
                        swVersion = 'RFM_HW_VER: ' + str(int(payloadStr[4:8], 16))
                        result = [device, hwVersion, swVersion]

                        # self.saveDeviceOnResyncMessage(fullMessage)

                elif self.generalMsg == 'COMMAND':  # CD = COMMAND

                    if binId[2] == '1':

                        result = ' Empty_payload'

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

                        self.opCode = opCodeDict[payloadStr[0:2]]
                        sessionPrefix = 'Session_prefix:0x' + payloadStr[2:4]
                        result = [self.opCode, sessionPrefix]

                elif self.generalMsg == 'DATA_STREAM':  # C4 = DATA_STREAM

                    if binId[2] == '1':

                        self.sessionControlCmd = 'ACK - ' + self.__getSessionCtrlCommand(payloadStr[0:2]).replace(' ',
                                                                                                                  '')

                        if self.sessionControlCmd == 'ACK - WP_DS_CLOSE':

                            if int(payloadStr[4:], 16) > 0:

                                packet = '*                      *****Packet error please check chunk resending!!!*****'
                                result = [self.sessionControlCmd, packet]

                            else:

                                packet = '*                      *****Packets was sent successfully!!!*****'
                                result = [self.sessionControlCmd, packet]

                        elif self.sessionControlCmd == 'ACK - WP_DS_ERROR':
                            # todo: check from message '8002' what '02' means..no documentation on WSCP
                            result = [self.sessionControlCmd]

                        else:

                            initDelay = "initDelay:" + str(int(payloadStr[4:6], 16))
                            fileSize = 'File_size:' + str(int(payloadStr[6:10], 16))
                            result = [self.sessionControlCmd, initDelay, fileSize]

                    else:

                        result = self.dataStreamParse(payloadStr)

                elif len(payloadStr[4:]) > 44:

                    packet = '*                      ***** Error - RFM !!!*****'
                    result = [self.sessionControlCmd, packet]

                else:

                    result = ['          ****** %s send by the accessory  *****' % self.generalMsg]

        except ValueError:

            result = '*                      **** System error: PAYLOAD LENGTH ERROR! **** fullMessage->' + fullMessage

            return result

        return result


    def saveDeviceOnResyncMessage(self, hexString):
        if self.generalMsg == 'RESYNC' and self.ackOrMessage == 'MSG':

            deviceType = hexString[18:20]
            serial = self.sourceId
            serialLen = self.sourceId.split(':')

            if len(serialLen) == 2:
                serial = serialLen[1]

            emptyString = ''

            if not serial.strip() == emptyString or not deviceType.strip() == emptyString:
                self.addDeviceIdToSerials(serial, deviceType)


    def deleteDeviceIdFromSerialsFile(self, serial, deviceType):
        self.savedDevicesTypeListOfDict = self.csvObj.readListDictFromCSV(self.serialsFilePath)
        isIdDeleted = False
        savedDevicesLength = len(self.savedDevicesTypeListOfDict)

        for index in range(savedDevicesLength):

            if not isIdDeleted and self.savedDevicesTypeListOfDict[index]['serial'] == serial and \
                            self.savedDevicesTypeListOfDict[index]['deviceTypeId'] == deviceType:  # serial found

                self.savedDevicesTypeListOfDict.pop(index)
                newSavedDeviceLength = savedDevicesLength - 1

                for newIndex in range(index, newSavedDeviceLength):  # update new serial id's

                    self.savedDevicesTypeListOfDict[newIndex]['id'] = str(newIndex + 1)

                for index in range(newSavedDeviceLength):  # write new serials dict list

                    if index == 0:

                        self.csvObj.replaceDictInFile(self.serialsFilePath, self.savedDevicesTypeListOfDict[index])

                    else:

                        self.csvObj.writeDictToCSV(self.serialsFilePath, self.savedDevicesTypeListOfDict[index])

                break  # deleted & updated


    def addDeviceIdToSerials(self, serial=None, deviceType=None):
        try:

            # self.savedDevicesTypeListOfDict = self.csvObj.readListDictFromCSV(self.serialsFilePath)
            pass

        except IOError:

            firstId = '1'
            defaultDeviceDict = {'id': firstId, 'serial': serial, 'deviceTypeId': deviceType}
            self.csvObj.createFileWithHeader(self.serialsFilePath, self.deviceHeaderOrder)
            self.savedDeviceTypeDict.update(defaultDeviceDict)
            self.savedDevicesTypeListOfDict = [defaultDeviceDict]
            self.csvObj.saveToCsvFile(self.serialsFilePath, self.savedDeviceTypeDict)

        # self.__loadSavedSerials(serial, deviceType)


    def __loadSavedSerials(self, serial, deviceType):
        hasItem = False
        lastIdInFile = None
        maximumSavedSerial = 70

        if serial is not None:
            serial = serial.zfill(7)

        if self.savedDevicesTypeListOfDict is not None:

            for device in self.savedDevicesTypeListOfDict:

                if device['serial'] == serial:
                    hasItem = True
                    break

                lastIdInFile = int(device['id'])

                if self.id <= lastIdInFile:
                    self.id += 1

        if not hasItem and lastIdInFile is not None and deviceType is not None:

            if not self.id > maximumSavedSerial:

                currentSaveIdIndex = str(self.id)
                newDeviceDict = {'id': currentSaveIdIndex, 'serial': serial, 'deviceTypeId': deviceType}
                self.savedDeviceTypeDict.update(newDeviceDict)
                self.csvObj.saveToCsvFile(self.serialsFilePath, self.savedDeviceTypeDict)
                self.savedDevicesTypeListOfDict.append(newDeviceDict)
                self.id += 1

            else:

                currentSaveIdIndex = str(maximumSavedSerial)
                newDeviceDict = {'id': currentSaveIdIndex, 'serial': serial, 'deviceTypeId': deviceType}

                for index in range(len(self.savedDevicesTypeListOfDict)):
                    self.savedDevicesTypeListOfDict[index].update(
                        {'id': str(int(self.savedDevicesTypeListOfDict[index]['id']) - 1)})

                self.savedDevicesTypeListOfDict.pop(0)  # pop first old index
                self.csvObj.replaceDictInFile(self.serialsFilePath,
                                              self.savedDevicesTypeListOfDict[0])  # add shifted item
                self.savedDevicesTypeListOfDict.append(newDeviceDict)

                for index in range(len(self.savedDevicesTypeListOfDict)):

                    if index != 0:
                        self.csvObj.writeDictToCSV(self.serialsFilePath, self.savedDevicesTypeListOfDict[index])


    def statusData(self, payLoadStr):  # Appendix c

        if payLoadStr.strip():

            inverseBitList = []
            binaryNumber = hexToBinList(payLoadStr)
            secondByteBinRssi = 'Empty_byte_was_sent'
            emptyList = ['Empty_byte']
            index = 1
            rssiOffset = 71

            for Byte in binaryNumber:
                inverseBitList.append(Byte[::-1])

            if len(inverseBitList) > index:
                rssiOffset = 71
                rssiRegisterStatus = payLoadStr[2:4]
                secondByteBinRssi = ['RSSI: ' + getDeviceRssi(rssiRegisterStatus, rssiOffset)]

            if len(inverseBitList) < 4:
                inverseBitList = inverseBitList + emptyList * (4 - len(inverseBitList))

            if self.devTypeId == '31' or self.devTypeId == '34' or self.devTypeId == '37':  # PIR|SMK|CAM

                result = self.statusDataPirSmkCam(inverseBitList[0]) + secondByteBinRssi

            elif self.devTypeId == '3C' or self.devTypeId == '32':  # TFM|MAG

                result = self.statusDataTfmMag(inverseBitList[0], inverseBitList[3]) + secondByteBinRssi

            elif self.devTypeId == '45' or self.devTypeId == '46' or self.devTypeId == '57':  # SRN

                result = self.statusDataSrn(inverseBitList[0], inverseBitList[1], payLoadStr[4:5])

            elif self.devTypeId == '98':
                # todo:check the correct rssi offset
                rssiRegisterStatus = payLoadStr[2:4]
                thirdByteBinRSSi = 'RSSI: ' + getDeviceRssi(rssiRegisterStatus, rssiOffset)
                result = thirdByteBinRSSi

            elif self.devTypeId == '36':
                # todo:check the correct rssi offset#GBD
                thirdByteBinRSSi = 'RSSI: ' + getDeviceRssi(payLoadStr[4:6], rssiOffset)
                result = thirdByteBinRSSi

            elif self.devTypeId == '33':  # '33': 'RMT/PANIC'
                # todo: fix this part because RMT&PANIC have the same devType, need to be a Distinguish between the detectors?
                if inverseBitList[0][6] == '0':

                    panic = 'Panic_on'

                else:

                    panic = 'Panic_off'

                if inverseBitList[0][7] == '0':

                    trouble = 'Trouble'

                else:

                    trouble = 'No_trouble'

                if inverseBitList[0][4] == '0':

                    battery = 'Battery_low'

                else:

                    battery = 'Battery_ok'

                if inverseBitList[0][0] == '0':

                    Key1Disarm = 'Key1_Disarm_released'

                else:

                    Key1Disarm = 'Key1_Disarm_pressed'

                if inverseBitList[0][1] == '0':

                    Key2Arm = 'Key2_Arm_released'

                else:

                    Key2Arm = 'Key2_Arm_pressed'

                if inverseBitList[0][2] == '0':

                    Key3StayArm = 'Key3_StayArm_released'

                else:

                    Key3StayArm = 'Key3_StayArm_pressed'

                if inverseBitList[0][3] == '0':

                    Key4Output = 'Key4_Output_released'

                else:

                    Key4Output = 'Key4_Output_pressed'

                detector = [battery, trouble, panic, Key1Disarm, Key2Arm, Key3StayArm, Key4Output]
                result = detector

            else:

                result = str(self.devTypeId) + " unknown dev_type_id"

        else:

            result = ' Empty_payload '

        return result


    def statusDataPirSmkCam(self, firstByteBinId):
        if firstByteBinId[0] == '0':

            superVision = 'SUPV'

        else:

            superVision = 'No_SUPV'

        if firstByteBinId[2] == '0':

            alarm = 'Alarm'

        else:

            alarm = 'No_alarm'

        if firstByteBinId[3] == '0':

            pictRdy = 'Pict_Rdy'

        else:

            pictRdy = 'No_pic'

        if firstByteBinId[4] == '0':

            battery = 'Battery_low'

        else:

            battery = 'Battery_ok'

        if firstByteBinId[5] == '0' and firstByteBinId[6] == '0':

            masking = 'Masking'

        else:

            masking = 'No Masking'

        if firstByteBinId[6] == '0':

            tamper = 'Tamper_open'

        else:

            tamper = 'Tamper_close'

        if firstByteBinId[7] == '0':

            trouble = 'Trouble'

        else:

            trouble = 'No_trouble'

        pirDetector = [superVision, alarm, self.notApplicableStr, battery, masking, tamper, trouble]
        smkDetector = [superVision, alarm, self.notApplicableStr, battery, tamper, trouble]
        camDetector = [superVision, alarm, pictRdy, battery, tamper, trouble]

        if self.devTypeId == '31':

            result = pirDetector

        elif self.devTypeId == '34':

            result = smkDetector

        elif self.devTypeId == '37':

            result = camDetector

        else:

            result = str(self.devTypeId) + " is unknown dev_type_id"

        return result


    def statusDataTfmMag(self, firstByteBinId, fourthByteBin):
        if firstByteBinId[0] == '0':

            superVision = 'SUPV'

        else:

            superVision = 'NO_SUPV'

        if firstByteBinId[2] == '0':

            alarm = 'Alarm'

        else:

            alarm = 'NO_Alarm'

        if firstByteBinId[3] == '0':

            alarm2 = 'Alarm2'

        else:

            alarm2 = 'NO_Alarm2'

        if firstByteBinId[4] == '0':

            battery = 'Battery_low'

        else:

            battery = 'Battery_ok'

        if firstByteBinId[6] == '0':

            tamper = 'Tamper_open'

        else:

            tamper = 'Tamper_close'

        if firstByteBinId[7] == '0':

            trouble = 'Trouble'

        else:

            trouble = 'NO_trouble'

        result = [superVision, alarm, alarm2, battery, tamper, trouble]

        if self.devTypeId == '3C':  # TFM

            externalTemperature = 'Temperature: ' + fourthByteBin
            result = result + [externalTemperature]

        return result


    def statusDataSrn(self, firstByteBinId, secondByteBinId, rSSIHexValue):
        if firstByteBinId[4] == '0':

            battery = 'Battery_low'

        else:

            battery = 'Battery_ok'

        if firstByteBinId[6] == '0':

            tamper = 'Tamper_open'

        else:

            tamper = 'Tamper_close'

        if firstByteBinId[7] == '0':

            trouble = 'Trouble'

        else:

            trouble = 'NO_trouble'

        if secondByteBinId[0] == '0':

            flasher = 'Flash_on'

        else:

            flasher = 'Flash_off'

        if secondByteBinId[1] == '0':

            sounder = 'Sound_on'

        else:

            sounder = 'Sound-off'

        # todo:check the correct rssi offset
        rssiOffset = 71
        rssi = 'RSSI: ' + getDeviceRssi(rSSIHexValue, rssiOffset)
        result = [battery, tamper, trouble, flasher, sounder, rssi]

        return result


    def configData(self, payLoadStr):
        if payLoadStr.strip():

            binaryNumber = hexToBinList(payLoadStr)
            # BitList = []
            inversBitList = []
            result = []
            emptylist = ['Empty_byte']

            # for Byte in binaryNumber:
            #    BitList.append(Byte)

            for Byte in binaryNumber:
                inversBitList.append(Byte[::-1])

            if len(inversBitList) < 4:  # initialize empty byte list

                inversBitList = inversBitList + emptylist * (4 - len(inversBitList))

            if self.devTypeId == '31' or self.devTypeId == '32' or self.devTypeId == '34' or self.devTypeId == '3C':  # PIR|MAG|SMK|TFM

                result = self.configDataPirMagSmkTfm(inversBitList[0], inversBitList[1])

            elif self.devTypeId == '45' or self.devTypeId == '46' or self.devTypeId == '57':  # SRN

                result = self.configDataSrn(inversBitList[0], inversBitList[1])

            elif self.devTypeId == '98':  # Keypad

                result = self.configDataKPD(payLoadStr)

            elif self.devTypeId == '57':  # Output

                result = self.configDataOutput(inversBitList[0], inversBitList[1], inversBitList[2], inversBitList[3])

            elif self.devTypeId == '36':  # GBD

                result = self.configDataGbd(inversBitList[0], inversBitList[1])

            elif self.devTypeId == '37':  # CAMPIR

                if self.generalMsg == 'WP_AREA_STATUS':

                    result = self.configDataCamPir(inversBitList[1], inversBitList[0], inversBitList[2],
                                                   inversBitList[3])

                else:

                    result = self.configDataCamPir(inversBitList[0], inversBitList[1], inversBitList[2],
                                                   inversBitList[3])

        else:

            result = [' Empty_payload ']

        return result


    def configDataPirMagSmkTfm(self, firstByteBinId, secondByteBinId):
        # timeDict = {'000': '7_min',
        #            '001': '1_min',
        #            '010': '2_min',
        #            '011': '4_min',
        #            '100': '10_min',
        #            '101': '15_min',
        #            '110': '20_min',
        #            '111': '30_min'}

        timeDict = {'000': '7_min',
                    '100': '1_min',
                    '010': '2_min',
                    '110': '4_min',
                    '001': '10_min',
                    '101': '15_min',
                    '011': '20_min',
                    '111': '30_min'}

        pulsesDict = {'00': '1_pulse',
                      '10': '2_pulse',
                      '01': '3_pulse',
                      '11': '1_pulse_No_filtering'}

        extTfmDict = {'00': 'Ext_disabled',
                      '01': 'Ext_reed_SW_enabled',
                      '10': 'Ext_temp_probe_enabled',
                      '11': 'Ext_flood_probe_enabled'}

        time = ''
        externalTfm = ''
        pulses = ''

        if firstByteBinId != 'Empty_byte':
            time = "TX:" + timeDict[firstByteBinId[1:4]]

        if secondByteBinId != 'Empty_byte':
            externalTfm = 'ext_Tfm:' + extTfmDict[secondByteBinId[4:6]]
            pulses = pulsesDict[secondByteBinId[4:6]]

        if firstByteBinId[4] == '1':

            mute = 'Mute_on'

        else:

            mute = 'Mute_off'

        if firstByteBinId[5] == '1':

            indication = 'Indication_active'

        else:

            indication = 'No_indication'

        if firstByteBinId[6] == '1':

            walkTest = 'Walk_test_active'

        else:

            walkTest = 'No_walk_test'

        if firstByteBinId[7] == '1':

            armed = 'Armed'

        else:

            armed = 'Not_armed'

        gainControl = int(secondByteBinId[::-1][5:], 2)

        if gainControl > 4:

            gainControl = 'Wrong_gain_ctrl-->' + str(gainControl)

        else:

            gainControl = 'Gain_ctrl:' + 'Level_' + str(gainControl)

        if secondByteBinId[3] == '1':  # HPF-high pass filter cutoff freq

            hpf = 'HPF_on'

        else:

            hpf = 'HPF_off'

        if secondByteBinId[6] == '1':

            localConfig = 'Device_config'

        else:

            localConfig = 'Host_config'

        if secondByteBinId[7] == '1':

            stayArmed = 'Stay_armed'

        else:

            stayArmed = 'Not_stay_armed'

        if secondByteBinId[1] == '1':

            externalMag = 'Ext_mag_enable'

        else:

            externalMag = 'Ext_mag_disable'

        if secondByteBinId[2] == '1':

            internalMag = 'Int_mag_enable'

        else:

            internalMag = 'Int_mag_disable'

        if secondByteBinId[0] == '1':

            sensorsDetects = 'Logic<AND>'

        else:

            sensorsDetects = 'Logic<OR>'

        if secondByteBinId[1] == '1':

            heat = 'Heat_on'

        else:

            heat = 'Heat_off'

        if secondByteBinId[2] == '1':

            smoke = 'Smoke_on'

        else:

            smoke = 'Smoke_on'

        result = [time, mute, indication, walkTest, armed]
        pirDetector = result + [gainControl, hpf, pulses, localConfig, stayArmed]
        magDetector = result + [sensorsDetects, externalMag, internalMag, localConfig, stayArmed]
        smkDetector = result + [sensorsDetects, heat, smoke, localConfig, stayArmed]
        tfmDetector = result + [sensorsDetects, internalMag, externalTfm, localConfig, stayArmed]

        if self.devTypeId == '31':

            result = pirDetector

        elif self.devTypeId == '32':

            result = magDetector

        elif self.devTypeId == '34':

            result = smkDetector

        elif self.devTypeId == '3C':

            result = tfmDetector

        else:

            result = str(self.devTypeId) + " is unknown_dev_type_id"

        return result


    def configDataSrn(self, firstByteBinId, secondByteBinId):
        ledTimeOutDict = {'00': 'Equals_Sound',
                          '01': 'Sound_timeout+5 min',
                          '10': 'Sound_timeout+15 min',
                          '11': 'No_timeout'}

        sounderLoudnessDict = {'00': 'level_1',
                               '01': 'level_2',
                               '10': 'level_3',
                               '11': 'level_4'}

        sounderActivaionTimeOutDict = {'00': '1_min',
                                       '01': '2_min',
                                       '10': '10_min',
                                       '11': '15_min'}

        ledTimeOut = ''
        souderLoudness = ''
        souderActivationTimeOut = ''

        if firstByteBinId != 'Empty_byte':
            ledTimeOut = 'Led_timeOut:' + ledTimeOutDict[firstByteBinId[0:2]]
            souderLoudness = 'Sound_loudness:' + sounderLoudnessDict[firstByteBinId[2:4]]
            souderActivationTimeOut = 'Sound_activaion_timeOut:' + sounderActivaionTimeOutDict[firstByteBinId[4:6]]

        if secondByteBinId[0] == '0':

            sounderOnMode = 'Sound_on_mode_disable'

        else:

            sounderOnMode = 'Sound_on_mode_disable'

        if secondByteBinId[1] == '0':

            sounderArmDisarm = 'Sound_arm/disarm_off'

        else:

            sounderArmDisarm = 'Sound_arm/disarm_on'

        if secondByteBinId[2] == '0':

            ledOnMode = 'Led_on_mode_disable'

        else:

            ledOnMode = 'Led_off_mode_enable'

        if secondByteBinId[3] == '0':

            ledArmDisarm = 'Led_arm/disarm_off'

        else:

            ledArmDisarm = 'Led_arm/disarm_on'

        if secondByteBinId[5] == '0':

            flashLeds = 'leds_disable'

        else:

            flashLeds = 'leds_enable'

        if secondByteBinId[6] == '0':

            systemStat = 'Sys_normal_stat'

        else:

            systemStat = 'Sys_WalkTest_stat'

        if secondByteBinId[6] == '0':

            systemActiveStat = 'Sys_in_stand_by_stat'

        else:

            systemActiveStat = 'Sys_in_active_stat'

        result = [ledTimeOut, souderLoudness, souderActivationTimeOut, sounderOnMode
            , sounderArmDisarm, ledOnMode, ledArmDisarm, flashLeds, systemStat, systemActiveStat]

        if firstByteBinId[6] == '1':

            factoryDefaultConfig = 'Reset_to_factory_default'

            result = result + [factoryDefaultConfig]

        else:

            result = result

        return result


    def configDataKPD(self, payload):
        result = []

        if self.generalMsg == 'SUPV':

            if payload[0:]:
                configSessionCounter = 'Config_counter: ' + payload[0:]
                result.append(configSessionCounter)

            if payload[7] == '1':
                supervision = 'Power up supervision'
                result.append(supervision)

        if self.generalMsg == 'RESYNC':

            if payload[4:6]:
                kpdIndex = 'Number of KPD index: ' + str(int(payload[4:6], 16))
                result.append(kpdIndex)

            if payload[6:8]:
                numberOfSentConfiguration = 'Number of sent CFG: ' + str(int(payload[6:8], 16))
                result.append(numberOfSentConfiguration)

        return result


    def configDataOutput(self, firstByteBinId, secondByteBinId, thirdByteBinId, fourthByteBinId):
        activationTimeoutDict = {'000': 'No_timeout',
                                 '001': '1_min',
                                 '010': '2_min',
                                 '011': '10_min',
                                 '100': '15_min',
                                 '101': '30_min',
                                 '110': '45_min',
                                 '111': '60_min'}

        systemStateDict = {'00': 'Disarm_state',
                           '01': 'Walk_test_state',
                           '10': 'Arm_state',
                           '11': 'NOT_SUPPORTED'}

        result = []

        if firstByteBinId != 'Empty_byte':
            activationTimeout = 'Activation_timeout:' + activationTimeoutDict[firstByteBinId[3:6]]
            result.append(activationTimeout)

        if firstByteBinId[6] == '0':

            maintenanceMode = 'Maintenance_mode_disable'

        else:

            maintenanceMode = 'Maintenance_mode_enable'

        if secondByteBinId[5] == '0':

            led = 'Leds_disable'

        else:

            led = 'Leds_enable'

        if secondByteBinId != 'Empty_byte':
            systemState = systemStateDict[secondByteBinId[6:]]
            result.append(systemState)

        if thirdByteBinId[0:] != 'Empty_byte':

            pulseOnTime = 'Pulse_on=' + str(int(thirdByteBinId[0:], 2) * 0.1) + ' sec'

        else:

            pulseOnTime = 'No_pulse_on_time'

        if fourthByteBinId[0:] != 'Empty_byte':

            pulseOffTime = 'Pulse_off:' + str(int(fourthByteBinId[0:], 2) * 0.1) + ' sec'

        else:

            pulseOffTime = 'No_pulse_off_time'

        result.append(maintenanceMode)
        result.append(led)
        result.append(pulseOnTime)
        result.append(pulseOffTime)

        return result


    def configDataGbd(self, firstByteBinId, secondByteBinId):
        sensitivityDict = {'00': 'Disable',
                           '01': 'Low_sensitivity',
                           '10': 'Mid_sensitivity',
                           '11': 'High_sensitivity'}

        gbdSensorAutoGainCtrlDict = {'00': '0% ',
                                     '01': '25%',
                                     '10': '50%(default)',
                                     '11': '75%'}

        supervisiontimeDict = {'000': '7_min',
                               '001': '1_min',
                               '010': '2_min',
                               '011': '4_min',
                               '100': '10_min',
                               '101': '15_min',
                               '110': '20_min',
                               '111': '30_min'}

        systemStateDict = {'00': 'Disarm_state',
                           '01': 'Walk_test_state',
                           '10': 'Arm_state',
                           '11': 'Not_supported'}

        result = []

        if firstByteBinId != 'Empty_byte':
            gbdSensorl = 'GBD_sensor:' + sensitivityDict[firstByteBinId[1:3]]
            result.append(gbdSensorl)
            gbdSensorAutoGainCtrl = 'GBD_sensor_auto_gain_ctrl:' + gbdSensorAutoGainCtrlDict[firstByteBinId[3:5]]
            result.append(gbdSensorAutoGainCtrl)
            fallSensor = 'Fall_sensor' + sensitivityDict[firstByteBinId[5:7]]
            result.append(fallSensor)

        if firstByteBinId != 'Empty_byte' and secondByteBinId != 'Empty_byte':
            vibrationSensor = 'Vibration_sensor:' + sensitivityDict[firstByteBinId[7] + secondByteBinId[0]]
            result.append(vibrationSensor)

        if firstByteBinId[0] == '0':

            sensorsDetectionLogic = 'Sensors_Logic=OR'

        else:

            sensorsDetectionLogic = 'Sensors_Logic=AND'

        result.append(sensorsDetectionLogic)

        if secondByteBinId != 'Empty_byte':
            supervision = 'SUPV:' + supervisiontimeDict[secondByteBinId[1:4]]
            result.append(supervision)
            systemState = systemStateDict[secondByteBinId[6:]]
            result.append(systemState)

        if secondByteBinId[4] == '0':

            mute = 'Mute_enabled'

        else:

            mute = 'Mute_disabled'

        if secondByteBinId[5] == '0':

            leds = 'Leds_disabled'

        else:

            leds = 'Leds_enabled'

        result.append(mute)
        result.append(leds)

        return result


    def configDataCamPir(self, firstByteBinId, secondByteBinId, thirdByteBinId, fourthByteBinId):
        pulsesDict = {'00': '1_pulse',
                      '01': '2_pulse',
                      '10': '3_pulse',
                      '11': '1_pulse_No_filtering'}

        numOfPicInOneSetDict = {'000': '1_Pic',
                                '001': '2_Pic',
                                '010': '3_Pic',
                                '011': '4_Pic',
                                '100': '5_Pic',
                                '101': 'Wrong_number_of_pic_config',
                                '110': 'Wrong_number_of_pic_config',
                                '111': 'Wrong_number_of_pic_config',}

        systemStateDict = {'00': 'Disarm_state',
                           '01': 'Walk_test_state',
                           '10': 'Arm_state',
                           '11': 'Not_supported'}

        pictureColorAndResolutionDict = {'00': 'QVGA B&W(320x240)',
                                         '01': 'VGA B&W(640x480)',
                                         '10': 'QVGA Color(320x240)',
                                         '11': 'VGA Color(640x480)'}

        pictureRateDict = {'000': '0.3_sec',
                           '001': '0.5_sec',
                           '010': '1_sec',
                           '011': '1.4_sec',
                           '100': '2_sec',
                           '101': '5_sec(regular mode JPEG only)',
                           '110': '15_sec(regular mode JPEG only)',
                           '111': '30_sec(regular mode JPEG only)'}

        holdOffTimeDict = {'000': '30_sec',
                           '001': '45_sec',
                           '010': '60_sec',
                           '011': '75_sec',
                           '100': '90_sec',
                           '101': '105_sec',
                           '110': '120_sec',
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

        if firstByteBinId != 'Empty_byte':
            firstByteBinId = firstByteBinId[::-1]
            systemState = systemStateDict[firstByteBinId[0:2]]
            result.append(systemState)
            numOfPicInOneSet = numOfPicInOneSetDict[firstByteBinId[5:8]]
            result.append(numOfPicInOneSet)

        if thirdByteBinId != 'Empty_byte':
            thirdByteBinId = thirdByteBinId[::-1]
            holdOffTime = 'Hold_off:' + holdOffTimeDict[thirdByteBinId[0:3]]
            result.append(holdOffTime)
            pictureRate = 'Pic_rate:' + pictureRateDict[thirdByteBinId[3:6]]
            result.append(pictureRate)
            pictureColorAndResolution = pictureColorAndResolutionDict[thirdByteBinId[6:8]]
            result.append(pictureColorAndResolution)

        if fourthByteBinId != 'Empty_byte':
            fourthByteBinId = fourthByteBinId[::-1]
            pictureQuality = 'Pic_quality' + pictureQualityDict[fourthByteBinId[0:3]]
            result.append(pictureQuality)

        if secondByteBinId != 'Empty_byte':

            gainControl = int(secondByteBinId[5:8], 2)

            if gainControl > 4:

                gainControl = 'Wrong_Gain_ctrl-->' + str(gainControl)

            else:

                gainControl = 'Gain_Ctrl: ' + 'Level_' + str(gainControl)

            result.append(gainControl)

        if secondByteBinId[4] == '0':

            petImmuneFilter = 'PetImmune:Disabled'

        else:

            petImmuneFilter = 'PetImmune:Enabled'

        if secondByteBinId[0] == '0':

            camEnabling = 'CAM:Disable'

        else:

            camEnabling = 'CAM:Enable'

        if firstByteBinId[3] == '0':

            mute = 'Mute_disabled'

        else:

            mute = 'Mute_enabled'

        if firstByteBinId[2] == '0':

            leds = "Leds_disabled"

        else:

            leds = "Leds_enabled"

        if fourthByteBinId[7] == '0':

            diffJpeg = 'Diff_JPEG_low'

        else:

            diffJpeg = 'Diff_JPEG_high'

        if fourthByteBinId[6] == '0':

            jpegMode = 'Regular_JPEG'

        else:

            jpegMode = 'Differential_JPEG'

        if fourthByteBinId[5] == '0':

            contrastEnhancement = 'Contrast_disable'

        else:

            contrastEnhancement = 'Contrast_enable(auto)'

        if fourthByteBinId[4] == '0':

            sharpnessEnhancement = 'Sharpness_disable'

        else:

            sharpnessEnhancement = 'Sharpness_enable'

        result.append(petImmuneFilter)
        result.append(camEnabling)
        result.append(mute)
        result.append(leds)
        result.append(diffJpeg)
        result.append(jpegMode)
        result.append(contrastEnhancement)
        result.append(sharpnessEnhancement)

        return result


    def dataStreamParse(self, payloadStr):
        result = []

        if payloadStr[:4]:
            self.sessionControlCmd = self.__getSessionCtrlCommand(payloadStr[0:2])
            sessionIndication = payloadStr[2:4]
            result.append('Chunk prefix:0x' + sessionIndication)

        if self.devTypeId == '37':  # CAM

            if payloadStr[8:10]:
                pictureTransfer = 'Pic_transfer:' + str(int(payloadStr[8:10], 16))
                result.append(pictureTransfer)

            if payloadStr[10:12]:
                pictureNumber = 'Pic_number:' + str(int(payloadStr[10:12], 16))
                result.append(pictureNumber)

        if payloadStr[4:8]:
            res = payloadStr[6:8] + payloadStr[4:6]
            fileSize = 'File_size:' + str(int(res, 16))
            result.append(fileSize)

        if self.sessionControlCmd == 'WP_DS_INIT':

            if self.devTypeId == '37':

                fileCrc = 'File_CRC:' + payloadStr[14:18]

                if payloadStr[12:14] == '00' and payloadStr[12:14]:

                    triggerSource = 'Trigger_source_from_alarm'

                else:

                    triggerSource = 'Trigger_source_from_take_command'

                result.append(triggerSource)

            else:  # '98' = KPD

                fileCrc = 'File_CRC: ' + payloadStr[20:]
                structureNumber = 'Structure number: ' + payloadStr[8:10]
                serenityStructureOffset = payloadStr[12:14] + payloadStr[10:12]
                serenityStructureOffset = 'Offset in serenity structure: ' + serenityStructureOffset
                result.append(structureNumber)
                result.append(serenityStructureOffset)

            result.append(fileCrc)

        if len(payloadStr[4:]) > 44:  # Bigger then length of normal message

            error = '*                      ***** Error - RFM - (to many bytes) !!!*****'
            result.append(error)

        result = [self.sessionControlCmd] + result

        return result


    def parseCrowBusMsgKpd(self, payloadStr):
        result = []

        if len(payloadStr) > 56:

            if payloadStr == '310384002C000000000022000000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000':

                isError = 'KPD status ok'

            else:

                isError = '*                      ***** Error - RFM !!!*****'

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
            dateTimeUpdated = 'Date & time updated: ' + day + ' ' + date + ' ' + time

            result = dateTimeUpdated

        if payloadStr[0:2] == '09':

            structureIndex = 'KPD structure index: ' + payloadStr[2:4]
            structureOffset = 'Offset in serenity structure: ' + payloadStr[6:8] + payloadStr[4:6]

            if payloadStr[12:]:

                sentBit = payloadStr[12:]

            else:

                sentBit = 'None'

            if payloadStr[8:12] == 'FFFF':

                bit = 'sent Reset bit ' + sentBit

            else:

                bit = 'sent Set bit: ' + sentBit

            result = [structureIndex, structureOffset, bit]

        return result


    def __getGeneralMsgType(self, generalMsgHexString):
        generalMsgDict = {'94': 'RESYNC',
                          '98': 'SUPV',
                          '50': 'OUTPUTS',
                          '11': 'WP_AREA_STATUS',
                          '9A': 'IO_STAT',
                          'C4': 'DATA_STREAM',
                          'CD': 'COMMAND',
                          'CB': 'WP_CROW_BUSS'}

        if generalMsgHexString in generalMsgDict.keys():

            generalMsgName = generalMsgDict[generalMsgHexString]

        else:

            generalMsgName = 'General_msg: %s is NA' % generalMsgHexString

        return generalMsgName


    def __getSessionCtrlCommand(self, sessionControlCmdId):
        sessionCtrlCommandDict = {'01': 'WP_DS_INIT',
                                  '02': 'WP_DS_OPEN',
                                  '04': 'WP_DS_SUSPENDED',
                                  '08': 'WP_DS_RESUME',
                                  '10': 'WP_DS_CLOSE',
                                  '20': 'WP_DS_DRATE',
                                  '80': 'WP_DS_ERROR'}

        if sessionCtrlCommandDict.has_key(sessionControlCmdId):

            result = sessionCtrlCommandDict[sessionControlCmdId]

        else:

            result = 'SessionControlCmdId:%s is NA' % sessionControlCmdId

        return result


    def controlParser(self, hexString):
        result = []
        self.ackOrMessage = "MSG"
        oneWayMsg = "2_way_accessory"


        try:

            binaryNum = hexToBinList(hexString)
            binId = binaryNum[0][::-1]
            sequenceNumber = "Seq:" + str(int(binId[0:2], 2))
            result.append(sequenceNumber)

        except ValueError, error:

            # self.PrintError(error.message)
            # self.PrintError(self.message)
            result = '%s That is an invalid hex value for control part.' % hexString

            return result

        except Exception, error:

            # self.PrintError(error.message)
            # self.PrintError(self.message)
            result = '%s That is an invalid hex value for control part.' % hexString

            return result

        if binId[2] == '1':
            self.ackOrMessage = "ACK"

        if binId[6] == '1':
            oneWayMsg = "1_way_accessory"

        result.append(self.ackOrMessage)
        result.append(oneWayMsg)

        return str(result)

    def my_control_parser(self, ctl_num):
        ctl_bin = bin(ctl_num)[2:].zfill(8)
        ctl_bin_rev = ctl_bin[::-1]
        ctl_num_rev = int(ctl_bin_rev, 2)
        mask_seq = 0b11000000
        seq = (ctl_num_rev & mask_seq) >> 6

        mask_ack = 0b00100000
        ack = "ack" if (ctl_num_rev & mask_ack) >> 5 == 1 else "msg"

        mask_one_way = 0b00000010
        one_way = "one_way" if (ctl_num_rev & mask_one_way) >> 1 == 1 else "two_way"

        res = {"seq": seq, "ack-msg": ack, "way": one_way}
        # print "s_j:", s_j
        # res = json.loads(s_j)
        print res
        return res



def main():
    sn = SnifferParser()

    idx = 4
    time_start = time.time()
    # for idx in xrange(56, 66):
    res = sn.controlParser(hex(idx)[2:])
    print res
    print 'Elapsed 1: {}'.format(time.time() - time_start)


    time_start = time.time()
    # for idx in xrange(56, 66):
    res2 = sn.my_control_parser(idx)
    print 'Elapsed 2: {}'.format(time.time() - time_start)


if __name__ == '__main__':
    main()
