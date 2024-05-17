/*
	File:		AVCDeviceControlPanelController.mm
 
 Synopsis: This is the source file for the AVCDevice Control-Panel Controller 
 
	Copyright: 	¬© Copyright 2001-2005 Apple Computer, Inc. All rights reserved.
 
	Written by: ayanowitz
 
 Disclaimer:	IMPORTANT:  This Apple software is supplied to you by Apple Computer, Inc.
 ("Apple") in consideration of your agreement to the following terms, and your
 use, installation, modification or redistribution of this Apple software
 constitutes acceptance of these terms.  If you do not agree with these terms,
 please do not use, install, modify or redistribute this Apple software.
 
 In consideration of your agreement to abide by the following terms, and subject
 to these terms, Apple grants you a personal, non-exclusive license, under Apple‚Äôs
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


#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#import "AVCDeviceControlPanelController.h"

#define kOpenDeviceButtonOpenString @"Open Device"
#define kOpenDeviceButtonCloseString @"Close Device"

// Defines for "Get EIA-775 Info"
#define kAVCCommandBufSize 16
#define KAVCDescriptorResponseBufSize 512

// Define the polling interval for user-intf timer
#define kAVCDeviceControlPanelPlugPollingInterval 1.0

// Defines for the tab-view index
#define kTabViewItemIndex_General 0
#define kTabViewItemIndex_Plug 1
#define kTabViewItemIndex_Tape 2
#define kTabViewItemIndex_CEA 3

#define kViewerButtonStartText @"Start Viewer"
#define kViewerButtonStopText @"Stop Viewer"

#define kNumCyclesInMPEGReceiverSegment 20
#define kNumSegmentsInMPEGReceiverProgram 100

// Prototypes for static funcitons
IOReturn MyAVCDeviceMessageNotification (class AVCDevice *pAVCDevice,
										 natural_t messageType,
										 void * messageArgument,
										 void *pRefCon);

IOReturn MyAVCDeviceCommandInterfaceMessageNotification(class AVCDeviceCommandInterface *pAVCDeviceCommandInterface,
														natural_t messageType,
														void * messageArgument,
														void *pRefCon);

IOReturn DoAVCTransaction(const UInt8 *command, 
						  UInt32 cmdLen, 
						  UInt8 *response, 
						  UInt32 *responseLen, 
						  AVCDeviceControlPanelController *userIntf,
						  bool doVerboseLogging,
						  bool doUpdateAVCCommandString);

void avcCommandVerboseLog(UInt8 *command, UInt32 cmdLen, AVCDeviceControlPanelController *userIntf);
void avcResponseVerboseLog(	UInt8 *response, UInt32 responseLen, AVCDeviceControlPanelController *userIntf);
static unsigned int bcd2bin(unsigned int input);

void StringLoggerPrintFunction(char *pString,void *pRefCon);

void MPEGReceiverMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon);
IOReturn MyStructuredDataPushProc(UInt32 CycleDataCount, MPEGReceiveCycleData *pCycleData, void *pRefCon);

@implementation AVCDeviceControlPanelController

#pragma mark -----------------------------------
#pragma mark Class General Methods
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// initWithDevice
//////////////////////////////////////////////////////
- (id)initWithDevice:(AVCDevice*)pDevice
{
	if ( self != [ super init ] )
		return nil ;
	
	pAVCDevice = pDevice;
	pAVCDeviceCommandInterface = nil;
	
	NSLog(@"Initializing AVCDeviceControlPanelController for device: %s\n",pAVCDevice->deviceName);

	pAVCDevice->SetClientPrivateData(self);
	
	return self ;
}

//////////////////////////////////////////////////////
// withDevice
//////////////////////////////////////////////////////
+(AVCDeviceControlPanelController *)withDevice:(AVCDevice*) pAVCdevice
{
    return [ [ [ self alloc ] initWithDevice:pAVCdevice ] autorelease ] ;
}

//////////////////////////////////////////////////////
// dealloc
//////////////////////////////////////////////////////
-(void)dealloc
{
	NSLog(@"Deallocating AVCDeviceControlPanelController for device: %s\n",pAVCDevice->deviceName);
	
	[avcLogString release];
	[TapePlayButtonNormalImage release];
	[TapeStopButtonNormalImage release];
	[TapePauseButtonNormalImage release];
	[TapeFFwdButtonNormalImage release];
	[TapeFRevButtonNormalImage release];
	[TapeRecButtonNormalImage release];
	
	// If we have an AVCDeviceCommandInterface, delete it now!
	if (pAVCDeviceCommandInterface)
	{
		delete pAVCDeviceCommandInterface;
		pAVCDeviceCommandInterface = nil;
	}
	
	// Remove a pointer to this control-panel object from the associated AVCDevice (to allow for future control-panel creation)
	pAVCDevice->SetClientPrivateData(0);
		
	[super dealloc];
}

//////////////////////////////////////////////////////
// awakeFromNib
//////////////////////////////////////////////////////
- (void)awakeFromNib
{
	NSBundle *appBundle = [NSBundle mainBundle];

	unsigned int i;
	CFMutableDictionaryRef matchingDict;
	CFNumberRef GUIDDesc;
	CFNumberRef SpecIDDesc;
	CFNumberRef SWVersDesc;
	io_object_t eia775Unit ;
	UInt64 guid;
	SInt32 specID = 0x5068;
	SInt32 swVers = 0x10101;
	
	[GUID setStringValue:[NSString stringWithFormat:@"0x%016llX",pAVCDevice->guid]];
	[openedByThisApp setStringValue:@"No"];	
	[openCloseDeviceButton setTitle:kOpenDeviceButtonOpenString];
	
	[inputPlugConnectButton setEnabled:NO];
	[inputPlugDisconnectButton setEnabled:NO];
	[outputPlugConnectButton setEnabled:NO];
	[outputPlugDisconnectButton setEnabled:NO];
	[rereadPlugsButton setEnabled:NO];
	[PollPlugRegistersButton setEnabled:NO];
		
	[deviceControlPanelWindow setTitle:[NSString stringWithFormat: @"AV/C Device-Control Panel: %s",pAVCDevice->deviceName]];

	[subunitInfoPage setIntValue: 0];
	[outputPlugSigFmtPlugNum setIntValue: 0];
	[inputPlugSigFmtPlugNum setIntValue: 0];
	
	for (i=1;i<64;i++)
	{
		[inputPlugChannel addItemWithTitle:[NSString stringWithFormat:@"%d",i]];
		[outputPlugChannel addItemWithTitle:[NSString stringWithFormat:@"%d",i]];
	}
	
	avcLogString = [[NSMutableString stringWithCapacity:4096] retain];
	[avcLog setString:avcLogString];
	
	// Enable or Disable EIA-775 Info Button, based on whether or not
	// this device has a EIA-775 unit directory in its config ROM
	matchingDict = IOServiceMatching("IOFireWireUnit");
	guid = pAVCDevice->guid;
	GUIDDesc = CFNumberCreate(nil,kCFNumberSInt64Type,&guid);
	
	SpecIDDesc = CFNumberCreate(nil,kCFNumberSInt32Type,&specID);
	SWVersDesc = CFNumberCreate(nil,kCFNumberSInt32Type,&swVers);
	
	CFDictionarySetValue(matchingDict, CFSTR("GUID"), GUIDDesc);
	CFDictionarySetValue(matchingDict, CFSTR("Unit_Spec_ID"), SpecIDDesc);
	CFDictionarySetValue(matchingDict, CFSTR("Unit_SW_Version"), SWVersDesc);
	eia775Unit = IOServiceGetMatchingService(kIOMasterPortDefault,matchingDict);
	if (eia775Unit)
	{
		NSLog(@"Found EIA-775 Unit Directory on Device\n");
		[eia775Info setEnabled:YES];
	}
	else
	{
		[eia775Info setEnabled:NO];
	}
	
	CFRelease(GUIDDesc);
	CFRelease(SpecIDDesc);
	CFRelease(SWVersDesc);
	
	numInputPCRs = 0;
	numOutputPCRs = 0;
	[self rereadPlugs:self];
	
	// Initialize Tape Control Button Images
	TapePlayButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Normal" ofType: @"tif"]];
	TapeStopButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Normal" ofType: @"tif"]];
	TapePauseButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Normal" ofType: @"tif"]];
	TapeFFwdButtonNormalImage  = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"FastForwardButton-Normal" ofType: @"tif"]];
	TapeFRevButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"RewindButton-Normal" ofType: @"tif"]];
	TapeRecButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-0N" ofType: @"tiff"]];
	
	// Assign button images to tape controller buttons
	[TapePlayButton setImage:TapePlayButtonNormalImage];
	[TapeStopButton setImage:TapeStopButtonNormalImage];
	[TapePauseButton setImage:TapePauseButtonNormalImage];
	[TapeFFwdButton setImage:TapeFFwdButtonNormalImage];
	[TapeFRevButton setImage:TapeFRevButtonNormalImage];
	[TapeRecButton setImage:TapeRecButtonNormalImage];
	
	// Select a particular tab view
	[deviceControlPanelTabView selectTabViewItemAtIndex: kTabViewItemIndex_General];
	
	[ViewerButton setTitle:kViewerButtonStartText];
	pAVCDeviceStream = nil;
	viewerSocket = 0;
	viewerTask = nil;

	// Start a repeating timer to handle polling
	userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:kAVCDeviceControlPanelPlugPollingInterval target:self selector:@selector(userInterfaceUpdateTimerExpired:) userInfo:nil repeats:YES];
}	

//////////////////////////////////////////////////////
// windowWillClose
//////////////////////////////////////////////////////
- (void)windowWillClose:(NSNotification *)aNotification
{
	// If the device was left opened by this control-panel, we need to close it now!
	if (pAVCDevice->isOpened())
	{
		// If viewer is active, we need to tear it down now
		if ([[ViewerButton title] isEqualTo:kViewerButtonStopText] == YES)
			[self ViewerButtonPushed:self];

		pAVCDevice->closeDevice();
	}
		
	// Disable the timer
	[userInterfaceUpdateTimer invalidate];

	// Release this control-panel object!
	[self release];
}

//////////////////////////////////////////////////////
// WindowDeminiaturizeAndBringToFront
//////////////////////////////////////////////////////
-(void)WindowDeminiaturizeAndBringToFront
{
	[deviceControlPanelWindow deminiaturize:self];
}

//////////////////////////////////////////////////////
// userInterfaceUpdateTimerExpired
//////////////////////////////////////////////////////
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer
{
	// Disable polling, if the device is not attached
	if (!pAVCDevice->isAttached)
	{
		[PollPlugRegistersButton setState:false];		
		[PollTapeSubunitButton setState:false];		
	}
	else
	{
		// If the device is attached, make sure we have a valid AVCDeviceCommandInterface
		// This ensures that we will get bus-reset notifications, as well as device disconnected
		// notifications.
		[self GetAVCDeviceCommandInterface];
	}
	
	// Do different things depending on which tab is visible
	switch ([deviceControlPanelTabView indexOfTabViewItem:[deviceControlPanelTabView selectedTabViewItem]])
	{
		case kTabViewItemIndex_General:
			break;
			
		case kTabViewItemIndex_Plug:
			if ((pAVCDevice->isOpened()) && ([PollPlugRegistersButton state]))
				[self rereadPlugs:self];
			break;

		case kTabViewItemIndex_Tape:
			if ((pAVCDevice->isAttached) && ([PollTapeSubunitButton state]))
			{
				[TapeTransportState setEnabled:YES];
				[TapeMediumInfoState setEnabled:YES];
				[TapeTimeCodeState setEnabled:YES];
				[self PollTapeStatus];
			}
			else
			{
				[TapeTransportState setEnabled:NO];
				[TapeMediumInfoState setEnabled:NO];
				[TapeTimeCodeState setEnabled:NO];
			}
			break;

		case kTabViewItemIndex_CEA:
			break;

		default:
			break;
	}
	
	// If we have a viewer task active, make sure it's still running
	// If not, tear down the mpeg receiver, etc.
	if ((viewerTask) && (![viewerTask isRunning]))
	{
		[self ViewerButtonPushed:self];
	}
}	

//////////////////////////////////////////////////////
// openCloseDeviceButtonPushed
//////////////////////////////////////////////////////
- (IBAction)openCloseDeviceButtonPushed:(id)sender
{
	IOReturn result;
	
	if (pAVCDevice->isOpened() == false)
	{
		// Attempt to open the device!
		result = pAVCDevice->openDevice(MyAVCDeviceMessageNotification,self);
		if (result == kIOReturnSuccess)
		{
			[openedByThisApp setStringValue:@"Yes"];	
			
			[inputPlugConnectButton setEnabled:YES];
			[inputPlugDisconnectButton setEnabled:YES];
			[outputPlugConnectButton setEnabled:YES];
			[outputPlugDisconnectButton setEnabled:YES];
			[rereadPlugsButton setEnabled:YES];
			[PollPlugRegistersButton setEnabled:YES];
			
			[openCloseDeviceButton setTitle:kOpenDeviceButtonCloseString];
			
			[self addToAVCLog:[NSString stringWithFormat:@"Device opened successfully.\n\n"]];
			
			// Read the current PCRs and update the tables
			[self rereadPlugs:self];
		}
		else
		{
			// Report the error via the log!
			[self addToAVCLog:[NSString stringWithFormat:@"Error: unable to open device. Result = 0x%08X\n\n",result]];
			
			[openedByThisApp setStringValue:@"No"];	
			
			[inputPlugConnectButton setEnabled:NO];
			[inputPlugDisconnectButton setEnabled:NO];
			[outputPlugConnectButton setEnabled:NO];
			[outputPlugDisconnectButton setEnabled:NO];
			[rereadPlugsButton setEnabled:NO];
			[PollPlugRegistersButton setEnabled:NO];
			
			[openCloseDeviceButton setTitle:kOpenDeviceButtonOpenString];
		}
	}
	else
	{
		// If viewer is active, we need to tear it down now
		if ([[ViewerButton title] isEqualTo:kViewerButtonStopText] == YES)
			[self ViewerButtonPushed:self];
		
		// Close the device
		pAVCDevice->closeDevice();
		
		[openedByThisApp setStringValue:@"No"];	
		
		[inputPlugConnectButton setEnabled:NO];
		[inputPlugDisconnectButton setEnabled:NO];
		[outputPlugConnectButton setEnabled:NO];
		[outputPlugDisconnectButton setEnabled:NO];
		[rereadPlugsButton setEnabled:NO];
		[PollPlugRegistersButton setEnabled:NO];
		
		[openCloseDeviceButton setTitle:kOpenDeviceButtonOpenString];
		
		[self addToAVCLog:[NSString stringWithFormat:@"Device closed successfully.\n\n"]];
		
		// Make sure we clear-out the iPCR/oPCR tables
		numInputPCRs = 0;
		numOutputPCRs = 0;
		[self rereadPlugs:self]; // This will cause the table-data to reload.
	}
}

//////////////////////////////////////////////////////
// sendAVCCommandBytes
//////////////////////////////////////////////////////
- (IBAction)sendAVCCommandBytes:(id)sender
{
    UInt32 cmdSize = 0;
    UInt32 respSize = 512;
    UInt8 cmd[512],response[512];
    IOReturn res;
	NSString *bytesString = [avcCommandBytes stringValue];
	UInt32 strLen = [bytesString length];
	UInt32 i;
	unichar hexByteStr[3];
	UInt8 hexByteVal;
	NSRange strRange;
	int c;
	unichar *s;
	
	// Parse the command bytes string to determine the command
	strRange.length=2;
	for (i=0;i<(strLen/2);i++)
	{
		strRange.location = i*2;
		[bytesString getCharacters:hexByteStr range:strRange];
		hexByteStr[2] = 0;
		hexByteVal = 0;
		s = hexByteStr;
		while(isxdigit(c = *s))
		{
			hexByteVal *= 16;
			if(c <= '9')
				hexByteVal += c - '0';
			else
				hexByteVal += (c & 0x5F) - 'A' + 10;
			s++;
		}
		cmd[cmdSize] = hexByteVal;
		cmdSize += 1;
	}
	
	if (cmdSize < 1)
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Invalid AV/C command bytes: %@\n\n",bytesString]];
		return;
	}
	
	respSize = 512;
	res = DoAVCTransaction(cmd, cmdSize, response, &respSize,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// GetAVCDeviceCommandInterface
//////////////////////////////////////////////////////
-(AVCDeviceCommandInterface*)GetAVCDeviceCommandInterface
{
	IOReturn result;
	
	// If we haven't already created a AVCDeviceCommandInterface for this AVCDevice, create it now!
	if (!pAVCDeviceCommandInterface)
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Creating AVCDeviceCommandInterface.\n\n"]];

		pAVCDeviceCommandInterface = new AVCDeviceCommandInterface(pAVCDevice);
		if (pAVCDeviceCommandInterface)
		{
			result = pAVCDeviceCommandInterface->activateAVCDeviceCommandInterface(MyAVCDeviceCommandInterfaceMessageNotification,self);
			if (result != kIOReturnSuccess)
			{
				[self addToAVCLog:[NSString stringWithFormat:@"Error: Couldn't activate AVCDevice command interface\n\n"]];
				delete pAVCDeviceCommandInterface;
				pAVCDeviceCommandInterface = nil;
			}
		}
		else
			[self addToAVCLog:[NSString stringWithFormat:@"Error: Couldn't create AVCDevice command interface\n\n"]];
	}
	
	return pAVCDeviceCommandInterface;
}

//////////////////////////////////////////////////////
// GetAVCDevice
//////////////////////////////////////////////////////
-(AVCDevice*)GetAVCDevice
{
	return pAVCDevice;
}

//////////////////////////////////////////////////////
// isAVCDeviceOpenedByThisApp
//////////////////////////////////////////////////////
-(bool)isAVCDeviceOpenedByThisApp
{
	return pAVCDevice->isOpened();
}

//////////////////////////////////////////////////////
// DeviceHasGoneAway
//////////////////////////////////////////////////////
-(void)DeviceHasGoneAway
{
	if (pAVCDevice->isOpened())
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Device was disconnected while open. Closing now...\n\n"]];
		[self openCloseDeviceButtonPushed:self];
	}
	else
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Device was disconnected.\n\n"]];
	}
	
	// If we have an AVCDeviceCommandInterface, delete it now!
	if (pAVCDeviceCommandInterface)
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Destroying AVCDeviceCommandInterface.\n\n"]];
		delete pAVCDeviceCommandInterface;
		pAVCDeviceCommandInterface = nil;
	}
}

#pragma mark -----------------------------------
#pragma mark Logging Methods
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// updateAVCCommandBytesView
//////////////////////////////////////////////////////
-(void)updateAVCCommandBytesView:(NSString*)commandByteString
{
	[avcCommandBytes setStringValue:commandByteString];
}

//////////////////////////////////////////////////////
// clearLog
//////////////////////////////////////////////////////
- (IBAction)clearLog:(id)sender
{
	// Start over with an empty log string
	[avcLogString autorelease];
	avcLogString = [[NSMutableString stringWithCapacity:4096] retain];
	[avcLog setString:avcLogString];
}

//////////////////////////////////////////////////////
// addToAVCLog
//////////////////////////////////////////////////////
- (void) addToAVCLog:(NSString*)string
{
	NSRange strRange;
	unsigned int strLen;
	
	[avcLogString appendString:string];
	[avcLog setString:avcLogString];
	
	// Set the range to point to the end of the string
	strRange.length=1;
	strLen = [avcLogString length];
	strRange.location=(strLen > 0) ? strLen-1 : 0;
	
	// Scroll the view to the end
	[avcLog scrollRangeToVisible:strRange];	
}

//////////////////////////////////////////////////////
// LogBusResetMessage
//////////////////////////////////////////////////////
-(void)LogBusResetMessage
{
	[self addToAVCLog:[NSString stringWithFormat:@"Bus-reset detected!\n\n"]];
}

#pragma mark -----------------------------------
#pragma mark Buttons on Plug Tab
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// makeInputPlugConnection
//////////////////////////////////////////////////////
- (IBAction)makeInputPlugConnection:(id)sender
{
	int plug = [InputPlugsTable selectedRow];
	int channel = [inputPlugChannel indexOfSelectedItem];
	UInt32 oldVal;
	UInt32 newVal;
	FWAddress addr;
	IOReturn status;
	UInt32 currentCount;
	io_object_t obj;
	IOReturn result;
	
	if (pAVCDevice->isOpened())
	{
		// Make sure something is selected
		if ((plug < 0) && (numInputPCRs > 0))
		{
			[InputPlugsTable selectRow:0 byExtendingSelection:NO];
			plug = 0;
		}
		
		if (plug >= 0)
		{
			// Read the current value of the plug
			addr.nodeID = 0;
			addr.addressHi = 0xffff;
			addr.addressLo = 0xf0000984 + (4*plug);
			obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
			result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &oldVal, false, 0);
			oldVal = EndianU32_BtoN(oldVal);
			if (result == kIOReturnSuccess)
			{
				currentCount = ((oldVal & 0x3F000000) >> 24);
				
				if (currentCount == 63)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Error: input plug %d already at maximum connection count\n\n",plug]];
					[self rereadPlugs:self];
					return;
				}
				else
				{
					// Create new Value
					newVal = oldVal & 0xFFC03FFF;
					newVal |= (channel << 16);
					newVal += (1 << 24);
					
					addr.nodeID = 0;
					addr.addressHi = 0xffff;
					addr.addressLo = 0xf0000984 + (4*plug);
					obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
					result = (*(pAVCDevice->deviceInterface))->CompareSwap(pAVCDevice->deviceInterface, 
																		   obj, 
																		   &addr, 
																		   EndianU32_NtoB(oldVal), 
																		   EndianU32_NtoB(newVal), 
																		   false, 
																		   0);
					if (result == kIOReturnSuccess)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Compare-swap to input plug %d successful. OldVal=0x%08X NewVal=0x%08X\n\n",plug,oldVal,newVal]];	
					}
					else
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error trying to connect to input plug %d: 0x%08X\n\n",plug,status]];
					}
				}
			}
			else
			{
				[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading input plug %d\n\n",plug,status]];
			}
		}
		else
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error: No input plug selected\n\n"]];
		}
	}
	
	[self rereadPlugs:self];
	return;
}
//////////////////////////////////////////////////////
// breakInputPlugConnection
//////////////////////////////////////////////////////
- (IBAction)breakInputPlugConnection:(id)sender
{
	int plug = [InputPlugsTable selectedRow];
	UInt32 oldVal;
	UInt32 newVal;
	FWAddress addr;
	IOReturn status;
	UInt32 currentCount;
	io_object_t obj;
	IOReturn result;
	
	if (pAVCDevice->isOpened())
	{
		// Make sure something is selected
		if ((plug < 0) && (numInputPCRs > 0))
		{
			[InputPlugsTable selectRow:0 byExtendingSelection:NO];
			plug = 0;
		}
		
		if (plug >= 0)
		{
			// Read the current value of the plug
			addr.nodeID = 0;
			addr.addressHi = 0xffff;
			addr.addressLo = 0xf0000984 + (4*plug);
			obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
			result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &oldVal, false, 0);
			oldVal = EndianU32_BtoN(oldVal);
			if (result == kIOReturnSuccess)
			{
				currentCount = ((oldVal & 0x3F000000) >> 24);
				
				if (currentCount == 0)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Error: input plug %d has no connections\n\n",plug]];
					[self rereadPlugs:self];
					return;
				}
				else
				{
					// Create new Value
					newVal = oldVal & 0xFFC03FFF;
					newVal = oldVal - (1 << 24);
					
					addr.nodeID = 0;
					addr.addressHi = 0xffff;
					addr.addressLo = 0xf0000984 + (4*plug);
					obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
					result = (*(pAVCDevice->deviceInterface))->CompareSwap(pAVCDevice->deviceInterface, 
																		   obj, 
																		   &addr, 
																		   EndianU32_NtoB(oldVal), 
																		   EndianU32_NtoB(newVal), 
																		   false, 
																		   0);
					if (result == kIOReturnSuccess)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Compare-swap to input plug %d successful. OldVal=0x%08X NewVal=0x%08X\n\n",plug,oldVal,newVal]];	
					}
					else
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error trying to disconnect from input plug %d: 0x%08X\n\n",plug,status]];
					}
				}
			}
			else
			{
				[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading input plug %d\n\n",plug,status]];
			}
		}
		else
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error: No input plug selected\n\n"]];
		}
	}
	
	[self rereadPlugs:self];
	return;
}
//////////////////////////////////////////////////////
// makeOutputPlugConnection
//////////////////////////////////////////////////////
- (IBAction)makeOutputPlugConnection:(id)sender
{
	int plug = [OutputPlugsTable selectedRow];
	int channel = [outputPlugChannel indexOfSelectedItem];
	int rate =  [outputPlugRate indexOfSelectedItem];
	UInt32 oldVal;
	UInt32 newVal;
	FWAddress addr;
	IOReturn status;
	UInt32 currentCount;
	io_object_t obj;
	IOReturn result;

	if (pAVCDevice->isOpened())
	{
		// Make sure something is selected
		if ((plug < 0) && (numOutputPCRs > 0))
		{
			[OutputPlugsTable selectRow:0 byExtendingSelection:NO];
			plug = 0;
		}
		
		if (plug >= 0)
		{
			// Read the current value of the plug
			addr.nodeID = 0;
			addr.addressHi = 0xffff;
			addr.addressLo = 0xf0000904 + (4*plug);
			obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
			result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &oldVal, false, 0);
			oldVal = EndianU32_BtoN(oldVal);
			if (result == kIOReturnSuccess)
			{
				currentCount = ((oldVal & 0x3F000000) >> 24);
				
				if (currentCount == 63)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Error: output plug %d already at maximum connection count\n\n",plug]];
					[self rereadPlugs:self];
					return;
				}
				else
				{
					// Create new Value
					newVal = oldVal & 0xFFC03FFF;
					newVal |= (channel << 16);
					newVal |= (rate << 14);
					newVal += (1 << 24);
					
					addr.nodeID = 0;
					addr.addressHi = 0xffff;
					addr.addressLo = 0xf0000904 + (4*plug);
					obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
					result = (*(pAVCDevice->deviceInterface))->CompareSwap(pAVCDevice->deviceInterface, 
																		   obj, 
																		   &addr, 
																		   EndianU32_NtoB(oldVal), 
																		   EndianU32_NtoB(newVal), 
																		   false, 
																		   0);
					if (result == kIOReturnSuccess)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Compare-swap to output plug %d successful. OldVal=0x%08X NewVal=0x%08X\n\n",plug,oldVal,newVal]];	
					}
					else
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error trying to connect to output plug %d: 0x%08X\n\n",plug,status]];
					}
				}
			}
			else
			{
				[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading output plug %d\n\n",plug,status]];
			}
		}
		else
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error: No output plug selected\n\n"]];
		}
	}
	
	[self rereadPlugs:self];
	return;
}

//////////////////////////////////////////////////////
// breakOutputPlugConnection
//////////////////////////////////////////////////////
- (IBAction)breakOutputPlugConnection:(id)sender
{
	int plug = [OutputPlugsTable selectedRow];
	UInt32 oldVal;
	UInt32 newVal;
	FWAddress addr;
	IOReturn status;
	UInt32 currentCount;
	io_object_t obj;
	IOReturn result;
	
	if (pAVCDevice->isOpened())
	{
		// Make sure something is selected
		if ((plug < 0) && (numOutputPCRs > 0))
		{
			[OutputPlugsTable selectRow:0 byExtendingSelection:NO];
			plug = 0;
		}
		
		if (plug >= 0)
		{
			// Read the current value of the plug
			addr.nodeID = 0;
			addr.addressHi = 0xffff;
			addr.addressLo = 0xf0000904 + (4*plug);
			obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
			result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &oldVal, false, 0);
			oldVal = EndianU32_BtoN(oldVal);
			if (result == kIOReturnSuccess)
			{
				currentCount = ((oldVal & 0x3F000000) >> 24);
				
				if (currentCount == 0)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Error: output plug %d has no connections\n\n",plug]];
					[self rereadPlugs:self];
					return;
				}
				else
				{
					// Create new Value
					newVal = oldVal & 0xFFC03FFF;
					newVal = oldVal - (1 << 24);
					
					addr.nodeID = 0;
					addr.addressHi = 0xffff;
					addr.addressLo = 0xf0000904 + (4*plug);
					obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
					result = (*(pAVCDevice->deviceInterface))->CompareSwap(pAVCDevice->deviceInterface, 
																		   obj, 
																		   &addr, 
																		   EndianU32_NtoB(oldVal), 
																		   EndianU32_NtoB(newVal), 
																		   false, 
																		   0);
					if (result == kIOReturnSuccess)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Compare-swap to output plug %d successful. OldVal=0x%08X NewVal=0x%08X\n\n",plug,oldVal,newVal]];	
					}
					else
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error trying to disconnect to output plug %d: 0x%08X\n\n",plug,status]];
					}
				}
			}
			else
			{
				[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading output plug %d\n\n",plug,status]];
			}
		}
		else
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error: No output plug selected\n\n"]];
		}
	}
	
	[self rereadPlugs:self];
	return;
}
//////////////////////////////////////////////////////
// rereadPlugs
//////////////////////////////////////////////////////
- (IBAction)rereadPlugs:(id)sender
{
	IOReturn result;
	UInt32 plugVal;
	io_object_t obj;
	FWAddress addr;
	UInt32 i;
	
	[InputPlugsCount setStringValue:@""];
	[OutputPlugsCount setStringValue:@""];
	
	if (pAVCDevice->isOpened())
	{
		// Read the oMPR
		addr.nodeID = 0;
		addr.addressHi = 0xffff;
		addr.addressLo = 0xf0000900;
		obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
		result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &plugVal, false, 0);
		plugVal = EndianU32_BtoN(plugVal);
		if (result == kIOReturnSuccess)
		{
			numOutputPCRs = (plugVal & 0x1F);
			[OutputPlugsCount setIntValue:numOutputPCRs];
			
			// Read the oPCRs
			for (i=0;i<numOutputPCRs;i++)
			{
				addr.nodeID = 0;
				addr.addressHi = 0xffff;
				addr.addressLo = 0xf0000904 + (4*i);
				obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
				result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &plugVal, false, 0);
				plugVal = EndianU32_BtoN(plugVal);
				if (result == kIOReturnSuccess)
				{
					oPCRValues[i].online = ((plugVal & 0x80000000) >> 31);
					oPCRValues[i].broadcast = ((plugVal & 0x40000000) >> 30);
					oPCRValues[i].p2pCount = ((plugVal & 0x3F000000) >> 24);
					oPCRValues[i].channel = ((plugVal & 0x003F0000) >> 16);
					oPCRValues[i].rate = ((plugVal & 0x0000C000) >> 14);
					oPCRValues[i].overhead = ((plugVal & 0x00003C00) >> 10);
					oPCRValues[i].payloadInQuads = (plugVal & 0x000003FF);
				}
				else
				{
					// Got an error reading one of the plugs.
					numOutputPCRs = i-1;
					[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading output plug register %d\n\n",result,i]];
					break;
				}
			}
		}
		else
		{
			numOutputPCRs = 0;
			[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading output master plug Register\n\n",result]];
		}
		
		// Read the iMPR
		addr.nodeID = 0;
		addr.addressHi = 0xffff;
		addr.addressLo = 0xf0000980;
		obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
		result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &plugVal, false, 0);
		plugVal = EndianU32_BtoN(plugVal);
		if (result == kIOReturnSuccess)
		{
			numInputPCRs = (plugVal & 0x1F);
			[InputPlugsCount setIntValue:numInputPCRs];
			
			// Read the iPCRs
			for (i=0;i<numInputPCRs;i++)
			{
				addr.nodeID = 0;
				addr.addressHi = 0xffff;
				addr.addressLo = 0xf0000984 + (4*i);
				obj = (*(pAVCDevice->deviceInterface))->GetDevice(pAVCDevice->deviceInterface);
				result = (*(pAVCDevice->deviceInterface))->ReadQuadlet(pAVCDevice->deviceInterface, obj, &addr, &plugVal, false, 0);
				plugVal = EndianU32_BtoN(plugVal);
				if (result == kIOReturnSuccess)
				{
					iPCRValues[i].online = ((plugVal & 0x80000000) >> 31);
					iPCRValues[i].broadcast = ((plugVal & 0x40000000) >> 30);
					iPCRValues[i].p2pCount = ((plugVal & 0x3F000000) >> 24);
					iPCRValues[i].channel = ((plugVal & 0x003F0000) >> 16);
				}
				else
				{
					// Got an error reading one of the plugs.
					numInputPCRs = i-1;
					[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading input plug register %d\n\n",result,i]];
					break;
				}
			}
		}
		else
		{
			numInputPCRs = 0;
			[self addToAVCLog:[NSString stringWithFormat:@"Error 0x%08X reading input master plug register\n\n",result]];
		}
	}

	
	[InputPlugsTable reloadData];
	[OutputPlugsTable reloadData];
}

#pragma mark -----------------------------------
#pragma mark Buttons on General Tab
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// UnitInfoCommand
//////////////////////////////////////////////////////
- (IBAction)UnitInfoCommand:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x30;
	cmd[3] = 0xFF;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
}

//////////////////////////////////////////////////////
// PlugInfoCommand
//////////////////////////////////////////////////////
- (IBAction)PlugInfoCommand:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x02;
	cmd[3] = 0x00;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// SubunitInfoCommand
//////////////////////////////////////////////////////
- (IBAction)SubunitInfoCommand:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	unsigned int page = [subunitInfoPage intValue];
	
	if ((page < 0) || (page > 7))
	{
		page = 0;
		[subunitInfoPage setIntValue:0];
	}
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x31;
	cmd[3] = (page << 4) + 0x07;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// outputPlugSigFmtCommand
//////////////////////////////////////////////////////
- (IBAction)outputPlugSigFmtCommand:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	unsigned int plug = [outputPlugSigFmtPlugNum intValue];
	
	if ((plug < 0) || (plug > 31))
	{
		plug = 0;
		[outputPlugSigFmtPlugNum setIntValue:0];
	}
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x18;
	cmd[3] = plug;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// inputPlugSigFmtCommand
//////////////////////////////////////////////////////
- (IBAction)inputPlugSigFmtCommand:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	unsigned int plug = [inputPlugSigFmtPlugNum intValue];
	
	if ((plug < 0) || (plug > 31))
	{
		plug = 0;
		[inputPlugSigFmtPlugNum setIntValue:0];
	}
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x19;
	cmd[3] = plug;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

#pragma mark -----------------------------------
#pragma mark Buttons on CEA 775/931 Tab
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// getEIA775Info
//////////////////////////////////////////////////////
- (IBAction)getEIA775Info:(id)sender
{
	
	// Local Vars
	IOReturn result;
	UInt32 size;
    UInt8 cmd[kAVCCommandBufSize],response[kAVCCommandBufSize];
	UInt8 descriptorResponse[KAVCDescriptorResponseBufSize];
	UInt32 descriptorResponseSize;
	UInt8 *pDescriptor;
	UInt8 *pInfoBlock;
	UInt16 allInfoBlocksLen;
	UInt16 thisInfoBlockLen;
	UInt16 descriptorLen; 
	UInt16 remainingInfoBlockBytes;
	UInt16 infoBlockType;
	UInt16 fieldsLen;
	UInt32 i;
	
	do
	{
		// Open Descriptor (for UID)
		cmd[0] = kAVCControlCommand;
		cmd[1] = 0xFF;
		cmd[2] = 0x08;
		cmd[3] = 0x00;
		cmd[4] = 0x01;
		cmd[5] = 0x00;
		size = 6;
		result = DoAVCTransaction(cmd, 6, response, &size,self,false,false);
		
		if (!((result == kIOReturnSuccess) && (response[0] == kAVCAcceptedStatus)))
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error opening EIA-775 unit-identifer descriptor\n\n"]];
			break;
		}
								
		// Read Descriptor
		cmd[0] = kAVCControlCommand;
		cmd[1] = 0xFF;
		cmd[2] = 0x09;
		cmd[3] = 0x00;
		cmd[4] = 0xFF;
		cmd[5] = 0x00;
		cmd[6] = 0x00;
		cmd[7] = 0x00;
		cmd[8] = 0x00;
		cmd[9] = 0x00;
		descriptorResponseSize = KAVCDescriptorResponseBufSize;
		result = DoAVCTransaction(cmd, 10, descriptorResponse, &descriptorResponseSize,self,false,false);
		
		if (!((result == kIOReturnSuccess) && (descriptorResponse[0] == kAVCAcceptedStatus)))
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error reading EIA-775 unit-identifer descriptor\n\n"]];
			break;
		}
		
		// Close Descriptor
		cmd[0] = kAVCControlCommand;
		cmd[1] = 0xFF;
		cmd[2] = 0x08;
		cmd[3] = 0x00;
		cmd[4] = 0x00;
		cmd[5] = 0x00;
		size = 6;
		result = DoAVCTransaction(cmd, 6, response, &size,self,false,false);
		
		if (!((result == kIOReturnSuccess) && (response[0] == kAVCAcceptedStatus)))
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Error closing EIA-775 unit-identifer descriptor\n\n"]];
		}
		
		[self addToAVCLog:[NSString stringWithFormat:@"EIA-775 unit-identifier descriptor:\n\n"]];
		
		// Parse Descriptor Bytes
		pDescriptor = &descriptorResponse[10];
		descriptorLen = (((UInt16)pDescriptor[0] << 8) | pDescriptor[1]);
		[self addToAVCLog:[NSString stringWithFormat:@"Unit-identifier descriptor length: %d\n",descriptorLen]];
		[self addToAVCLog:[NSString stringWithFormat:@"Generation ID: %d\n",pDescriptor[2]]];
		[self addToAVCLog:[NSString stringWithFormat:@"Size of list-ID: %d\n",pDescriptor[3]]];
		[self addToAVCLog:[NSString stringWithFormat:@"Size of object-ID: %d\n",pDescriptor[4]]];
		[self addToAVCLog:[NSString stringWithFormat:@"Size of object position: %d\n",pDescriptor[5]]];
		[self addToAVCLog:[NSString stringWithFormat:@"Number of root-object lists: %d\n",(((UInt16)pDescriptor[6] << 8) | pDescriptor[7])]];
		[self addToAVCLog:[NSString stringWithFormat:@"Unit-dependent length: %d\n",(((UInt16)pDescriptor[8] << 8) | pDescriptor[9])]];
		[self addToAVCLog:[NSString stringWithFormat:@"Well-defined-fields length: %d\n",(((UInt16)pDescriptor[10] << 8) | pDescriptor[11])]];
		allInfoBlocksLen = ((((UInt16)pDescriptor[8] << 8) | pDescriptor[9]) - 2);
		if (pDescriptor[3] == 0)
			pInfoBlock = &pDescriptor[12];
		else
			pInfoBlock = &pDescriptor[12 + (pDescriptor[3] * (((UInt16)pDescriptor[6] << 8) | pDescriptor[7]))];
		
		remainingInfoBlockBytes = allInfoBlocksLen;
		while (remainingInfoBlockBytes > 0)
		{
			thisInfoBlockLen = (((UInt16)pInfoBlock[0] << 8) | pInfoBlock[1]);
			[self addToAVCLog:[NSString stringWithFormat:@"\nInfo-block len: %d\n",thisInfoBlockLen]];
			infoBlockType = (((UInt16)pInfoBlock[2] << 8) | pInfoBlock[3]);
			[self addToAVCLog:[NSString stringWithFormat:@"Info-block type: %d\n",infoBlockType]];
			fieldsLen = (((UInt16)pInfoBlock[4] << 8) | pInfoBlock[5]);
			[self addToAVCLog:[NSString stringWithFormat:@"Fields length: %d\n",fieldsLen]];
			
			if (infoBlockType == 0)
			{
				if (fieldsLen > 5)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Specifier ID: 0x%02X%02X%02X\n",pInfoBlock[6],pInfoBlock[7],pInfoBlock[8]]];
					if ((pInfoBlock[6] == 0x00) && (pInfoBlock[7] == 0x50) && (pInfoBlock[8] == 0x68))
					{
						[self addToAVCLog:[NSString stringWithFormat:@"EIA-775 block type: %d\n",(((UInt16)pInfoBlock[9] << 8) | pInfoBlock[10])]];
						if (pInfoBlock[10] == 1)
						{
							[self addToAVCLog:[NSString stringWithFormat:@"EIA-775 plug-info block, version: %d\n\n",pInfoBlock[11]]];
							[self addToAVCLog:[NSString stringWithFormat:@"OSD input-plug: 0x%02X\n",pInfoBlock[12]]];
							[self addToAVCLog:[NSString stringWithFormat:@"OSD output-plug: 0x%02X\n",pInfoBlock[13]]];
							[self addToAVCLog:[NSString stringWithFormat:@"Analog input-plug: 0x%02X\n",pInfoBlock[14]]];
							[self addToAVCLog:[NSString stringWithFormat:@"Analog output-plug: 0x%02X\n",pInfoBlock[15]]];
							[self addToAVCLog:[NSString stringWithFormat:@"Digital input-plug: 0x%02X\n",pInfoBlock[16]]];
							[self addToAVCLog:[NSString stringWithFormat:@"Digital output-plug: 0x%02X\n",pInfoBlock[17]]];
							[self addToAVCLog:[NSString stringWithFormat:@"Transport-stream input formats: "]];
							if (pInfoBlock[21] & 0x01)
								[self addToAVCLog:[NSString stringWithFormat:@"MPEG-2 "]];
							if (pInfoBlock[21] & 0x02)
								[self addToAVCLog:[NSString stringWithFormat:@"DV "]];
							if (pInfoBlock[21] & 0x04)
								[self addToAVCLog:[NSString stringWithFormat:@"DirectTV "]];
							if (pInfoBlock[21] & 0xF8)
								[self addToAVCLog:[NSString stringWithFormat:@"Other "]];
							[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
							[self addToAVCLog:[NSString stringWithFormat:@"Transport-stream output formats: "]];
							if (pInfoBlock[25] & 0x01)
								[self addToAVCLog:[NSString stringWithFormat:@"MPEG-2 "]];
							if (pInfoBlock[25] & 0x02)
								[self addToAVCLog:[NSString stringWithFormat:@"DV "]];
							if (pInfoBlock[25] & 0x04)
								[self addToAVCLog:[NSString stringWithFormat:@"DirectTV "]];
							if (pInfoBlock[25] & 0xF8)
								[self addToAVCLog:[NSString stringWithFormat:@"Other "]];
							[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
						}
						else if (pInfoBlock[10] == 2)
						{
							[self addToAVCLog:[NSString stringWithFormat:@"EIA-775 DTV info-block, profile-level: %d ",pInfoBlock[11]]];
							switch (pInfoBlock[11])
							{
								case 0:
									[self addToAVCLog:[NSString stringWithFormat:@"(Profile A)"]];
									break;
								case 1:
									[self addToAVCLog:[NSString stringWithFormat:@"(Profile B)"]];
									break;
								case 255:
									[self addToAVCLog:[NSString stringWithFormat:@"(Ala-carte)"]];
									break;
								default:
									[self addToAVCLog:[NSString stringWithFormat:@"(Reserved profile value)"]];
									break;
							};
							[self addToAVCLog:[NSString stringWithFormat:@"\n\n"]];
							[self addToAVCLog:[NSString stringWithFormat:@"OSD formats supported:\n"]];
							if ((pInfoBlock[12] == 0) && (pInfoBlock[13] == 0) && (pInfoBlock[14] == 0) && (pInfoBlock[15] == 0))
								[self addToAVCLog:[NSString stringWithFormat:@"    None\n"]];
							else
							{
								if (pInfoBlock[15] & 0x01)
									[self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 0, pixel format 1 %s (640x480x4, a:Y:Cb:Cr = 2:6:4:4)\n",
								  (pInfoBlock[19] & 0x01) ? "(Double Buffered)" : ""]];
								if (pInfoBlock[15] & 0x02)
									[self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 0, pixel format 2 %s (640x480x4, a:Y:Cb:Cr = 4:6:3:3)\n",
								  (pInfoBlock[19] & 0x02) ? "(Double Buffered)" : ""]];
								if (pInfoBlock[15] & 0x04)
									[self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 1, pixel format 1 %s (640x480x8, a:Y:Cb:Cr = 2:6:4:4)\n",
								  (pInfoBlock[19] & 0x04) ? "(Double Buffered)" : ""]];;
								  if (pInfoBlock[15] & 0x08)
									  [self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 1, pixel format 2 %s (640x480x8, a:Y:Cb:Cr = 4:6:3:3)\n",
									(pInfoBlock[19] & 0x08) ? "(Double Buffered)" : ""]];
								  if (pInfoBlock[15] & 0x10)
									  [self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 1, pixel format 0 %s (640x480x8, Y:Cb:Cr = 6:5:5)\n",
									(pInfoBlock[19] & 0x10) ? "(Double Buffered)" : ""]];
								  if (pInfoBlock[15] & 0x20)
									  [self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 2, pixel format 1 %s (640x480x16, a:Y:Cb:Cr = 2:6:4:4)\n",
									(pInfoBlock[19] & 0x20) ? "(Double Buffered)" : ""]];
								  if (pInfoBlock[15] & 0x40)
									  [self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 2, pixel format 2 %s (640x480x16, a:Y:Cb:Cr = 4:6:3:3)\n",
									(pInfoBlock[19] & 0x40) ? "(Double Buffered)" : ""]];
								  if (pInfoBlock[15] & 0x80)
									  [self addToAVCLog:[NSString stringWithFormat:@"    OSD layout 2, pixel format 0 %s (640x480x16, Y:Cb:Cr = 6:5:5)\n",
									(pInfoBlock[19] & 0x80) ? "(Double Buffered)" : ""]];
							}
							[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
							
							[self addToAVCLog:[NSString stringWithFormat:@"Misc features:\n"]];
							[self addToAVCLog:[NSString stringWithFormat:@"    Stretching of 640x480 grid to 14:9: %s\n",
										(pInfoBlock[22] & 0x02) ? "Yes" : "No"]];
							[self addToAVCLog:[NSString stringWithFormat:@"    Stretching of 640x480 grid to 16:9: %s\n",
										(pInfoBlock[22] & 0x04) ? "Yes" : "No"]];
							[self addToAVCLog:[NSString stringWithFormat:@"    OSD fill surround: %s\n",
										(pInfoBlock[22] & 0x08) ? "Yes" : "No"]];
							[self addToAVCLog:[NSString stringWithFormat:@"    Source-driven digital/analog selection: %s\n",
										(pInfoBlock[22] & 0x10) ? "Yes" : "No"]];
							[self addToAVCLog:[NSString stringWithFormat:@"    OSD over analog video: %s\n",
										(pInfoBlock[22] & 0x20) ? "Yes" : "No"]];
							[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
							
							[self addToAVCLog:[NSString stringWithFormat:@"Default video format: "]];
							switch (pInfoBlock[23])
							{
								case 0:
									[self addToAVCLog:[NSString stringWithFormat:@"Unknown\n"]];
									break;
								case 1:
									[self addToAVCLog:[NSString stringWithFormat:@"1920x1080 interlaced\n"]];
									break;
								case 2:
									[self addToAVCLog:[NSString stringWithFormat:@"1920x1080 progressive\n"]];
									break;
								case 3:
									[self addToAVCLog:[NSString stringWithFormat:@"1280x720 progressive\n"]];
									break;
								case 4:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (4x3) interlaced\n"]];
									break;
								case 5:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (4x3) progressive\n"]];
									break;
								case 6:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (16x9) interlaced\n"]];
									break;
								case 7:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (16x9) progressive\n"]];
									break;
								case 8:
									[self addToAVCLog:[NSString stringWithFormat:@"640x480 interlaced\n"]];
									break;
								case 9:
									[self addToAVCLog:[NSString stringWithFormat:@"640x480 progressive\n"]];
									break;
								default:
									[self addToAVCLog:[NSString stringWithFormat:@"Reserved value\n"]];
									break;
							};
							
							[self addToAVCLog:[NSString stringWithFormat:@"Analog video conversion format: "]];
							switch (pInfoBlock[24])
							{
								case 0:
									[self addToAVCLog:[NSString stringWithFormat:@"Unknown\n"]];
									break;
								case 1:
									[self addToAVCLog:[NSString stringWithFormat:@"1920x1080 interlaced\n"]];
									break;
								case 2:
									[self addToAVCLog:[NSString stringWithFormat:@"1920x1080 progressive\n"]];
									break;
								case 3:
									[self addToAVCLog:[NSString stringWithFormat:@"1280x720 progressive\n"]];
									break;
								case 4:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (4x3) interlaced\n"]];
									break;
								case 5:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (4x3) progressive\n"]];
									break;
								case 6:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (16x9) interlaced\n"]];
									break;
								case 7:
									[self addToAVCLog:[NSString stringWithFormat:@"704x480 (16x9) progressive\n"]];
									break;
								case 8:
									[self addToAVCLog:[NSString stringWithFormat:@"640x480 interlaced\n"]];
									break;
								case 9:
									[self addToAVCLog:[NSString stringWithFormat:@"640x480 progressive\n"]];
									break;
								default:
									[self addToAVCLog:[NSString stringWithFormat:@"Reserved value\n"]];
									break;
							};
							[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
							[self addToAVCLog:[NSString stringWithFormat:@"Alignment data:\n\n"]];
							for (i=0;i<9;i++)
							{
								switch (i)
								{
									case 0:
										[self addToAVCLog:[NSString stringWithFormat:@"    1920x1080 interlaced:\n"]];
										break;
									case 1:
										[self addToAVCLog:[NSString stringWithFormat:@"    1920x1080 progressive:\n"]];
										break;
									case 2:
										[self addToAVCLog:[NSString stringWithFormat:@"    1280x720 progressive:\n"]];
										break;
									case 3:
										[self addToAVCLog:[NSString stringWithFormat:@"    704x480 (4x3) interlaced:\n"]];
										break;
									case 4:
										[self addToAVCLog:[NSString stringWithFormat:@"    704x480 (4x3) progressive:\n"]];
										break;
									case 5:
										[self addToAVCLog:[NSString stringWithFormat:@"    704x480 (16x9) interlaced:\n"]];
										break;
									case 6:
										[self addToAVCLog:[NSString stringWithFormat:@"    704x480 (16x9) progressive:\n"]];
										break;
									case 7:
										[self addToAVCLog:[NSString stringWithFormat:@"    640x480 interlaced:\n"]];
										break;
									case 8:
									default:
										[self addToAVCLog:[NSString stringWithFormat:@"    640x480 progressive:\n"]];
										break;
								};
								if (pInfoBlock[25+(i*6)] & 0x80)
									[self addToAVCLog:[NSString stringWithFormat:@"      Stretching to 14:9\n"]];
								if (pInfoBlock[25+(i*6)] & 0x40)
									[self addToAVCLog:[NSString stringWithFormat:@"      Stretching to 16:9\n"]];
								if (pInfoBlock[25+(i*6)] & 0x10)
									[self addToAVCLog:[NSString stringWithFormat:@"      Display as interlaced\n"]];
								else
									[self addToAVCLog:[NSString stringWithFormat:@"      Display as progressive\n"]];
								[self addToAVCLog:[NSString stringWithFormat:@"      Video scan-lines: %d\n",(((UInt16)pInfoBlock[25+(i*6)] & 0x0F) << 8) | pInfoBlock[26+(i*6)]]];
								[self addToAVCLog:[NSString stringWithFormat:@"      OSD scan-lines: %d\n",(((UInt16)pInfoBlock[27+(i*6)] & 0x0F) << 8) | pInfoBlock[28+(i*6)]]];
								[self addToAVCLog:[NSString stringWithFormat:@"      Pixel aspect-ratio: %f\n\n",pInfoBlock[30+(i*6)] / 128.0]];
							}
						}
					}
				}
			}
			remainingInfoBlockBytes -= (thisInfoBlockLen+2);
			pInfoBlock = &pInfoBlock[thisInfoBlockLen+2];
		}
		
		[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
		
	}while(0);
}

//////////////////////////////////////////////////////
// getDTCPInfo
//////////////////////////////////////////////////////
- (IBAction)getDTCPInfo:(id)sender
{
    UInt32 size;
    UInt8 cmd[12],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0xFF;
	cmd[2] = 0x0F;
	cmd[3] = 0x00;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	cmd[8] = 0xFF;
	cmd[9] = 0xFF;
	cmd[10] = 0xFF;
	cmd[11] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 12, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
	
	// If successful (and rCode is IMPLEMENTED/STABLE), parse response!
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		[self addToAVCLog:[NSString stringWithFormat:@"DTCP Info:\n\n"]];

		[self addToAVCLog:[NSString stringWithFormat:@"Authentication modes supported:\n"]];
		if (response[5] & 0x01)
			[self addToAVCLog:[NSString stringWithFormat:@"    Restricted\n"]];
		if (response[5] & 0x02)
			[self addToAVCLog:[NSString stringWithFormat:@"    Enhanced restricted\n"]];
		if (response[5] & 0x04)
			[self addToAVCLog:[NSString stringWithFormat:@"    Full\n"]];
		if (response[5] & 0x08)
			[self addToAVCLog:[NSString stringWithFormat:@"    Enhanced full\n"]];
		[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
		
		[self addToAVCLog:[NSString stringWithFormat:@"Exchange keys supported:\n"]];
		if (response[6] & 0x01)
			[self addToAVCLog:[NSString stringWithFormat:@"    Copy never\n"]];
		if (response[6] & 0x02)
			[self addToAVCLog:[NSString stringWithFormat:@"    Copy one-generation\n"]];
		if (response[6] & 0x04)
			[self addToAVCLog:[NSString stringWithFormat:@"    Copy no-more\n"]];
		if (response[6] & 0x08)
			[self addToAVCLog:[NSString stringWithFormat:@"    AES-128\n"]];
		[self addToAVCLog:[NSString stringWithFormat:@"\n"]];
		
		[self addToAVCLog:[NSString stringWithFormat:@"Maximum DTCP command-data length: %d\n\n",
			(((UInt32)response[10] & 0x01) << 8) + response[11]]];
	}
	else
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Could not get DTCP info for device.\n\n"]];
	}
	
}

//////////////////////////////////////////////////////
// UpButtonPushed
//////////////////////////////////////////////////////
- (IBAction) UpButtonPushed:(id)sender
{
	UInt32 chan = [CEA931DeterministicChannelNumber intValue];
	
	chan += 1;
	
	if (chan > 1023)
		chan = 1023;
	
	[CEA931DeterministicChannelNumber setIntValue:chan];
	[self SendChannelChangeCommand:chan];	
}

//////////////////////////////////////////////////////
// DownButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DownButtonPushed:(id)sender
{
	UInt32 chan = [CEA931DeterministicChannelNumber intValue];
	
	if (chan > 1)
		chan -= 1;
	
	if (chan > 1023)
		chan = 1023;
	
	[CEA931DeterministicChannelNumber setIntValue:chan];
	[self SendChannelChangeCommand:chan];	
}

//////////////////////////////////////////////////////
// SetChannelButtonPushed
//////////////////////////////////////////////////////
- (IBAction) SetChannelButtonPushed:(id)sender
{
	UInt32 chan = [CEA931DeterministicChannelNumber intValue];
	if (chan < 1)
		chan = 1;
	
	if (chan > 1023)
		chan = 1023;
	
	[CEA931DeterministicChannelNumber setIntValue:chan];
	[self SendChannelChangeCommand:chan];	
}


//////////////////////////////////////////////////////
// Num0ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num0ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit0];
}

//////////////////////////////////////////////////////
// Num1ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num1ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit1];
}

//////////////////////////////////////////////////////
// Num2ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num2ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit2];
}

//////////////////////////////////////////////////////
// Num3ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num3ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit3];
}

//////////////////////////////////////////////////////
// Num4ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num4ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit4];
}

//////////////////////////////////////////////////////
// Num5ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num5ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit5];
}

//////////////////////////////////////////////////////
// Num6ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num6ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit6];
}

//////////////////////////////////////////////////////
// Num7ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num7ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit7];
}

//////////////////////////////////////////////////////
// Num8ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num8ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit8];
}

//////////////////////////////////////////////////////
// Num9ButtonPushed
//////////////////////////////////////////////////////
- (IBAction) Num9ButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDigit9];
}

//////////////////////////////////////////////////////
// DotButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DotButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDot];
}

//////////////////////////////////////////////////////
// EnterButtonPushed
//////////////////////////////////////////////////////
- (IBAction) EnterButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyEnter];
}

//////////////////////////////////////////////////////
// ChanUpButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ChanUpButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyChUp];
}

//////////////////////////////////////////////////////
// ChanDownButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ChanDownButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyChDown];
}

//////////////////////////////////////////////////////
// PrevChanButtonPushed
//////////////////////////////////////////////////////
- (IBAction) PrevChanButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyPrevious];
}

//////////////////////////////////////////////////////
// VolUpButtonPushed
//////////////////////////////////////////////////////
- (IBAction) VolUpButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyVolUp];
}

//////////////////////////////////////////////////////
// VolDownButtonPushed
//////////////////////////////////////////////////////
- (IBAction) VolDownButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyVolDown];
}

//////////////////////////////////////////////////////
// MuteButtonPushed
//////////////////////////////////////////////////////
- (IBAction) MuteButtonPushed:(id)sender;
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyMute];
}

//////////////////////////////////////////////////////
// ArrowUpButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ArrowUpButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyUp];
}

//////////////////////////////////////////////////////
// ArrowDownButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ArrowDownButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyDown];
}

//////////////////////////////////////////////////////
// ArrowLeftButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ArrowLeftButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyLeft];
}

//////////////////////////////////////////////////////
// ArrowRightButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ArrowRightButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeyRight];
}

//////////////////////////////////////////////////////
// SelectButtonPushed
//////////////////////////////////////////////////////
- (IBAction) SelectButtonPushed:(id)sender
{
	[self SendCEA931PassThroughCommand:kAVCPanelKeySelect];
}

//////////////////////////////////////////////////////////////////////
// SendCEA931PassThroughCommand
//////////////////////////////////////////////////////////////////////
- (void) SendCEA931PassThroughCommand:(int)operationID
{
    UInt8 cmd[5],response[512];
	UInt32 size;
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x48;
	cmd[2] = 0x7C;	// PASS_THROUGH opcode
	cmd[3] = operationID + 0x00;	// operation_id + state_pressed
	cmd[4] = 0;	// Lenght of operation data
	size = 512;

	// Don't do if we're only supposed to do "release"
	if ([CEA931PassThroughCommandType selectedRow] != 1)
	{
		res = DoAVCTransaction(cmd, 5, response, &size,self,true,true);
		if (res != kIOReturnSuccess)
			[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
	}

	size = 512;
	cmd[3] = operationID + 0x80;	// operation_id + state_released
	
	// Don't do if we're only supposed to do "press"
	if ([CEA931PassThroughCommandType selectedRow] != 0)
	{
		res = DoAVCTransaction(cmd, 5, response, &size,self,true,true);
		if (res != kIOReturnSuccess)
			[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
	}
}

//////////////////////////////////////////////////////
// SendChannelChangeCommand
//////////////////////////////////////////////////////
- (void) SendChannelChangeCommand:(int)channel
{
	UInt8 cmd[9],response[512];
	UInt32 size = 512;
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x48;
	cmd[2] = 0x7C;	// PASS_THROUGH opcode
	cmd[3] = kAVCPanelKeyTuneFunction;
	cmd[4] = 4;	// Lenght of operation data
	cmd[5] = ((channel & 0x0F00) >> 8);
	cmd[6] = (channel & 0x00FF);
	cmd[7] = 0x00;
	cmd[8] = 0x00;
	
	res = DoAVCTransaction(cmd, 9, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
}

//////////////////////////////////////////////////////
// ViewerButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ViewerButtonPushed:(id)sender
{
	IOReturn res;
	NSMutableArray *viewerTaskArgs;
	int pid;
	ProcessSerialNumber psn;

	if (!pAVCDevice->isOpened())
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Cannot use viewer since device is not opened!\n\n"]];	
		return;
	}
	
	if ([[ViewerButton title] isEqualTo:kViewerButtonStartText] == YES)
	{
		// Start viewer and MPEG receiver

		// Setup the arguments for VLC
		viewerTaskArgs = [NSMutableArray arrayWithCapacity:0];
		
		[viewerTaskArgs addObject:@"--no-fullscreen"];
		
		// These optional arguments enable the deinterlacer by default,
		// and cause VLC to start without the VLC controller window.
		//[viewerTaskArgs addObject:@"--deinterlace-mode"];
		//[viewerTaskArgs addObject:@"bob"];
		//[viewerTaskArgs addObject:@"--intf"];
		//[viewerTaskArgs addObject:@"rc"];
		//[viewerTaskArgs addObject:@"--rc-fake-tty"];
		
		[viewerTaskArgs addObject:[NSString stringWithString:@"udp://@:41394"]];
		
		// Create a new viewerTask
		viewerTask = [[NSTask alloc] init];
		[viewerTask setStandardInput: [NSPipe pipe]];
		[viewerTask setStandardOutput: [NSPipe pipe]];
		[viewerTask setLaunchPath:@"/Applications/VLC.app/Contents/MacOS/VLC"];
		[viewerTask setArguments:viewerTaskArgs];
		[viewerTask launch];
		usleep(600000);
		pid = [viewerTask processIdentifier];
		GetProcessForPID(pid, &psn);
		SetFrontProcess(&psn);
		
		/* open UDP socket */
		viewerSocket = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
		if (viewerSocket == -1)
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Could not create socket for UDP streaming to viewer\n\n"]];	
			return;
		}
		
		// Set address to "local node"
		inet_aton("127.0.0.1", &socketAddr.sin_addr);
		
		/* target port 41394 */
		socketAddr.sin_family = AF_INET;
		socketAddr.sin_port = htons(41394);
		
		if (connect(viewerSocket, (struct sockaddr *) &socketAddr, sizeof socketAddr) == -1)
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Could not connect to viewer socket\n\n"]];	
			return;
		}

		pAVCDeviceStream = pAVCDevice->CreateMPEGReceiverForDevicePlug(0,
																	   nil, // We'll install the structured callback later (MyStructuredDataPushProc),
																	   self,
																	   MPEGReceiverMessageReceivedProc,
																	   self,
																	   nil,
																	   kNumCyclesInMPEGReceiverSegment,
																	   kNumSegmentsInMPEGReceiverProgram);
		if (pAVCDeviceStream == nil)
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Could not create MPEGReceiver\n\n"]];	
			return;
		}

		pAVCDeviceStream->pMPEGReceiver->registerStructuredDataPushCallback(MyStructuredDataPushProc, kNumCyclesInMPEGReceiverSegment, (void*) viewerSocket);
		
		res = pAVCDevice->StartAVCDeviceStream(pAVCDeviceStream);
		if (res != kIOReturnSuccess)
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Could not start MPEGReceiver\n\n"]];	
			pAVCDevice->DestroyAVCDeviceStream(pAVCDeviceStream);
			return;
		}
		
		[ViewerButton setTitle:kViewerButtonStopText];
	}
	else
	{
		// Stop viewer and MPEG receiver
		
		res = pAVCDevice->StopAVCDeviceStream(pAVCDeviceStream);
		pAVCDevice->DestroyAVCDeviceStream(pAVCDeviceStream);
		pAVCDeviceStream = nil;
		
		[viewerTask terminate];
		[viewerTask release];
		viewerTask = nil;

		close(viewerSocket);

		[ViewerButton setTitle:kViewerButtonStartText];
	}
}

