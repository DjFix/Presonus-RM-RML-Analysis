/*
	File:		AVCTapeTgt.mm

 Synopsis: This is the source file for the AVCTapeTgt functionality

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

#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#import "AVHDD.h"

#include "avcTarget.h"
#include "AVCTapeTgt.h"
#include "avcCommandVerboseLog.h"

// Global Var for tape subunit data
AVCTapeTgtDataPtr gpTapeData;

// Prototypes
IOReturn AVCCommandHandlerCallback( void *refCon,
									UInt32 generation,
									UInt16 srcNodeID,
									IOFWSpeed speed,
									const UInt8 * command,
									UInt32 cmdLen);

IOReturn AVCUnitVendorUniqueCommandHandlerCallback( void *refCon,
													UInt32 generation,
													UInt16 srcNodeID,
													IOFWSpeed speed,
													const UInt8 * command,
													UInt32 cmdLen);


IOReturn AVCSubUnitPlugHandlerCallback(void *refCon,
									   UInt32 subunitTypeAndID,
									   IOFWAVCPlugTypes plugType,
									   UInt32 plugID,
									   IOFWAVCSubunitPlugMessages plugMessage,
									   UInt32 messageParams);

static UInt32 intToBCD(unsigned int value);
static unsigned int bcd2bin(unsigned int input);

//////////////////////////////////////////////////////
// AVCTapeTgtInit
//////////////////////////////////////////////////////
IOReturn AVCTapeTgtInit(IOFireWireAVCLibProtocolInterface **nodeAVCProtocolInterface)
{
	IOReturn result = kIOReturnSuccess ;
	AVCTapeTgtDataPtr pTapeData;
	UInt32 subUnitTypeAndID;
	UInt32 sourcePlugNum = 0;
	UInt32 destPlugNum = 0;
	UInt32 retry = 5;
	
	// Allocate memory for this tape subunit's private data struct
	pTapeData = (AVCTapeTgtData*) malloc(sizeof (AVCTapeTgtData));
	if (!pTapeData)
		return kIOReturnNoMemory;
			
	gpTapeData = pTapeData;
	// Initialize private data vars
	pTapeData->timeCode = 0;
	pTapeData->nodeAVCProtocolInterface = nodeAVCProtocolInterface;
	pTapeData->transport_mode = kAVCTapeWindOpcode;
	pTapeData->transport_state = kAVCTapeWindStop;
	
	// Add a tape subunit
	result = (*nodeAVCProtocolInterface)->addSubunit(nodeAVCProtocolInterface,
												  kAVCTapeRecorder,
												  1,
												  1,
												  pTapeData,
												  AVCSubUnitPlugHandlerCallback,
												  &subUnitTypeAndID);
    if (result != kIOReturnSuccess)
        return result ;

	[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Added virtual tape subunit: 0x%02X\n",subUnitTypeAndID]];
	
	// Setup signal formats for plugs
	result = (*nodeAVCProtocolInterface)->setSubunitPlugSignalFormat(nodeAVCProtocolInterface,
																  subUnitTypeAndID,
																  IOFWAVCPlugSubunitSourceType,
																  0,
												(kAVCPlugSignalFormatNTSCDV+(gpDVFormatInfo->dvMode) << 16) );
	if (result != kIOReturnSuccess)
		return result;

	result = (*nodeAVCProtocolInterface)->setSubunitPlugSignalFormat(nodeAVCProtocolInterface,
																  subUnitTypeAndID,
																  IOFWAVCPlugSubunitDestType,
																  0,
													(kAVCPlugSignalFormatNTSCDV+(gpDVFormatInfo->dvMode) << 16) );
	if (result != kIOReturnSuccess)
		return result;
	
	sourcePlugNum = 0;
	destPlugNum = kAVCAnyAvailableIsochPlug;
	// Connect the subunit source to any available unit output plug
	result = (*nodeAVCProtocolInterface)->connectTargetPlugs(nodeAVCProtocolInterface,
														  subUnitTypeAndID,
														  IOFWAVCPlugSubunitSourceType,
														  &sourcePlugNum,
														  kAVCUnitAddress,
														  IOFWAVCPlugIsochOutputType,
														  &destPlugNum,
														  false,
														  false);
	if (result != kIOReturnSuccess)
		return result;
	
	// Save the isoch out plug num
	gpTapeData->isochOutPlug = destPlugNum;

	sourcePlugNum = kAVCAnyAvailableIsochPlug;
	destPlugNum = 0;
	// Connect the subunit dest to any available unit input plug
	result = (*nodeAVCProtocolInterface)->connectTargetPlugs(nodeAVCProtocolInterface,
														  kAVCUnitAddress,
														  IOFWAVCPlugIsochInputType,
														  &sourcePlugNum,
														  subUnitTypeAndID,
														  IOFWAVCPlugSubunitDestType,
														  &destPlugNum,
														  false,
														  false);
	if (result != kIOReturnSuccess)
		return result;

	// Save the isoch in plug num
	gpTapeData->isochInPlug = sourcePlugNum;

	// Install command handler for the newly installed tape subunit
	result = (*nodeAVCProtocolInterface)->installAVCCommandHandler(nodeAVCProtocolInterface,
																subUnitTypeAndID,
																kAVCAllOpcodes,
																pTapeData,
																AVCCommandHandlerCallback);
	if (result != kIOReturnSuccess)
		return -1;

	if ((gpDVFormatInfo->dvMode == 0x78) || 
	 (gpDVFormatInfo->dvMode == 0xF8) || 
	 (gpDVFormatInfo->dvMode == 0x74) || 
	 (gpDVFormatInfo->dvMode == 0xF4) || 
	 (gpDVFormatInfo->dvMode == 0x70) || 
	 (gpDVFormatInfo->dvMode == 0xF0))
	{
		// FOR DVCPro devices, we must support the vendor unique command addressed to the unit
		result = (*nodeAVCProtocolInterface)->installAVCCommandHandler(nodeAVCProtocolInterface,
																 kAVCUnitAddress,
																 0x00,
																 pTapeData,
																 AVCUnitVendorUniqueCommandHandlerCallback);
		if (result != kIOReturnSuccess)
			return -1;
	}
	
	// Set the master plug registers 
	retry = 0;
	do
	{
		result =(*nodeAVCProtocolInterface)->updateOutputMasterPlug(nodeAVCProtocolInterface,
															  (*nodeAVCProtocolInterface)->readOutputMasterPlug(nodeAVCProtocolInterface),
															  0xBFFFFF1F);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));

	retry = 0;
	do
	{
		result = (*nodeAVCProtocolInterface)->updateInputMasterPlug(nodeAVCProtocolInterface,
													 (*nodeAVCProtocolInterface)->readInputMasterPlug(nodeAVCProtocolInterface),
													 0x80FFFF1F);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));
	
	// Set the oPCR/iPCR correctly
	retry = 0;
	do
	{
		result = (*nodeAVCProtocolInterface)->updateOutputPlug(nodeAVCProtocolInterface,
												gpTapeData->isochOutPlug,
												(*nodeAVCProtocolInterface)->readOutputPlug(nodeAVCProtocolInterface,gpTapeData->isochOutPlug),
												0x803F3C7A);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));
	
	retry = 0;
	do
	{
		(*nodeAVCProtocolInterface)->updateInputPlug(nodeAVCProtocolInterface,
											   gpTapeData->isochInPlug,
											   (*nodeAVCProtocolInterface)->readInputPlug(nodeAVCProtocolInterface,gpTapeData->isochInPlug),
											   0xC03F0000);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));
	
	return result;
}


//////////////////////////////////////////////////////
// AVCTapeTgtSetOutputPlugBroadcastConnection
//////////////////////////////////////////////////////
void AVCTapeTgtSetOutputPlugBroadcastConnection(UInt32 chan, IOFWSpeed speed)
{
	IOReturn result;
	UInt32 retry = 0;
	UInt32 oldVal, newVal;
	do
	{
		oldVal = (*gpTapeData->nodeAVCProtocolInterface)->readOutputPlug(gpTapeData->nodeAVCProtocolInterface,gpTapeData->isochOutPlug);
		
		newVal = oldVal & 0xFFC03FFF;
		newVal |= (chan << 16);
		newVal |= ((UInt32)speed << 14);
		newVal |= 0x40000000;
		
		result = (*gpTapeData->nodeAVCProtocolInterface)->updateOutputPlug(gpTapeData->nodeAVCProtocolInterface,
														 gpTapeData->isochOutPlug,
														 oldVal,
														 newVal);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));
}

//////////////////////////////////////////////////////
// AVCTapeTgtClearOutputPlugBroadcastConnection
//////////////////////////////////////////////////////
void AVCTapeTgtClearOutputPlugBroadcastConnection(void)
{
	IOReturn result;
	UInt32 retry = 0;
	UInt32 oldVal, newVal;
	do
	{
	
		oldVal = (*gpTapeData->nodeAVCProtocolInterface)->readOutputPlug(gpTapeData->nodeAVCProtocolInterface,gpTapeData->isochOutPlug);
		
		newVal = oldVal & 0xBFFFFFFF;
		
		result = (*gpTapeData->nodeAVCProtocolInterface)->updateOutputPlug(gpTapeData->nodeAVCProtocolInterface,
														 gpTapeData->isochOutPlug,
														 oldVal,
														 newVal);
	}
	while ((result != kIOReturnSuccess) && (retry++ < 5));
}

//////////////////////////////////////////////////////
// AVCUnitVendorUniqueCommandHandlerCallback
//////////////////////////////////////////////////////
IOReturn AVCUnitVendorUniqueCommandHandlerCallback( void *refCon,
									UInt32 generation,
									UInt16 srcNodeID,
									IOFWSpeed speed,
									const UInt8 * command,
									UInt32 cmdLen)
{
	AVCTapeTgtDataPtr pTapeData = (AVCTapeTgtDataPtr) refCon;
	UInt8 *pRspFrame;
	
	pRspFrame = (UInt8*) malloc(cmdLen);
	if (!pRspFrame)
		return kIOReturnNoMemory;

	/* copy cmd frame to rsp frame */
	bcopy(command,pRspFrame,cmdLen);

	// Set implemented/stable response
	pRspFrame[kAVCCommandResponse] = kAVCImplementedStatus;

	/* Send the response */
	(*pTapeData->nodeAVCProtocolInterface)->sendAVCResponse(
														 pTapeData->nodeAVCProtocolInterface,
														 generation,
														 srcNodeID,
														 (const char*) pRspFrame,
														 cmdLen);

	// Free allocated response frame
	free(pRspFrame);

	return kIOReturnSuccess;
}	

