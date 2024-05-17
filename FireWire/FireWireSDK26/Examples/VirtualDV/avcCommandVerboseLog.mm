/*
	File:		avcCommandVerboseLog.mm

 Synopsis: This is the source file for the avcCommandVerboseLog functionality

	Copyright: 	© Copyright 2001-2005 Apple Computer, Inc. All rights reserved.

	Written by: ayanowitz

 Disclaimer:	IMPORTANT:  This Apple software is supplied to you by Apple Computer, Inc.
 ("Apple") in consideration of your agreement to the following terms, and your
 use, installation, modification or redistribution of this Apple software
 constitutes acceptance of these terms.  If you do not agree with these terms,
 please do not use, install, modify or redistribute this Apple software.

 In consideration of your agreement to abide by the following terms, and subject
 to these terms, Apple grants you a personal, non-exclusive license, under Apple’s
 copyrights in this original Apple software (the "Apple Software"), to use,
 reproduce, modify and redistribute the Apple Software, with or without
 modifications, in source and/or binary forms; provided that if you redistribute
 the Apple Software in its entirety and without modifications, you must retain
 this notice and the following text and disclaimers in all such redistributions of
 the Apple Software.  Neither the name, trademarks, service marks or logos of
 Apple Computer, Inc. may be used to endorse or promote products derived from the
 Apple Software without specific prior written permission from Apple.  Except as
 expressly stated in this notice, no other rights or licenses, express or implied,
 are granted by Apple herein, including but not limited to any patent rights that
 may be infringed by your derivative works or by other works in which the Apple
 Software may be incorporated.

 The Apple Software is provided by Apple on an "AS IS" basis.  APPLE MAKES NO
 WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION THE IMPLIED
 WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 PURPOSE, REGARDING THE APPLE SOFTWARE OR ITS USE AND OPERATION ALONE OR IN
 COMBINATION WITH YOUR PRODUCTS.

 IN NO EVENT SHALL APPLE BE LIABLE FOR ANY SPECIAL, INDIRECT, INCIDENTAL OR
 CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
 GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 ARISING IN ANY WAY OUT OF THE USE, REPRODUCTION, MODIFICATION AND/OR DISTRIBUTION
 OF THE APPLE SOFTWARE, HOWEVER CAUSED AND WHETHER UNDER THEORY OF CONTRACT, TORT
 (INCLUDING NEGLIGENCE), STRICT LIABILITY OR OTHERWISE, EVEN IF APPLE HAS BEEN
 ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*/

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/firewire/IOFireWireLibIsoch.h>
#include <IOKit/avc/IOFireWireAVCLib.h>

#import "AVHDD.h"

#import "avcCommandVerboseLog.h"

typedef struct valueStringsStruct
{
	int val;
	const char *string;
}ValueStrings, *ValueStringsPtr;

ValueStrings cTypeStrings[] =
{
	{ 0,"Control"},
	{ 1,"Status"},
	{ 2,"Specific-Inquiry"},
	{ 3,"Notify"},
	{ 4,"General-Inquiry"},
	{ -1,nil} 
};

ValueStrings responseStrings[] =
{
	{ 0x08,"Not Implemented"},
	{ 0x09,"Accepted"},
	{ 0x0A,"Rejected"},
	{ 0x0B,"In Transition"},
	{ 0x0C,"Implemented/Stable"},
	{ 0x0D,"Changed"},
	{ 0x0E,"Reserved Response"},
	{ 0x0F,"Interim"},
	{ -1,nil}
};

ValueStrings unitOpCodeStrings[] =
{
	// Unit Commands
	{ 0x00,"Vendor Unique"},
	{ 0x02,"Plug-Info"},
	{ 0x30,"Unit Info"},
	{ 0x31,"Sub-Unit Info"},
	{ 0xB2,"Power"},
	{ 0x24,"Connect"},
	{ 0x25,"Disconnect"},
	{ 0x18,"Output Plug Signal Format"},
	{ 0x19,"Input Plug Signal Format"},
	{ 0x0F,"DTCP"},

	// Descriptor Commands
	{ 0x06,"Read Info-Block"},
	{ 0x07,"Write Info-Block"},
	{ 0x08,"Open Descriptor"},
	{ 0x09,"Read Descriptor"},
	{ 0x0A,"Write Descriptor"},
	{ 0x0C,"Create Descriptor"},

	{ -1,nil}
};