#pragma mark -----------------------------------
#pragma mark Buttons on Tape Tab
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// TapePlugInfoButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapePlugInfoButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0x02;
	cmd[3] = 0x00;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeInputSignalModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction)TapeInputSignalModeButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0x79;
	cmd[3] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeOutputSignalModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction)TapeOutputSignalModeButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0x78;
	cmd[3] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeMediumInfoButtonPushed
//////////////////////////////////////////////////////
- (IBAction)TapeMediumInfoButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[5],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xDA;
	cmd[3] = 0x7F;
	cmd[4] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 5, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeTransportStateButtonPushed
//////////////////////////////////////////////////////
- (IBAction)TapeTransportStateButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapePlayButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapePlayButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC3;
	cmd[3] = 0x75;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeStopButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeStopButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC4;
	cmd[3] = 0x60;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapePauseButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapePauseButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	// First, determine which transport state we're in;
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
	
	// Setup common command parameters
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[3] = 0x7D;
	size = 512;
	
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus) && (response[2] == 0xC2))
	{
		// Do record-pause command
		cmd[2] = 0xC2;
	}
	else
	{
		// Do play-pause command
		cmd[2] = 0xC3;
	}
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeFFwdButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeFFwdButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	// First, determine which transport state we're in;
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
		
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		if (response[2] == 0xC3)
		{
			// If play-pause mode, then do next-frame, otherwise Play Fastest Fwd
			if ((response[3] == 0x7D) || (response[3] == 0x6D))
				cmd[3] = 0x30;
			else
				cmd[3] = 0x3F;
			
			cmd[0] = kAVCControlCommand;
			cmd[1] = 0x20;
			cmd[2] = 0xC3;
			size = 512;
			res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
			if (res != kIOReturnSuccess)
				[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
		}
		else if (response[2] == 0xC4)
		{
			// Wind Fast Forward
			cmd[0] = kAVCControlCommand;
			cmd[1] = 0x20;
			cmd[2] = 0xC4;
			cmd[3] = 0x75;
			size = 512;
			res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
			if (res != kIOReturnSuccess)
				[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
		}
	}
}