//////////////////////////////////////////////////////
// AVCCommandHandlerCallback
//////////////////////////////////////////////////////
IOReturn AVCCommandHandlerCallback( void *refCon,
									UInt32 generation,
									UInt16 srcNodeID,
									IOFWSpeed speed,
									const UInt8 * command,
									UInt32 cmdLen)
{
	/* Local Vars */
	AVCTapeTgtDataPtr pTapeData = (AVCTapeTgtDataPtr) refCon;
	UInt8 cType = command[kAVCCommandResponse] & 0x0F;
	UInt8 *pRspFrame;
	UInt32 timeInFrames;
	UInt32 hours;
	UInt32 seconds;
	UInt32 minutes;
	FCPCommandHandlerParams fcpParams;

	pRspFrame = (UInt8*) malloc(cmdLen);
	if (!pRspFrame)
		return kIOReturnNoMemory;

	// Set parameters of structure for verbose logging
	fcpParams.generation = generation;
	fcpParams.srcNodeID = srcNodeID;
	fcpParams.command = (UInt8 *) command;
	fcpParams.cmdLen = cmdLen;
	fcpParams.response = pRspFrame;
	fcpParams.responseLen = &cmdLen;

	// If verbose logging enabled, print command packet info 
	if ([gpUserIntf verboseAVCLoggingEnabled])
		avcCommandVerboseLog(&fcpParams);
	
	/* copy cmd frame to rsp frame */
	bcopy(command,pRspFrame,cmdLen);

	/* We currently don't support notify type commands */
	/* For others, set the default response as accepted or stable */
	if (cType == kAVCNotifyCommand)
		pRspFrame[kAVCCommandResponse] = kAVCNotImplementedStatus;
	else if (cType == kAVCControlCommand)
		pRspFrame[kAVCCommandResponse] = kAVCAcceptedStatus;
	else
		pRspFrame[kAVCCommandResponse] = kAVCImplementedStatus;
	
	/* parse the command */
	switch (command[kAVCOpcode])
	{

		////////////////////////////
		//
		// AVC Tape Play Command
		//
		////////////////////////////
		case kAVCTapePlayOpcode:
			// If we are in record mode, now we need to stop the DV receiver
			if (pTapeData->transport_mode == kAVCTapeRecordOpcode)
				[gpUserIntf performSelectorOnMainThread:@selector(avcRecordStopCmdHandler)
																		   withObject:nil
																	 waitUntilDone:YES];

			// Set the new mode
			pTapeData->transport_mode = command[kAVCOpcode];
			pTapeData->transport_state = command[kAVCOperand0];
			
			// Start the DV transmitter if it's not already running
			if (gpXmitter->transportState == kDVTransmitterTransportStopped)
				[gpUserIntf performSelectorOnMainThread:@selector(avcPlayCmdHandler)
														   withObject:nil
													 waitUntilDone:NO];
			break;
			
		////////////////////////////
		//
		// AVC Tape Wind Command
		//
		////////////////////////////
		case kAVCTapeWindOpcode:
			if (gpXmitter->transportState != kDVTransmitterTransportStopped)
				[gpUserIntf performSelectorOnMainThread:@selector(avcRecordStopCmdHandler)
														 withObject:nil
													  waitUntilDone:YES];
			
				
			if (gpXmitter->transportState != kDVTransmitterTransportStopped)
				[gpUserIntf performSelectorOnMainThread:@selector(avcStopCmdHandler)
														 withObject:nil
													  waitUntilDone:YES];
			
			if (command[kAVCOperand0] == kAVCTapeWindFastFwd)
			{
				[gpUserIntf adjustTimeCodePositionToEOF];
			}
			else if ((command[kAVCOperand0] == kAVCTapeWindRew) || (command[kAVCOperand0] == kAVCTapeWindHighSpdRew))
			{
				[gpUserIntf adjustTimeCodePosition:0];
			}
				
			pTapeData->transport_mode = command[kAVCOpcode];
			pTapeData->transport_state = kAVCTapeWindStop;
			break;

		////////////////////////////
		//
		// AVC Tape Record Command
		//
		////////////////////////////
		case kAVCTapeRecordOpcode:
			// If we are in play mode, now we need to stop the DV receiver
			if (pTapeData->transport_mode == kAVCTapePlayOpcode)
				[gpUserIntf performSelectorOnMainThread:@selector(avcStopCmdHandler)
																			withObject:nil
																		waitUntilDone:YES];
			
			// Set the new mode
			pTapeData->transport_mode = command[kAVCOpcode];
			pTapeData->transport_state = command[kAVCOperand0];
			
			// Start the DV receiver if it's not already running
			if (gpReceiver->transportState == kDVReceiverTransportStopped)
				[gpUserIntf performSelectorOnMainThread:@selector(avcRecordCmdHandler)
																		   withObject:nil
																	 waitUntilDone:NO];
			break;
			
		////////////////////////////
   		//
		// AVC Tape Relative Time Counter Command
		//
		////////////////////////////
		case kAVCTapeRelativeTimeCounterOpcode:
			if (cType == kAVCStatusInquiryCommand)
			{
				timeInFrames = pTapeData->timeCode;

				hours = timeInFrames / 108000;
				timeInFrames -= (hours*108000);
				minutes = timeInFrames / 1800;
				timeInFrames -= (minutes*1800);
				seconds = timeInFrames / 30;
				timeInFrames -= (seconds*30);
				
				pRspFrame[kAVCOperand1] = intToBCD(timeInFrames);
				pRspFrame[kAVCOperand2] = intToBCD(seconds);
				pRspFrame[kAVCOperand3] = intToBCD(minutes);
				pRspFrame[kAVCOperand4] = intToBCD(hours);

				pRspFrame[kAVCCommandResponse] = kAVCImplementedStatus;
			}
			else if (cType == kAVCControlCommand)
				pRspFrame[kAVCCommandResponse] = kAVCRejectedStatus;
			break;


		////////////////////////////
		//
		// AVC Tape (Absolute) Time Counter Command
  		//
  		////////////////////////////
		case kAVCTapeTimeCodeOpcode:
			if (cType == kAVCControlCommand)
			{
				if (command[kAVCOperand0] != 0x20)
				{
					pRspFrame[kAVCCommandResponse] = kAVCRejectedStatus;
				}
				else
				{
					// First, if we are transmitting or receiving, stop it now!
					if (gpXmitter->transportState != kDVTransmitterTransportStopped)
						[gpUserIntf performSelectorOnMainThread:@selector(avcRecordStopCmdHandler)
																			 withObject:nil
																	   waitUntilDone:YES];
					
					
					if (gpXmitter->transportState != kDVTransmitterTransportStopped)
						[gpUserIntf performSelectorOnMainThread:@selector(avcStopCmdHandler)
																			 withObject:nil
																	   waitUntilDone:YES];
					
					timeInFrames = bcd2bin(command[kAVCOperand1]);
					timeInFrames += (bcd2bin(command[kAVCOperand2])*30);
					timeInFrames += (bcd2bin(command[kAVCOperand3])*1800);
					timeInFrames += (bcd2bin(command[kAVCOperand4])*108000);
					
					[gpUserIntf adjustTimeCodePosition:timeInFrames];
					
					// Set the new mode
					pTapeData->transport_mode = kAVCTapePlayOpcode;
					pTapeData->transport_state = kAVCTapePlayFwdPause;
					
					// Start the DV transmitter if it's not already running
					if (gpXmitter->transportState == kDVTransmitterTransportStopped)
						[gpUserIntf performSelectorOnMainThread:@selector(avcPlayCmdHandler)
																			 withObject:nil
																	   waitUntilDone:NO];
				}
			}
			else if (cType == kAVCStatusInquiryCommand)
			{
				if (command[kAVCOperand0] != 0x71)
				{
					pRspFrame[kAVCCommandResponse] = kAVCRejectedStatus;
				}
				else
				{
					timeInFrames = pTapeData->timeCode;
					
					hours = timeInFrames / 108000;
					timeInFrames -= (hours*108000);
					minutes = timeInFrames / 1800;
					timeInFrames -= (minutes*1800);
					seconds = timeInFrames / 30;
					timeInFrames -= (seconds*30);
					
					pRspFrame[kAVCOperand1] = intToBCD(timeInFrames);
					pRspFrame[kAVCOperand2] = intToBCD(seconds);
					pRspFrame[kAVCOperand3] = intToBCD(minutes);
					pRspFrame[kAVCOperand4] = intToBCD(hours);
				}
			}
			break;
			


		case kAVCTapeOutputSignalModeOpcode:
		case kAVCTapeInputSignalModeOpcode:
			if (cType == kAVCStatusInquiryCommand)
			{
				pRspFrame[kAVCOperand0] = gpDVFormatInfo->dvMode;
			}
			else if (cType == kAVCControlCommand)
				pRspFrame[kAVCCommandResponse] = kAVCRejectedStatus;
			break;

		case kAVCTapeRecordingSpeedOpcode:
			pRspFrame[kAVCOperand0] = kAVCTapeRecSpeedSP;
			break;

		case kAVCTapeTapePlaybackFormatOpcode:
		case kAVCTapeTapeRecordingFormatOpcode:
			pRspFrame[kAVCOperand0] = 0xF8;
			pRspFrame[kAVCOperand1] = 0x00;
			pRspFrame[kAVCOperand2] = 0x00;
			pRspFrame[kAVCOperand3] = 0x00;
			pRspFrame[kAVCOperand4] = 0x00;
			pRspFrame[kAVCOperand5] = 0x00;
			pRspFrame[kAVCOperand6] = 0x00;
			pRspFrame[kAVCOperand7] = 0x00;
			pRspFrame[kAVCOperand8] = 0x00;
			break;

		case kAVCTapeMediumInfoOpcode:
			pRspFrame[kAVCOperand0] = 0x32;	/* SmallDV type cassette */
			pRspFrame[kAVCOperand1] = 0x30; /* DV, OK TO Record */
			break;

		////////////////////////////
		//
		// AVC Tape Transport State Command
		//
		////////////////////////////
		case kAVCTapeTransportStateOpcode:
			pRspFrame[kAVCOpcode] = pTapeData->transport_mode;   /* opcode */
			pRspFrame[kAVCOperand0] = pTapeData->transport_state;   /* operand 0 */
			break;

		case kAVCTapeAbsoluteTrackNumberOpcode:
			/* Hard code this for now */
			pRspFrame[kAVCOperand0] = 0x71;                     /* operand 0 */
			pRspFrame[kAVCOperand1] = 0xFF;                     /* operand 1 */
			pRspFrame[kAVCOperand2] = 0xFF;
			pRspFrame[kAVCOperand3] = 0xFF;
			pRspFrame[kAVCOperand4] = 0xFF;
			break;

		default:
			pRspFrame[kAVCCommandResponse] = kAVCNotImplementedStatus;
			break;
	}

	// If verbose logging enabled, print response packet info 
	if ([gpUserIntf verboseAVCLoggingEnabled])
		avcResponseVerboseLog(&fcpParams);
	
	/* Send the response */
	(*pTapeData->nodeAVCProtocolInterface)->sendAVCResponse(
														 pTapeData->nodeAVCProtocolInterface,
														 generation,
														 srcNodeID,
														 (const char*) pRspFrame,
														 cmdLen);
	// Free allocated response frame
	free(pRspFrame);

	return kIOReturnSuccess;
}

