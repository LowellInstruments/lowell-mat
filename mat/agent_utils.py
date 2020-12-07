AG_BLE_CMD_STATUS = 'status'
AG_BLE_CMD_CONNECT = 'connect'
AG_BLE_CMD_DISCONNECT = 'disconnect'
AG_BLE_CMD_GET_TIME = 'get_time'
AG_BLE_CMD_SET_TIME = 'set_time'
AG_BLE_CMD_GET_FW_VER = 'get_fw_ver'
AG_BLE_CMD_LS_LID = 'ls_lid'
AG_BLE_CMD_LS_NOT_LID = 'ls_not_lid'
AG_BLE_CMD_STOP = 'stop'
AG_BLE_CMD_GET_FILE = 'get_file'
AG_BLE_CMD_BYE = 'bye!'
AG_BLE_CMD_QUERY = 'query'
AG_BLE_CMD_SCAN = 'scan'
AG_BLE_CMD_SCAN_LI = 'scan_li'
AG_BLE_ANS_CONN_ALREADY = 'already connected'
AG_BLE_ANS_CONN_OK = 'connected'
AG_BLE_ANS_CONN_PROGRESS = 'connecting'
AG_BLE_ANS_CONN_ERR = 'connection fail'
AG_BLE_ANS_DISC_ALREADY = 'was not connected'
AG_BLE_ANS_DISC_OK = 'disconnected'
AG_BLE_ANS_STOP_OK = 'stopped'
AG_BLE_ANS_STOP_ERR = 'not stopped, error'
AG_BLE_ANS_BYE = 'bye you from ble'
AG_BLE_ERR = 'ERR'
AG_BLE_EMPTY = 'empty'
AG_BLE_CMD_RLI = 'rli'
AG_BLE_CMD_RHS = 'rhs'
AG_BLE_CMD_FORMAT = 'format'
AG_BLE_CMD_EBR = 'ebr'
AG_BLE_CMD_MBL = 'mbl'
AG_BLE_CMD_LOG_TOGGLE = 'log'
AG_BLE_CMD_GSR = 'gsr'
AG_BLE_CMD_GSR_DO = 'gsr_do'
AG_BLE_CMD_RESET = 'reset'
AG_BLE_CMD_UPTIME = 'uptime'
AG_BLE_CMD_CFS = 'free_space'
AG_BLE_CMD_RFN = 'rfn'
AG_BLE_CMD_MTS = 'mts'


AG_N2LH_CMD_BYE = 'bye!'
AG_N2LH_PATH_BLE = 'ble'
AG_N2LH_PATH_GPS = 'gps'

AG_N2LL_CMD_BYE = 'bye!'
AG_N2LL_CMD_WHO = 'who'
AG_N2LL_CMD_QUERY = 'query'
AG_N2LL_CMD_ROUTE_NX = 'route_nx'
AG_N2LL_CMD_ROUTE_AGENT = 'route_agent'
AG_N2LL_CMD_ROUTE_KILL = 'kill'
AG_N2LL_ANS_BYE = 'bye you by N2LL'
AG_N2LL_ANS_QUERY = 'NX {} agent {} at {}'
AG_N2LL_ANS_ROUTE_OK = 'ngrok at mac {}\n{}port {}\n{}url {}'
AG_N2LL_ANS_ROUTE_ERR_PERMISSIONS = 'error: few permissions to rm ngrok'
AG_N2LL_ANS_ROUTE_ERR_ALREADY = 'error: ngrok not grep at {}, maybe runs somewhere else?'