//////////////////////////////////////////////////////
// TapeFRevButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeFRevButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	// First, determine which transport state we're in;
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
	
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		if (response[2] == 0xC3)
		{
			// If play-pause mode, then do prev-frame, otherwise Play Fastest Reverse
			if ((response[3] == 0x7D) || (response[3] == 0x6D))
				cmd[3] = 0x40;
			else
				cmd[3] = 0x4F;
			
			cmd[0] = kAVCControlCommand;
			cmd[1] = 0x20;
			cmd[2] = 0xC3;
			size = 512;
			res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
			if (res != kIOReturnSuccess)
				[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
		}
		else if (response[2] == 0xC4)
		{
			// Wind Rewind
			cmd[0] = kAVCControlCommand;
			cmd[1] = 0x20;
			cmd[2] = 0xC4;
			cmd[3] = 0x65;
			size = 512;
			res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
			if (res != kIOReturnSuccess)
				[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
		}
	}
}

//////////////////////////////////////////////////////
// TapeRecButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeRecButtonPushed:(id)sender;
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC2;
	cmd[3] = 0x75;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeATNButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeATNButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0x52;
	cmd[3] = 0x71;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeEjectButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeEjectButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC1;
	cmd[3] = 0x60;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapePlaySpecificModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapePlaySpecificModeButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	UInt8 playModes[] = 
	{
		0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x3e,0x3f,
		0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e,0x4f,
		0x65,0x6d,0x75,0x7d
	};
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC3;
	cmd[3] = playModes[[tapePlayMode indexOfSelectedItem]];
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeRecSpecificModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeRecSpecificModeButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	UInt8 recModes[] = {0x75,0x7D};
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC2;
	cmd[3] = recModes[[tapeRecMode indexOfSelectedItem]];
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeWindSpecificModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeWindSpecificModeButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[512];
    IOReturn res;
	UInt8 windModes[] = {0x45,0x60,0x65,0x75};
	
	cmd[0] = kAVCControlCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xC4;
	cmd[3] = windModes[[tapeWindMode indexOfSelectedItem]];
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// TapeStatusOneShotButtonPushed
//////////////////////////////////////////////////////
- (IBAction) TapeStatusOneShotButtonPushed:(id)sender
{
	[self PollTapeStatus];
}