ValueStrings discOpCodeStrings[] =
{
	// Unit/Subunit Commands
	{ 0x00,"Vendor Unique"},
	{ 0x02,"Plug-Info"},

	// Descriptor Commands
	{ 0x06,"Read Info-Block"},
	{ 0x07,"Write Info-Block"},
	{ 0x08,"Open Descriptor"},
	{ 0x09,"Read Descriptor"},
	{ 0x0A,"Write Descriptor"},
	{ 0x0C,"Create Descriptor"},

	// Disc Subunit Commands
	{ 0xC5,"Stop"},
	{ 0xC3,"Play"},
	{ 0xC2,"Record"},
	{ 0xD1,"Configure"},
	{ 0x40,"Erase"},
	{ 0xD3,"Set Plug Association"},

	{ -1,nil}
};

ValueStrings tapeOpCodeStrings[] =
{
	// Unit/Subunit Commands
	{ 0x00,"Vendor Unique"},
	{ 0x02,"Plug-Info"},

	// Tape Subunit Commands
	{ 0x70,"Analog Audio Output Mode"},
	{ 0x72,"Area Mode"},
	{ 0x52,"Absolute Track Number"},
	{ 0x71,"Audio Mode"},
	{ 0x56,"Backward"},
	{ 0x5A,"Binary Group"},
	{ 0x40,"Edit Mode"},
	{ 0x55,"Forward"},
	{ 0x79,"Input Signal Mode"},
	{ 0xC1,"Load Medium"},
	{ 0xCA,"Marker"},
	{ 0xDA,"Medium Info"},
	{ 0x60,"Open MIC"},
	{ 0x78,"Output Signal Mode"},
	{ 0xC3,"Play"},
	{ 0x45,"Preset"},
	{ 0x61,"Read MIC"},
	{ 0xC2,"Record"},
	{ 0x53,"Recording Date"},
	{ 0xDB,"Recording Speed"},
	{ 0x54,"Recording Time"},
	{ 0x57,"Relative Time Counter"},
	{ 0x50,"Search Mode"},
	{ 0x5C,"SMPTE/EBU Recording Time"},
	{ 0x59,"SMPTE/EBU Time Code"},
	{ 0xD3,"Tape Playback Format"},
	{ 0xD2,"Tape Recording Format"},
	{ 0x51,"Time Code"},
	{ 0xD0,"Transport State"},
	{ 0xC4,"Wind"},
	{ 0x62,"Write MIC"},
	
	{ -1,nil}
};

/***********************************************************************
**
**
**
*/
const char* valToString(ValueStringsPtr pStringTable, int val)
{
	ValueStringsPtr pValueString = pStringTable;

	while (pValueString->val != -1)
	{
		if (pValueString->val == val)
			return pValueString->string;
		else
			pValueString = pValueString + 1; // Index to the next value string pair
	}
	return "Unknown";
}


/***********************************************************************
**
**
**
*/
void avcCommandVerboseLog(FCPCommandHandlerParamsPtr pParams)
{
	UInt8 cType = pParams->command[0] & 0x0F;
    UInt8 subUnit = pParams->command[1];
    UInt8 opCode = pParams->command[2];
//    UInt8 *pOperands = (UInt8*) &pParams->command[3];
	unsigned int i;

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n=============== Received AVC Command ===============\n"]];

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"cType:   %s\n",valToString(cTypeStrings,cType)]];
	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"subUnit: 0x%02X\n",subUnit]];

	if (subUnit == 0x20)
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(tapeOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x18)
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(discOpCodeStrings,opCode),opCode]];
	else
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(unitOpCodeStrings,opCode),opCode]];

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"FCP Command Frame:"]];
	for (i=0;i<pParams->cmdLen;i++)
	{
		if ((i % 16) == 0)
			[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];

		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"%02X ",pParams->command[i]]];
	}
	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];
	
	return;
}


/***********************************************************************
**
**
**
*/
void avcResponseVerboseLog(FCPCommandHandlerParamsPtr pParams)
{
    UInt8 subUnit = pParams->response[1];
    UInt8 opCode = pParams->response[2];
//    UInt8 *pResponseOperands = (UInt8*) &pParams->response[3];
    UInt8 *pResponseType = (UInt8*) &pParams->response[0];
	unsigned int i;

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n=============== Sending AVC Response ===============\n"]];

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"response: %s\n",valToString(responseStrings,*pResponseType)]];
	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"subUnit: 0x%02X\n",subUnit]];

	if (subUnit == 0x20)
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(tapeOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x18)
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(discOpCodeStrings,opCode),opCode]];
	else
		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(unitOpCodeStrings,opCode),opCode]];

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"FCP Response Frame:"]];

	for (i=0;i<*pParams->responseLen;i++)
	{
		if ((i % 16) == 0)
			[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];

		[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"%02X ",pParams->response[i]]];
	}
	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];
	
	return;
}