//////////////////////////////////////////////////////
// AVCSubUnitPlugHandlerCallback
//////////////////////////////////////////////////////
IOReturn AVCSubUnitPlugHandlerCallback(void *refCon,
									   UInt32 subunitTypeAndID,
									   IOFWAVCPlugTypes plugType,
									   UInt32 plugID,
									   IOFWAVCSubunitPlugMessages plugMessage,
									   UInt32 messageParams)
{
	IOReturn result = kIOReturnSuccess;
	UInt32 connectedSubunitTypeAndID = ((messageParams & 0x00FF0000) >> 16);
	UInt32 connectedPlugType = ((messageParams & 0x0000FF00) >> 8);
	UInt32 connectedPlugID = (messageParams & 0x000000FF);

	UInt32 newChannel = ((messageParams & 0x003F0000) >> 16);
    UInt32 p2pCount = ((messageParams & 0x3F000000) >> 24);
	UInt32 newSpeed = ((messageParams & 0x0000C000) >> 14);
	
	// Handle the various plug messages
	switch (plugMessage)
	{

		case kIOFWAVCSubunitPlugMsgConnected:
			[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\nTape Subunit %s %d Connected To\n",
					(plugType == IOFWAVCPlugSubunitSourceType) ? "Source Plug":"Dest Plug", plugID]];
			switch (connectedPlugType)
			{
				case IOFWAVCPlugSubunitSourceType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Subunit 0x%02X Source Plug %d\n\n",
						connectedSubunitTypeAndID,
						connectedPlugID]];
					break;

				case IOFWAVCPlugSubunitDestType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Subunit 0x%02X Dest Plug %d\n\n",
						connectedSubunitTypeAndID,
						connectedPlugID]];
					break;

				case IOFWAVCPlugIsochInputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit Isoch Input Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugIsochOutputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit Isoch Output Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugExternalInputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit External Input Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugExternalOutputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit External Output Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugAsynchInputType:
				case IOFWAVCPlugAsynchOutputType:
				default:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Invalid Plug\n\n"]];
					break;
			};
			break;

		case kIOFWAVCSubunitPlugMsgDisconnected:
			[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"\nTape Subunit %s %d Disconnected From\n",
		  (plugType == IOFWAVCPlugSubunitSourceType) ? "Source Plug":"Dest Plug", plugID]];
			switch (connectedPlugType)
			{
				case IOFWAVCPlugSubunitSourceType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Subunit 0x%02X Source Plug %d\n\n",
						connectedSubunitTypeAndID,
						connectedPlugID]];
					break;

				case IOFWAVCPlugSubunitDestType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Subunit 0x%02X Dest Plug %d\n\n",
						connectedSubunitTypeAndID,
						connectedPlugID]];
					break;

				case IOFWAVCPlugIsochInputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit Isoch Input Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugIsochOutputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit Isoch Output Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugExternalInputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit External Input Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugExternalOutputType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Unit External Output Plug %d\n\n",
						connectedPlugID]];
					break;

				case IOFWAVCPlugAsynchInputType:
				case IOFWAVCPlugAsynchOutputType:
				default:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Invalid Plug\n\n"]];
					break;
			};
			break;
			
		case kIOFWAVCSubunitPlugMsgConnectedPlugModified:
			switch (plugType)
			{
				case IOFWAVCPlugSubunitSourceType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"oPCR: Chan:%d P2P Cnt:%d Spd: %d\n",newChannel,p2pCount,newSpeed]];

					// P2P Count
					[gpUserIntf updateOutputPlugConnections:p2pCount];

					if ((p2pCount > 0) && (gpAVC->transmitStarted == false))
					{
						// We weren't transmitting, but
						// somebody has connected to us.

						// Channel
						gpXmitter->setTransmitIsochChannel(newChannel);
						[gpUserIntf updateOutputPlugChannel:newChannel];
						[gpUserIntf updateOutputChannelStepperIntVal:newChannel];

						// Speed
						switch (newSpeed)
						{
							case 0:
								[gpUserIntf updateOutputPlugSpeed:@"100"];
								gpXmitter->setTransmitIsochSpeed(kFWSpeed100MBit);
								break;
							case 1:
								[gpUserIntf updateOutputPlugSpeed:@"200"];
								gpXmitter->setTransmitIsochSpeed(kFWSpeed200MBit);
								break;
							case 2:
								[gpUserIntf updateOutputPlugSpeed:@"400"];
								gpXmitter->setTransmitIsochSpeed(kFWSpeed400MBit);
								break;
							default:
								[gpUserIntf updateOutputPlugSpeed:@"Unknown"];
								gpXmitter->setTransmitIsochSpeed(kFWSpeed100MBit);
								break;
						};
					}
					break;
					
				case IOFWAVCPlugSubunitDestType:
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"iPCR: Chan:%d P2P Cnt:%d Spd: %d\n",newChannel,p2pCount,newSpeed]];

					// P2P Count
					[gpUserIntf updateInputPlugConnections:p2pCount];

					if ((p2pCount > 0) && (gpAVC->receiveStarted == false))
					{
						// We weren't receiving, but
						// somebody has connected to us.

						// Channel
						gpReceiver->setReceiveIsochChannel(newChannel);
						[gpUserIntf updateInputPlugChannel:newChannel];
						[gpUserIntf updateInputChannelStepperIntVal:newChannel];

						// Speed
						switch (newSpeed)
						{
							case 0:
								[gpUserIntf updateInputPlugSpeed:@"100"];
								gpReceiver->setReceiveIsochSpeed(kFWSpeed100MBit);
								break;
							case 1:
								[gpUserIntf updateInputPlugSpeed:@"200"];
								gpReceiver->setReceiveIsochSpeed(kFWSpeed200MBit);
								break;
							case 2:
								[gpUserIntf updateInputPlugSpeed:@"400"];
								gpReceiver->setReceiveIsochSpeed(kFWSpeed400MBit);
								break;
							default:
								[gpUserIntf updateInputPlugSpeed:@"Unknown"];
								gpReceiver->setReceiveIsochSpeed(kFWSpeed100MBit);
								break;
						};
					}
					break;
					
				default:
					break;
			};

			break;

		case kIOFWAVCSubunitPlugMsgSignalFormatModified:
			// Return an error if the new signal format is not MPEG2-TS
			if ((messageParams & 0xFF000000) != 0xA0000000)
				result = kIOReturnError;
			break;

		default:
			break;
	};
	
	return result;
}	