//////////////////////////////////////////////////////
// PollTapeStatus
//////////////////////////////////////////////////////
-(void) PollTapeStatus
{
    UInt32 size;
    UInt8 cmd[12],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 4, response, &size,self,[LogTapeSubunitPollingButton state],false);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
	
	// If successful (and rCode is IMPLEMENTED/STABLE), parse response!
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		switch(response[2])
		{
			case 0xC1:
				[TapeTransportState setStringValue:@"No Tape"];
				break;
				
			case 0xC2:
				switch(response[3])
				{
					case 0x75:
						[TapeTransportState setStringValue:@"Record"];
						break;

					case 0x7D:
						[TapeTransportState setStringValue:@"Record Pause"];
						break;

					default:
						[TapeTransportState setStringValue:[NSString stringWithFormat:@"Record (0x%02X)",response[3]]];
						break;
				};
				break;
				
			case 0xC3:
				switch(response[3])
				{
					case 0x30:
						[TapeTransportState setStringValue:@"Play Next Frame"];
						break;
						
					case 0x31:
						[TapeTransportState setStringValue:@"Play Slowest Fwd"];
						break;
						
					case 0x32:
						[TapeTransportState setStringValue:@"Play Slow Fwd 6"];
						break;
						
					case 0x33:
						[TapeTransportState setStringValue:@"Play Slow Fwd 5"];
						break;
						
					case 0x34:
						[TapeTransportState setStringValue:@"Play Slow Fwd 4"];
						break;
						
					case 0x35:
						[TapeTransportState setStringValue:@"Play Slow Fwd 3"];
						break;

					case 0x36:
						[TapeTransportState setStringValue:@"Play Slow Fwd 2"];
						break;
					
					case 0x37:
						[TapeTransportState setStringValue:@"Play Slow Fwd 1"];
						break;
					
					case 0x38:
						[TapeTransportState setStringValue:@"Play X1"];
						break;
					
					case 0x39:
						[TapeTransportState setStringValue:@"Play Fast Fwd 1"];
						break;
					
					case 0x3A:
						[TapeTransportState setStringValue:@"Play Fast Fwd 2"];
						break;
					
					case 0x3B:
						[TapeTransportState setStringValue:@"Play Fast Fwd 3"];
						break;
					
					case 0x3C:
						[TapeTransportState setStringValue:@"Play Fast Fwd 4"];
						break;
					
					case 0x3D:
						[TapeTransportState setStringValue:@"Play Fast Fwd 5"];
						break;
					
					case 0x3E:
						[TapeTransportState setStringValue:@"Play Fast Fwd 6"];
						break;
					
					case 0x3F:
						[TapeTransportState setStringValue:@"Play Fastest Fwd"];
						break;
					
					case 0x40:
						[TapeTransportState setStringValue:@"Play Prev Frame"];
						break;
					
					case 0x41:
						[TapeTransportState setStringValue:@"Play Slowest Rev"];
						break;
					
					case 0x42:
						[TapeTransportState setStringValue:@"Play Slow Rev 6"];
						break;
					
					case 0x43:
						[TapeTransportState setStringValue:@"Play Slow Rev 5"];
						break;
					
					case 0x44:
						[TapeTransportState setStringValue:@"Play Slow Rev 4"];
						break;
					
					case 0x45:
						[TapeTransportState setStringValue:@"Play Slow Rev 3"];
						break;
					
					case 0x46:
						[TapeTransportState setStringValue:@"Play Slow Rev 2"];
						break;
					
					case 0x47:
						[TapeTransportState setStringValue:@"Play Slow Rev 1"];
						break;
					
					case 0x48:
						[TapeTransportState setStringValue:@"Play X1 Rev"];
						break;
					
					case 0x49:
						[TapeTransportState setStringValue:@"Play Fast Rev 1"];
						break;
					
					case 0x4A:
						[TapeTransportState setStringValue:@"Play Fast Rev 2"];
						break;
					
					case 0x4B:
						[TapeTransportState setStringValue:@"Play Fast Rev 3"];
						break;
					
					case 0x4C:
						[TapeTransportState setStringValue:@"Play Fast Rev 4"];
						break;
					
					case 0x4D:
						[TapeTransportState setStringValue:@"Play Fast Rev 5"];
						break;
					
					case 0x4E:
						[TapeTransportState setStringValue:@"Play Fast Rev 6"];
						break;
					
					case 0x4F:
						[TapeTransportState setStringValue:@"Play Fastest Rev"];
						break;
					
					case 0x65:
						[TapeTransportState setStringValue:@"Play Reverse"];
						break;
					
					case 0x6D:
						[TapeTransportState setStringValue:@"Play Rev Pause"];
						break;

					case 0x75:
						[TapeTransportState setStringValue:@"Play"];
						break;
						
					case 0x7D:
						[TapeTransportState setStringValue:@"Play Pause"];
						break;
						
					default:
						[TapeTransportState setStringValue:[NSString stringWithFormat:@"Play (0x%02X)",response[3]]];
						break;
				};
				break;
				
			case 0xC4:
				switch(response[3])
				{
					case 0x30:
						[TapeTransportState setStringValue:@"Stop Emergency"];
						break;
						
					case 0x31:
						[TapeTransportState setStringValue:@"Stop (Condensation)"];
						break;

					case 0x45:
						[TapeTransportState setStringValue:@"High Speed Rew"];
						break;
						
					case 0x60:
						[TapeTransportState setStringValue:@"Stop"];
						break;
					
					case 0x65:
						[TapeTransportState setStringValue:@"Rewind"];
						break;

					case 0x75:
						[TapeTransportState setStringValue:@"Fast-Fwd"];
						break;

					default:
						[TapeTransportState setStringValue:[NSString stringWithFormat:@"Wind (0x%02X)",response[3]]];
						break;
				};
				break;
				
			default:
				[TapeTransportState setStringValue:@"Unknown"];
				break;
		};
	}
	else
	{
		if ((res == kIOReturnSuccess) && (response[0] == kAVCNotImplementedStatus))
			[TapeTransportState setStringValue:@"Not Implemented"];
		else if ((res == kIOReturnSuccess) && (response[0] == kAVCInTransitionStatus))
			[TapeTransportState setStringValue:@"In Transition"];
		else 
			[TapeTransportState setStringValue:@"Error"];
	}
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x20;
	cmd[2] = 0xDA;
	cmd[3] = 0x7F;
	cmd[4] = 0x7F;
	size = 512;
	
	res = DoAVCTransaction(cmd, 5, response, &size,self,[LogTapeSubunitPollingButton state],false);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
	
	// If successful (and rCode is IMPLEMENTED/STABLE), parse response!
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		switch(response[3])
		{
			case 0x31:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"Standard-DV (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"Standard-DV (write-protect)"];
						break;
						
					case 0x40:
						[TapeMediumInfoState setStringValue:@"Standard-DV MP (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"Standard-DV MP (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"Standard-DV (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x32:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"Mini-DV (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"Mini-DV (write-protect)"];
						break;
						
					case 0x40:
						[TapeMediumInfoState setStringValue:@"Mini-DV MP (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"Mini-DV MP (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"Mini-DV (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x33:
				switch(response[4])
				{
					case 0x40:
						[TapeMediumInfoState setStringValue:@"Medium-DV MP (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"Medium-DV MP (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"Medium-DV (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x22:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"VHS (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"VHS (write-protect)"];
						break;
						
					case 0x40:
						[TapeMediumInfoState setStringValue:@"S-VHS (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"S-VHS (write-protect)"];
						break;
						
					case 0x50:
						[TapeMediumInfoState setStringValue:@"D-VHS (write-ok)"];
						break;
						
					case 0x51:
						[TapeMediumInfoState setStringValue:@"D-VHS (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"VHS (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x23:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"VHS-C (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"VHS-C (write-protect)"];
						break;
						
					case 0x40:
						[TapeMediumInfoState setStringValue:@"S-VHS-C (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"S-VHS-C (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"VHS-C (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x60:
				[TapeMediumInfoState setStringValue:@"No Tape"];
				break;

			case 0x7E:
				[TapeMediumInfoState setStringValue:@"Unknown Cassette"];
				break;
			
			case 0x12:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"8mm MP (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"8mm MP (write-protect)"];
						break;
						
					case 0x40:
						[TapeMediumInfoState setStringValue:@"8mm ME (write-ok)"];
						break;
						
					case 0x41:
						[TapeMediumInfoState setStringValue:@"8mm ME (write-protect)"];
						break;
						
					case 0x50:
						[TapeMediumInfoState setStringValue:@"Hi-8 MP (write-ok)"];
						break;
						
					case 0x51:
						[TapeMediumInfoState setStringValue:@"Hi-8 MP (write-protect)"];
						break;
						
					case 0x60:
						[TapeMediumInfoState setStringValue:@"Hi-8 ME (write-ok)"];
						break;
						
					case 0x61:
						[TapeMediumInfoState setStringValue:@"Hi-8 Me (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"8mm (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x41:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"Micro-MV (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"Micro-MV (write-protect)"];
						break;

					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"Micro-MV (0x%02X)",response[4]]];
						break;
				}
				break;
				
			case 0x01:
				switch(response[4])
				{
					case 0x30:
						[TapeMediumInfoState setStringValue:@"Analog-audio (write-ok)"];
						break;
						
					case 0x31:
						[TapeMediumInfoState setStringValue:@"Analog-audio (write-protect)"];
						break;
						
					default:
						[TapeMediumInfoState setStringValue:[NSString stringWithFormat:@"Analog-audio (0x%02X)",response[4]]];
						break;
				}
				break;
				
			default:
				[TapeMediumInfoState setStringValue:@"Unknown"];
				break;
		};
	}
	else
	{
		if ((res == kIOReturnSuccess) && (response[0] == kAVCNotImplementedStatus))
			[TapeMediumInfoState setStringValue:@"Not Implemented"];
		else
			[TapeMediumInfoState setStringValue:@"Error"];
	}
	
	if ([TapeTimeCodeType selectedRow] == 0)
	{
		// Absolute Time Code
		
		cmd[0] = kAVCStatusInquiryCommand;
		cmd[1] = 0x20;
		cmd[2] = 0x51;
		cmd[3] = 0x71;
		cmd[4] = 0xFF;
		cmd[5] = 0xFF;
		cmd[6] = 0xFF;
		cmd[7] = 0xFF;
		size = 512;
		
		res = DoAVCTransaction(cmd, 8, response, &size,self,[LogTapeSubunitPollingButton state],false);
		if (res != kIOReturnSuccess)
			[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
		
		// If successful (and rCode is IMPLEMENTED/STABLE), parse response!
		if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
		{
			if ( (response[4] == 0xFF) && (response[5] == 0xFF) && (response[6] == 0xFF) && (response[7] == 0xFF))
				[TapeTimeCodeState setStringValue:@"Unknown"];
			else
				[TapeTimeCodeState setStringValue:[NSString stringWithFormat:@"%02d:%02d:%02d.%02d",
					bcd2bin(response[7]),
					bcd2bin(response[6]),
					bcd2bin(response[5]),
					bcd2bin(response[4])]];
		}
		else
		{
			if ((res == kIOReturnSuccess) && (response[0] == kAVCNotImplementedStatus))
				[TapeTimeCodeState setStringValue:@"Not Implemented"];
			else
				[TapeTimeCodeState setStringValue:@"Error"];
		}
	}
	else
	{
		// Relative Time Counter

		cmd[0] = kAVCStatusInquiryCommand;
		cmd[1] = 0x20;
		cmd[2] = 0x57;
		cmd[3] = 0x71;
		cmd[4] = 0xFF;
		cmd[5] = 0xFF;
		cmd[6] = 0xFF;
		cmd[7] = 0xFF;
		size = 512;
		
		res = DoAVCTransaction(cmd, 8, response, &size,self,[LogTapeSubunitPollingButton state],false);
		if (res != kIOReturnSuccess)
			[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];	
		
		// If successful (and rCode is IMPLEMENTED/STABLE), parse response!
		if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
		{
			[TapeTimeCodeState setStringValue:[NSString stringWithFormat:@"%c%02d:%02d:%02d",
									 ((response[4] & 0x80) == 0x80) ? '-':'+',
					bcd2bin(response[7]),
					bcd2bin(response[6]),
					bcd2bin(response[5])]];
		}
		else
		{
			if ((res == kIOReturnSuccess) && (response[0] == kAVCNotImplementedStatus))
				[TapeTimeCodeState setStringValue:@"Not Implemented"];
			else
				[TapeTimeCodeState setStringValue:@"Error"];
		}
	}
	
}

#pragma mark -----------------------------------
#pragma mark Buttons on Music Tab
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// MusicPlugInfoButtonPushed
//////////////////////////////////////////////////////
- (IBAction) MusicPlugInfoButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[8],response[512];
    IOReturn res;
	
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = 0x60;
	cmd[2] = 0x02;
	cmd[3] = 0x00;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;
	size = 512;
	
	res = DoAVCTransaction(cmd, 8, response, &size,self,true,true);
	if (res != kIOReturnSuccess)
		[self addToAVCLog:[NSString stringWithFormat:@"AVCCommand returned error: 0x%08X\n\n",res]];
}

//////////////////////////////////////////////////////
// FullDeviceAnalysisButtonPushed
//////////////////////////////////////////////////////
- (IBAction) FullDeviceAnalysisButtonPushed:(id)sender
{
	NSMutableString *logString = [NSMutableString stringWithCapacity:0];
	StringLogger logger(StringLoggerPrintFunction,logString);
	MusicSubunitController *pMusicSubunitController = nil;
	
	if (1) // TODO: ((pAVCDevice->hasMusicSubunit == true) || (pAVCDevice->hasAudioSubunit == true))
	{
		if (pAVCDevice->isOpened())
			pMusicSubunitController = new MusicSubunitController(pAVCDevice,0,&logger);
		else
		{
			[self GetAVCDeviceCommandInterface];
			if (pAVCDeviceCommandInterface)
				pMusicSubunitController = new MusicSubunitController(pAVCDeviceCommandInterface,0, &logger);
		}
		
		if (pMusicSubunitController)
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Music/Audio subunit device analysis:\n\n"]];

			// Discover the configuration of this device
			pMusicSubunitController->DiscoverConfiguration();
			
			// Add the discovery info to the log
			[self addToAVCLog:logString];

			// We're done
			delete pMusicSubunitController;
		}
		else
		{
			[self addToAVCLog:[NSString stringWithFormat:@"Could not do analysis on Music/Audio subunit based device\n"]];
		}
	}
	else
	{
		[self addToAVCLog:[NSString stringWithFormat:@"Device is not a Music or Audio subunit based device\n"]];
	}
}


#pragma mark -----------------------------------
#pragma mark TableView Delagate Functios
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// TableView methods
//////////////////////////////////////////////////////
- (int) numberOfRowsInTableView: (NSTableView*) aTableView
{
	if (aTableView == InputPlugsTable)
		return numInputPCRs;
	else if (aTableView == OutputPlugsTable)
		return numOutputPCRs;
	else
		return 0; 
}

- (id) tableView: (NSTableView*) aTableView
objectValueForTableColumn: (NSTableColumn*) aTableColumn
			 row: (int) rowIndex
{
	NSString *identifier = [aTableColumn identifier];
	NSString *indexString = NULL;

	
	if (aTableView == InputPlugsTable)
	{
		if ([identifier isEqualToString:@"index"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",rowIndex];
		}
		if ([identifier isEqualToString:@"online"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",iPCRValues[rowIndex].online];
		}
		if ([identifier isEqualToString:@"broadcast"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",iPCRValues[rowIndex].broadcast];
		}
		if ([identifier isEqualToString:@"point"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",iPCRValues[rowIndex].p2pCount];
		}
		if ([identifier isEqualToString:@"channel"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",iPCRValues[rowIndex].channel];
		}
	}
	else if (aTableView == OutputPlugsTable)
	{
		if ([identifier isEqualToString:@"index"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",rowIndex];
		}
		if ([identifier isEqualToString:@"online"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].online];
		}
		if ([identifier isEqualToString:@"broadcast"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].broadcast];
		}
		if ([identifier isEqualToString:@"point"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].p2pCount];
		}
		if ([identifier isEqualToString:@"channel"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].channel];
		}
		if ([identifier isEqualToString:@"rate"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].rate];
		}
		if ([identifier isEqualToString:@"overhead"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].overhead];
		}
		if ([identifier isEqualToString:@"payload"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%d",oPCRValues[rowIndex].payloadInQuads];
		}
	}
	
	return indexString;
}

- (void) tableView: (NSTableView*) aTableView
	setObjectValue: (id) anObject
	forTableColumn: (NSTableColumn*) aTableColumn
			   row: (int) rowIndex
{

}

@end

#pragma mark -----------------------------------
#pragma mark Misc Non-class functions
#pragma mark -----------------------------------

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

ValueStrings panelOpCodeStrings[] =
{
	// Unit/Subunit Commands
	{ 0x00,"Vendor Unique"},
	{ 0x02,"Plug-Info"},
	
	// Disc Subunit Commands
	{ 0x7C,"Pass-Through"},
	
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

//////////////////////////////////////////////////////////////////////
//
// valToString
//
//////////////////////////////////////////////////////////////////////
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

//////////////////////////////////////////////////////////////////////
//
// avcCommandVerboseLog
//
//////////////////////////////////////////////////////////////////////
void avcCommandVerboseLog(UInt8 *command, UInt32 cmdLen, AVCDeviceControlPanelController *userIntf)
{
	UInt8 cType = command[0] & 0x0F;
    UInt8 subUnit = command[1];
    UInt8 opCode = command[2];
	//    UInt8 *pOperands = (UInt8*) &command[3];
	unsigned int i;
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"=============== AVC Command ===============\n"]];
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"cType:   %s\n",valToString(cTypeStrings,cType)]];
	[userIntf addToAVCLog:[NSString stringWithFormat:@"subUnit: 0x%02X\n",subUnit]];
	
	if (subUnit == 0x20)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(tapeOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x18)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(discOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x48)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(panelOpCodeStrings,opCode),opCode]];
	else
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(unitOpCodeStrings,opCode),opCode]];
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"FCP command frame:"]];
	for (i=0;i<cmdLen;i++)
	{
		if ((i % 16) == 0)
			[userIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];
		
		[userIntf addToAVCLog:[NSString stringWithFormat:@"%02X ",command[i]]];
	}
	[userIntf addToAVCLog:[NSString stringWithFormat:@"\n\n"]];
	
	return;
}

