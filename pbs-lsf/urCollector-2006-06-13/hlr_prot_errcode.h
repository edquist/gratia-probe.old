/* DGAS (DataGrid Accounting System)
 * definition of error codes.
// -------------------------------------------------------------------------
// Copyright (c) 2004-2006, The EGEE project, INFN, 
// All rights reserved. See LICENSE file for details.
// -------------------------------------------------------------------------
// Author: Andrea Guarise <andrea.guarise@to.infn.it>
*/
/***************************************************************************
 * Code borrowed from:
 *  authors   : 
 *             
 *  
 ***************************************************************************/

/*Following errors are 'int' */
#define E_GM_ALREADY_PRESENT	113
#define E_GM_INSERT		114
#define ACCESS_DENIED 		-1
/*UI : 5* */
#define INFO_NOT_FOUND 		"51"
#define E_UI_PARSE_ID 		"55"
/*BANK: 2* */
#define CREDIT_ERROR 		"21"
#define CREDIT_DUPL  		"22"
#define E_NO_USER 		"23"
#define E_DEBIT_ERROR 		"24"
#define E_BANK_PARSE_ID 	"25"
#define E_NO_RES_BANK_ID 	"26"
/*generic 1* */
#define E_MAXRETRY 		"11"
#define E_PARSE_ERROR 		"12"
#define E_NO_CONNECTION 	"13"
#define E_SEND_MESSAGE 		"14"
#define E_RECEIVE_MESSAGE 	"15"
#define E_NO_ATTRIBUTES		"16"
#define E_NO_DB			"17"
#define E_LOCK_OPEN		"18"
#define E_LOCK_REMOVE		"19"
#define E_SERVER_START		"110"
#define E_PARAM			"111"
#define E_FOPEN			"112"

/*PA: 3* */
#define PA_ERR_NO_PRICE 	"31"
#define PA_ERR_MDS_INFO 	"32"
#define PA_ERR_PUT_PRICE 	"33"
#define PA_ERR_RES_INIT 	"34"
#define E_PA_PARSE_ID 		"35"
#define PA_ERR_DL_OPEN          "36"
#define PA_ERR_DL_SYMBOL        "37"
#define E_NO_PA       		"38"

/*jobAuth 4* */
#define JOB_DUPL  		"41"
#define E_JA_PARSE_ID 		"45"

/*ATM 6* */
#define ATM_E_AUTH 		"61"
#define ATM_E_PRICE 		"62"
#define ATM_E_COST 		"63"
#define ATM_E_TRANS 		"64"
#define ATM_E_DUPLICATED 	"65"
#define E_WRONG_RES_HLR		"66"

/*RUI 7* */
#define E_RUI_PARSE_ID          "75"

/*PING 8* */
#define E_PING_PARSE_ID		"85"

/*UserAuth*/
#define E_JOB_NOTREG		"91"