/*******************************************************************************
**
** intToBCD
*/
static UInt32 intToBCD(unsigned int value)
{
	int result = 0;
	int i = 0;

	while (value > 0) {
		result |= ((value % 10) << (4 * i++));

		value /= 10;
	}

	return (result);
}

/*******************************************************************************
**
** AVCTapeTgtSetState
*/
IOReturn	AVCTapeTgtSetState(UInt8 transport_mode, UInt8 transport_state)
{
	if (gpTapeData)
	{
		gpTapeData->transport_mode = transport_mode;
		gpTapeData->transport_state = transport_state;
	}

	return kIOReturnSuccess;
}

/*******************************************************************************
**
** AVCTapeTgtGetState
*/
IOReturn	AVCTapeTgtGetState(UInt8 *pTransport_mode, UInt8 *pTransport_state)
{
	if (gpTapeData)
	{
		*pTransport_mode = gpTapeData->transport_mode;
		*pTransport_state = gpTapeData->transport_state;
	}
	else
	{
		*pTransport_mode = kAVCTapeWindOpcode;
		*pTransport_state = kAVCTapeWindStop;
	}
	
	return kIOReturnSuccess;
}


/*******************************************************************************
**
** AVCTapeTgtSetTimeCode
*/
IOReturn AVCTapeTgtSetTimeCode(unsigned int timecodeInFrames)
{
	if (gpTapeData)
		gpTapeData->timeCode = timecodeInFrames;

	return kIOReturnSuccess;
}


//////////////////////////////////////////////
// bcd2bin - BCD to Bin conversion
//////////////////////////////////////////////
static unsigned int bcd2bin(unsigned int input)
{
	unsigned int shift,output;
	
	shift = 1;
	output = 0;
	while(input)
	{
		output += (input%16) * shift;
		input /= 16;
		shift *= 10;
	};
	
	return output;
}