//////////////////////////////////////////////////////////////////////
//
// avcResponseVerboseLog
//
//////////////////////////////////////////////////////////////////////
void avcResponseVerboseLog(	UInt8 *response, UInt32 responseLen, AVCDeviceControlPanelController *userIntf)
{
    UInt8 subUnit = response[1];
    UInt8 opCode = response[2];
	//    UInt8 *pResponseOperands = (UInt8*) &response[3];
    UInt8 *pResponseType = (UInt8*) &response[0];
	unsigned int i;
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"=============== AVC Response ===============\n"]];
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"response: %s\n",valToString(responseStrings,*pResponseType)]];
	[userIntf addToAVCLog:[NSString stringWithFormat:@"subUnit: 0x%02X\n",subUnit]];
	
	if (subUnit == 0x20)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(tapeOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x18)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(discOpCodeStrings,opCode),opCode]];
	else if (subUnit == 0x48)
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(panelOpCodeStrings,opCode),opCode]];
	else
		[userIntf addToAVCLog:[NSString stringWithFormat:@"opCode:  %s (0x%02X)\n",valToString(unitOpCodeStrings,opCode),opCode]];
	
	[userIntf addToAVCLog:[NSString stringWithFormat:@"FCP response frame:"]];
	
	for (i=0;i<responseLen;i++)
	{
		if ((i % 16) == 0)
			[userIntf addToAVCLog:[NSString stringWithFormat:@"\n"]];
		
		[userIntf addToAVCLog:[NSString stringWithFormat:@"%02X ",response[i]]];
	}
	[userIntf addToAVCLog:[NSString stringWithFormat:@"\n\n"]];
	
	return;
}

//////////////////////////////////////////////////////////////////////
//
// DoAVCTransaction
//
//////////////////////////////////////////////////////////////////////
IOReturn DoAVCTransaction(const UInt8 *command, 
						  UInt32 cmdLen, 
						  UInt8 *response, 
						  UInt32 *responseLen, 
						  AVCDeviceControlPanelController *userIntf,
						  bool doVerboseLogging,
						  bool doUpdateAVCCommandString)
{
	IOReturn result = kIOReturnError;
	AVCDeviceCommandInterface *pAVCDeviceCommandInterface;
	AVCDevice *pAVCDevice = [userIntf GetAVCDevice];
	
	if (doVerboseLogging)
		avcCommandVerboseLog((UInt8*)command,cmdLen,userIntf);
	
	if (doUpdateAVCCommandString)
	{
		NSMutableString *commandByteString = [NSMutableString stringWithCapacity:((cmdLen*2)+1)];
		for (int i=0;i<cmdLen;i++)
			[commandByteString appendFormat:@"%02X", command[i]];
		[userIntf updateAVCCommandBytesView:commandByteString];
	}
	
	if (pAVCDevice->isOpened())
	{
		result = pAVCDevice->AVCCommand(command, cmdLen, response, responseLen);
	}
	else
	{
		pAVCDeviceCommandInterface = [userIntf GetAVCDeviceCommandInterface];
		if (pAVCDeviceCommandInterface)
			result = pAVCDeviceCommandInterface->AVCCommand(command, cmdLen, response, responseLen);
	}

	if ((doVerboseLogging) && (result == kIOReturnSuccess))
		avcResponseVerboseLog(response,*responseLen,userIntf);
	
	return result;
}

//////////////////////////////////////////////////////////////////////
//
// MyAVCDeviceMessageNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyAVCDeviceMessageNotification (AVCDevice *pAVCDevice,
										 natural_t messageType,
										 void * messageArgument,
										 void *pRefCon)
{
	AVCDeviceControlPanelController *userIntf = (AVCDeviceControlPanelController *) pRefCon; 
	
	// Handle device going away while opened!
	if (messageType == kIOMessageServiceIsRequestingClose)
		[userIntf performSelectorOnMainThread:@selector(DeviceHasGoneAway) withObject:userIntf waitUntilDone:YES];
	else if (messageType == kIOMessageServiceIsSuspended)
		[userIntf performSelectorOnMainThread:@selector(LogBusResetMessage) withObject:userIntf waitUntilDone:YES];
	
	return kIOReturnSuccess;
}

//////////////////////////////////////////////////////////////////////
//
// MyAVCDeviceCommandInterfaceMessageNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyAVCDeviceCommandInterfaceMessageNotification(AVCDeviceCommandInterface *pAVCDeviceCommandInterface,
														natural_t messageType,
														void * messageArgument,
														void *pRefCon)
{
	AVCDeviceControlPanelController *userIntf = (AVCDeviceControlPanelController *) pRefCon; 

	// Only handle messages here if we've not got the device opened.
	if (![userIntf isAVCDeviceOpenedByThisApp])
	{
		if (messageType == kIOMessageServiceIsTerminated)
			[userIntf performSelectorOnMainThread:@selector(DeviceHasGoneAway) withObject:userIntf waitUntilDone:YES];
		else if (messageType == kIOMessageServiceIsSuspended)
			[userIntf performSelectorOnMainThread:@selector(LogBusResetMessage) withObject:userIntf waitUntilDone:YES];
	}
	
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

//////////////////////////////////////////////
// StringLoggerPrintFunction
//////////////////////////////////////////////
void StringLoggerPrintFunction(char *pString,void *pRefCon)
{
	NSMutableString *pLogString = (NSMutableString*) pRefCon;
	[pLogString appendString:[NSString stringWithCString:pString]];

}

//////////////////////////////////////////////////////////////////////
//
// MPEGReceiverMessageReceivedProc
//
//////////////////////////////////////////////////////////////////////
void MPEGReceiverMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon)
{

}

//////////////////////////////////////////////////////////////////////
//
// MyStructuredDataPushProc
//
//////////////////////////////////////////////////////////////////////
IOReturn MyStructuredDataPushProc(UInt32 CycleDataCount, MPEGReceiveCycleData *pCycleData, void *pRefCon)
{
	int vectIndex = 0;
	struct iovec iov[kNumCyclesInMPEGReceiverSegment*5];
	int viewerSocket = (int) pRefCon;
	
	if (viewerSocket)
	{
		for (int cycle=0;cycle<CycleDataCount;cycle++)
		{
			for (int sourcePacket=0;sourcePacket<pCycleData[cycle].tsPacketCount;sourcePacket++)
			{
				iov[vectIndex].iov_base = pCycleData[cycle].pBuf[sourcePacket];
				iov[vectIndex].iov_len = kMPEG2TSPacketSize;
				vectIndex += 1;
			}
		}
		
		writev(viewerSocket, iov, vectIndex);
	}
	
	return 0;
}


