/*
	File:		DVHSCapController.mm

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
#include <IOKit/IOMessage.h>
#include <IOKit/firewire/IOFireWireLib.h>
#include <IOKit/firewire/IOFireWireLibIsoch.h>
#include <IOKit/avc/IOFireWireAVCLib.h>
#include <IOKit/avc/IOFireWireAVCConsts.h>

#include <AVCVideoServices/AVCVideoServices.h>

using namespace AVS;

#import "DVHSCapController.h"

#define kTransmitterExtraPacketCount 1000
#define kReceiverExtraPacketCount 1000
#define kFireWireCyclesPerSecond 8000
#define kMPEGXmitterPrerollCount 4000

#define kCaptureButtonText @"Capture from D-VHS"
#define kExportButtonText @"Export to D-VHS"
#define kStopCaptureText @"Stop Capture"
#define kStopExportText @"Stop Export"

typedef enum
{
	kAppStateIdle,
	kAppStateImport,
	kAppStateExport
}AppState;

// States for our external DVHS Device
typedef enum
{
	kDVHSStateStopped,
	kDVHSStateRecPause,
	kDVHSStateRecForward,
	kDVHSStatePlayPause,
	kDVHSStatePlayForward,
	kDVHSStateFFwd,
	kDVHSStateFRew,
	kDVHSStateUnknown
}DVHSTransportState;

// Global Vars
FILE *inFile = nil;
FILE *outFile = nil;
FILE *outVideoFile = nil;
FILE *outAudioFile = nil;
DVHSCapController *gpUserIntf;
TSDemuxer *deMux;
StringLogger *stringLogger;
bool xmitterFlushMode;
unsigned int xmitterFlushCnt;
char tsPacketBuf[kMPEG2TSPacketSize];
unsigned int packetCount = 0;
bool transmitDone = false;
bool demuxDuringCapture = false;
bool foundFirstIFrame = false;
unsigned int xmitterPrerollCount;
AppState appState;
AVCDeviceController *pAVCDeviceController = nil;
AVCDevice  *pDVHSDevice = nil;
DVHSTransportState	dvhsDeviceTransportState = kDVHSStateUnknown;
AVCDeviceStream* pAVCDeviceStream = nil;

// Prototpes
void GetDVHSDeckTimeCode(AVCDevice *dvhsDevice);
void GetDVHSDeckTransportState(AVCDevice *dvhsDevice);
void GetDVHSDeckPowerState(AVCDevice *dvhsDevice);
static unsigned int bcd2bin(unsigned int input);
void DVHSStop(AVCDevice *dvhsDevice);
void DVHSPlay(AVCDevice *dvhsDevice);
void DVHSRecord(AVCDevice *dvhsDevice);
void DVHSPause(AVCDevice *dvhsDevice);
void DVHSFFwd(AVCDevice *dvhsDevice);
void DVHSFRew(AVCDevice *dvhsDevice);
void TransmitterMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon);
void ReceiverMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon);
void StringLoggerHandler(char *pString);
IOReturn packetDataFetchHandler (UInt32 **ppBuf, bool *pDiscontinuityFlag, void *pRefCon);
IOReturn packetDataStoreHandler(UInt32 tsPacketCount, UInt32 **ppBuf, void *pRefCon);
IOReturn tsDemuxCallback(TSDemuxerMessage msg, PESPacketBuf* pPESPacket, void *pRefCon);
IOReturn MyAVCDeviceControllerNotification(AVCDeviceController *pAVCDeviceController, void *pRefCon, AVCDevice* pDevice);
IOReturn MyAVCDeviceMessageNotification(AVCDevice *pAVCDevice,
										natural_t messageType,
										void * messageArgument,
										void *pRefCon);

@implementation DVHSCapController

//////////////////////////////////////////////////////
// awakeFromNib
//////////////////////////////////////////////////////
- (void)awakeFromNib
{
	IOReturn err;
	NSBundle *appBundle = [NSBundle mainBundle];

	// Load the images from the resource directory
	DVHSPlayButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Normal" ofType: @"tif"]];
	DVHSStopButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Normal" ofType: @"tif"]];
	DVHSPauseButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Normal" ofType: @"tif"]];
	DVHSFFwdButtonNormalImage  = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"FastForwardButton-Normal" ofType: @"tif"]];
	DVHSFRevButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"RewindButton-Normal" ofType: @"tif"]];
	DVHSRecButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-0N" ofType: @"tiff"]];

	// Initialize the icon buttons
	[DVHSPlayButton setImage:DVHSPlayButtonNormalImage];
	[DVHSStopButton setImage:DVHSStopButtonNormalImage];
	[DVHSPauseButton setImage:DVHSPauseButtonNormalImage];
	[DVHSFFwdButton setImage:DVHSFFwdButtonNormalImage];
	[DVHSFRevButton setImage:DVHSFRevButtonNormalImage];
	[DVHSRecButton setImage:DVHSRecButtonNormalImage];
	[self DisableDVHSControllerUI];

	// Initialize Log
	avcLogString = [[NSMutableString stringWithCapacity:4096] retain];
	[avcLog setString:avcLogString];

	[PacketCount setIntValue:0];
	[Bitrate setIntValue:0];
	[Overruns setIntValue:0];

	// Instantiatie the StringLogger object
	stringLogger = new StringLogger(StringLoggerHandler);

	// Instantiate the TSDemuxer object
	deMux = new TSDemuxer(tsDemuxCallback,
					   nil,
					   nil,
					   nil,
					   1,
					   kMaxVideoPESSizeDefault,
					   kMaxAudioPESSizeDefault,
					   kDefaultVideoPESBufferCount,
					   kDefaultAudioPESBufferCount,
					   stringLogger);
	if (!deMux)
	{
		// TODO:Handle Error Here!
		[self addToAVCLog:@"Error: Failed to Create TSDemuxer Object\n"];
	}
	
	// Start a repeating timer to handle log & user-interface updates
	userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:0.50 target:self selector:@selector(userInterfaceUpdateTimerExpired:) userInfo:nil repeats:YES];

	// Initialize some other vars
	appState = kAppStateIdle;

	[CaptureButton setEnabled:YES];
	[CaptureButton setTitle:kCaptureButtonText];
	[ExportButton setEnabled:YES];
	[ExportButton setTitle:kExportButtonText];
	[ExportPreviewModeButton setEnabled:YES];
	
	// Set the global pointer to this object
	gpUserIntf = self;

	// Create a AVCDeviceController
	err = CreateAVCDeviceController(&pAVCDeviceController,MyAVCDeviceControllerNotification, nil);
	if (!pAVCDeviceController)
	{
		// TODO:Handle Error Here!
		[self addToAVCLog:@"Error creating AVCDeviceController object\n"];
	}
}

//////////////////////////////////////////////////////
// DVHSPlayButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSPlayButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSPlay(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSStopButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSStopButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSStop(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSPauseButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSPauseButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSPause(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSFFwdButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSFFwdButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSFFwd(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSFRevButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSFRevButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSFRew(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSRecButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSRecButtonPushed:(id)sender
{
	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	DVHSRecord(pDVHSDevice);
}

//////////////////////////////////////////////////////
// DVHSPowerButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVHSPowerButtonPushed:(id)sender
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;
	UInt8 currentPowerState;
	UInt8 nextPowerState;

	// If we don't have a DVHS device, return now
	if (pDVHSDevice == nil)
		return;

	// Determine the current power state
	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = kAVCUnitAddress;
	cmd[2] = 0xB2;
	cmd[3] = 0x7F;
	size = 4;

	res = (*pDVHSDevice->avcInterface)->AVCCommand(pDVHSDevice->avcInterface, cmd, 4, response, &size);
	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		currentPowerState = response[3];
	}
	else
		return;

	// Decide on the next power state
	nextPowerState = (currentPowerState == 0x60) ? 0x70 : 0x60;

	// Set the power state
	cmd[0] = kAVCControlCommand;
	cmd[1] = kAVCUnitAddress;
	cmd[2] = 0xB2;
	cmd[3] = nextPowerState;
	size = 4;
	res = (*pDVHSDevice->avcInterface)->AVCCommand(pDVHSDevice->avcInterface, cmd, 4, response, &size);

	// Get the power state and update the UI field
	GetDVHSDeckPowerState(pDVHSDevice);

}

//////////////////////////////////////////////////////
// EnableDVHSControllerUI
//////////////////////////////////////////////////////
- (void) EnableDVHSControllerUI
{
	[DVHSPlayButton setEnabled:YES];
	[DVHSStopButton setEnabled:YES];
	[DVHSPauseButton setEnabled:YES];
	[DVHSFFwdButton setEnabled:YES];
	[DVHSFRevButton setEnabled:YES];
	[DVHSRecButton setEnabled:YES];
	[DVHSPowerButton setEnabled:YES];
	[self updateDVHSTimecode:@""];
	[self updateDVHSState:@""];
	[self updateDVHSPowerState:@""];
}

//////////////////////////////////////////////////////
// DisableDVHSControllerUI
//////////////////////////////////////////////////////
- (void) DisableDVHSControllerUI
{
	[DVHSPlayButton setEnabled:NO];
	[DVHSStopButton setEnabled:NO];
	[DVHSPauseButton setEnabled:NO];
	[DVHSFFwdButton setEnabled:NO];
	[DVHSFRevButton setEnabled:NO];
	[DVHSRecButton setEnabled:NO];
	[DVHSPowerButton setEnabled:NO];
	[self updateDVHSDeviceName:@"No DVHS Device"];
	[self updateDVHSTimecode:@""];
	[self updateDVHSState:@""];
	[self updateDVHSPowerState:@""];
}

//////////////////////////////////////////////////////
// updateDVHSTimecode
//////////////////////////////////////////////////////
- (void) updateDVHSTimecode: (NSString*)s
{
    [DVHSTimecode setStringValue:s];
}

//////////////////////////////////////////////////////
// updateDVHSState
//////////////////////////////////////////////////////
- (void) updateDVHSState: (NSString*)s
{
    [DVHSState setStringValue:s];
}

//////////////////////////////////////////////////////
// updateDVHSDeviceName
//////////////////////////////////////////////////////
- (void) updateDVHSDeviceName: (NSString*)s
{
    [DVHSDeviceName setStringValue:s];
}

//////////////////////////////////////////////////////
// updateDVHSDeviceName
//////////////////////////////////////////////////////
- (void) updateDVHSPowerState: (NSString*)s
{
    [DVHSPowerState setStringValue:s];
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
// stopCapture
//////////////////////////////////////////////////////
- (void) stopCapture
{
	[ExportButton setEnabled:YES];
	[CaptureButton setTitle:kCaptureButtonText];
	[self DVHSStopButtonPushed:self];

	pDVHSDevice->StopAVCDeviceStream(pAVCDeviceStream);
	pDVHSDevice->DestroyAVCDeviceStream(pAVCDeviceStream);
	pAVCDeviceStream = nil;
	
	if (demuxDuringCapture == true)
	{
		fclose(outVideoFile);
		fclose(outAudioFile);
	}
	else
	{
		fclose(outFile);
	}
	
	[Bitrate setIntValue:0];
	appState = kAppStateIdle;
}

//////////////////////////////////////////////////////
// stopExport
//////////////////////////////////////////////////////
- (void) stopExport
{
	[CaptureButton setEnabled:YES];
	[ExportPreviewModeButton setEnabled:YES];
	[ExportButton setTitle:kExportButtonText];
	if ([ExportPreviewModeButton state] == NSOffState)
	{
		[self DVHSStopButtonPushed:self];
	}

	pDVHSDevice->StopAVCDeviceStream(pAVCDeviceStream);
	pDVHSDevice->DestroyAVCDeviceStream(pAVCDeviceStream);
	pAVCDeviceStream = nil;
	
	fclose(inFile);
	[Bitrate setIntValue:0];
	appState = kAppStateIdle;
}

//////////////////////////////////////////////////////
// CaptureButtonPushed
//////////////////////////////////////////////////////
- (IBAction) CaptureButtonPushed:(id)sender
{
	int status;
	NSSavePanel *savePanel = [NSSavePanel savePanel];
	char outVideoFileName[255];
	char outAudioFileName[255];

	if (pDVHSDevice == nil)
	{	
		[self addToAVCLog:@"Error: Cannot capture because no DVHS/HDV device has been detected!\n"];
		return;
	}
	
	switch (appState)
	{
		case kAppStateIdle:
			[ExportButton setEnabled:NO];
			[CaptureButton setTitle:kStopCaptureText];

			[savePanel setTitle:@"Select Capture File"];
			[savePanel setRequiredFileType:@"m2t"];
			status = [savePanel runModal];
			if (status != NSOKButton)
			{
				[FileName setStringValue:@"No File Selected"];
				[ExportButton setEnabled:YES];
				[CaptureButton setTitle:kCaptureButtonText];
			}
			else
			{
				[FileName setStringValue:[savePanel filename]];

				// Read state of demux during capture mode button
				if ([CaptureDemuxModeButton state] == NSOffState)
				{
					demuxDuringCapture = false;
					outFile = fopen([[savePanel filename] cString],"wb");
					if (!outFile)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error: Unable to open output file: %@\n",[savePanel filename]]];
						[ExportButton setEnabled:YES];
						[CaptureButton setTitle:kCaptureButtonText];
					}
					else
					{
						packetCount = 0;
						pAVCDeviceStream = pDVHSDevice->CreateMPEGReceiverForDevicePlug(0,
																	  packetDataStoreHandler,
																	  nil,
																	  ReceiverMessageReceivedProc,
																	  nil,
																	  stringLogger,
																	  (kCyclesPerReceiveSegment+kReceiverExtraPacketCount),
																	  kNumReceiveSegments);
						if (pAVCDeviceStream == nil)
						{
							[self addToAVCLog:@"Error creating MPEG2Receiver object for device\n"];
							fclose(outFile);
							[ExportButton setEnabled:YES];
							[CaptureButton setTitle:kCaptureButtonText];
						}
						else
						{
							pDVHSDevice->StartAVCDeviceStream(pAVCDeviceStream);
							[self resetDCLOverrunCount];
							[self DVHSPlayButtonPushed:self];
							appState = kAppStateImport;
						}
					}
				}
				else
				{
					demuxDuringCapture = true;
					foundFirstIFrame = false;

					// Generate the outputfile names
					// by removing any file extension from
					// the TS file, and replacing it
					// with .mpv for video, and .mp3 for audio
					strncpy(outVideoFileName,[[savePanel filename] cString],255);
					strncpy(outAudioFileName,[[savePanel filename] cString],255);
					strtok(outVideoFileName,".");
					strtok(outAudioFileName,".");
					strcat(outVideoFileName,".mpv");
					strcat(outAudioFileName,".mp3");

					// Open the output files
					outVideoFile = fopen(outVideoFileName,"wb");
					if (outVideoFile == nil)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error: Unable to open output video file: %s\n",outVideoFileName]];
					}
					outAudioFile = fopen(outAudioFileName,"wb");
					if (outAudioFile == nil)
					{
						[self addToAVCLog:[NSString stringWithFormat:@"Error: Unable to open output audio file: %s\n",outAudioFileName]];
					}

					if ((outVideoFile == nil) || (outAudioFile == nil))
					{
						if (outVideoFile != nil)
							fclose(outVideoFile);
						if (outAudioFile != nil)
							fclose(outVideoFile);

						[ExportButton setEnabled:YES];
						[CaptureButton setTitle:kCaptureButtonText];
					}
					else
					{
						packetCount = 0;

						pAVCDeviceStream = pDVHSDevice->CreateMPEGReceiverForDevicePlug(0,
																	  packetDataStoreHandler,
																	  nil,
																	  ReceiverMessageReceivedProc,
																	  nil,
																	  stringLogger,
																	  (kCyclesPerReceiveSegment+kReceiverExtraPacketCount),
																	  kNumReceiveSegments);
						if (pAVCDeviceStream == nil)
						{
							[self addToAVCLog:@"Error creating MPEG2Receiver object for device\n"];
							fclose(outVideoFile);
							fclose(outVideoFile);
							[ExportButton setEnabled:YES];
							[CaptureButton setTitle:kCaptureButtonText];
						}
						else
						{
							pDVHSDevice->StartAVCDeviceStream(pAVCDeviceStream);
							[self resetDCLOverrunCount];
							[self DVHSPlayButtonPushed:self];
							appState = kAppStateImport;
						}
					}
				}
			}
			break;

		case kAppStateImport:
			[self stopCapture];
			break;

		case kAppStateExport:
		default:
			break;
	};
}

//////////////////////////////////////////////////////
// DVModeButtonPushed
//////////////////////////////////////////////////////
- (IBAction) DVModeButtonPushed:(id)sender
{
	
}

//////////////////////////////////////////////////////
// ExportButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ExportButtonPushed:(id)sender
{
	int status;
	NSOpenPanel *openPanel = [NSOpenPanel openPanel];

	switch (appState)
	{
		case kAppStateIdle:
			
			// If no device has been discovered, don't continue
			if (pDVHSDevice == nil)
			{
				[self addToAVCLog:@"Error: Cannot export because no DVHS/HDV device has been detected!\n"];
				return;
			}
			
			[CaptureButton setEnabled:NO];
			[ExportButton setTitle:kStopExportText];
			
			[openPanel setAllowsMultipleSelection:NO];
			[openPanel setCanChooseDirectories:NO];
			[openPanel setTitle:@"Select Export File"];
			status = [openPanel runModalForTypes:NULL];
			if (status != NSOKButton)
			{
				[FileName setStringValue:@"No File Selected"];
				[CaptureButton setEnabled:YES];
				[ExportButton setTitle:kExportButtonText];
			}
			else
			{
				[FileName setStringValue:[openPanel filename]];
				inFile = fopen([[openPanel filename] cString],"rb");
				if (!inFile)
				{
					[self addToAVCLog:[NSString stringWithFormat:@"Error: Unable to open input file: %@\n",[openPanel filename]]];
					[CaptureButton setEnabled:YES];
					[ExportButton setTitle:kExportButtonText];
				}
				else
				{
					//TODO: Verify file is indeed MPEG2-TS.

					if ([ExportPreviewModeButton state] == NSOffState)
					{
						[self DVHSRecButtonPushed:self];
					}

					[ExportPreviewModeButton setEnabled:NO];

					pAVCDeviceStream = pDVHSDevice->CreateMPEGTransmitterForDevicePlug(0,
																		packetDataFetchHandler,
																		nil,
																		TransmitterMessageReceivedProc,
																		nil,
																		stringLogger,
																	(kCyclesPerTransmitSegment+kTransmitterExtraPacketCount),
																		kNumTransmitSegments,
																		3,
																		kTSPacketQueueSizeInPackets);
					if (pAVCDeviceStream == nil)
					{
						[self addToAVCLog:@"Error creating MPEG2Transmitter object for device\n"];
						fclose(inFile);
						[CaptureButton setEnabled:YES];
						[ExportButton setTitle:kExportButtonText];
					}
					else
					{
						pDVHSDevice->StartAVCDeviceStream(pAVCDeviceStream);
						[self resetDCLOverrunCount];
						appState = kAppStateExport;
					}
				}
			}
			break;

		case kAppStateExport:
			[self stopExport];
			break;

		case kAppStateImport:
		default:
			break;
	};
}

//////////////////////////////////////////////////////
// userInterfaceUpdateTimerExpired
//////////////////////////////////////////////////////
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer
{
	if (pDVHSDevice != nil)
	{
		GetDVHSDeckTimeCode(pDVHSDevice);
		GetDVHSDeckTransportState(pDVHSDevice);
		GetDVHSDeckPowerState(pDVHSDevice);
	}

	switch (appState)
	{
		case kAppStateIdle:
			break;

		case kAppStateExport:
			[Bitrate setFloatValue:pAVCDeviceStream->pMPEGTransmitter->mpegDataRate];
			[PacketCount setIntValue:packetCount];
			if (transmitDone == true)
				[self stopExport];
			break;

		case kAppStateImport:
			[Bitrate setFloatValue:pAVCDeviceStream->pMPEGReceiver->mpegDataRate];
			[PacketCount setIntValue:packetCount];
			break;
			
		default:
			break;
	};
}	

//////////////////////////////////////////////////////
// incrementDCLOverrunCount
//////////////////////////////////////////////////////
- (void) incrementDCLOverrunCount
{
	[Overruns setIntValue:([Overruns intValue]+1)];
}

//////////////////////////////////////////////////////
// resetDCLOverrunCount
//////////////////////////////////////////////////////
- (void) resetDCLOverrunCount
{
	[Overruns setIntValue:0];
}

@end

///////////////////////////////////////////////////////////////////////////////////////
// GetDVHSDeckTimeCode
///////////////////////////////////////////////////////////////////////////////////////
void GetDVHSDeckTimeCode(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[8],response[8];
    IOReturn res;
	bool success = false;

	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0x57;
	cmd[3] = 0x71;
	cmd[4] = 0xFF;
	cmd[5] = 0xFF;
	cmd[6] = 0xFF;
	cmd[7] = 0xFF;

	size = 8;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 8, response, &size);

	if (res == kIOReturnSuccess)
	{
		if (response[0] == kAVCImplementedStatus)
		{
			// Formulate the relative time code into a string
			[gpUserIntf updateDVHSTimecode:[NSString stringWithFormat:@"%c%02d:%02d:%02d",
																  ((response[4] & 0x80) == 0x80) ? '-':'+',
				bcd2bin(response[7]),
				bcd2bin(response[6]),
				bcd2bin(response[5])]];
			success = true;
		}
		else
		{
			// Try the timecode comand
			cmd[0] = kAVCStatusInquiryCommand;
			cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
			cmd[2] = 0x51;
			cmd[3] = 0x71;
			cmd[4] = 0xFF;
			cmd[5] = 0xFF;
			cmd[6] = 0xFF;
			cmd[7] = 0xFF;

			size = 8;

			res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 8, response, &size);

			if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
			{
				[gpUserIntf updateDVHSTimecode:[NSString stringWithFormat:@"%02d:%02d:%02d",
					bcd2bin(response[7]),
					bcd2bin(response[6]),
					bcd2bin(response[5])]];
				success = true;
			}
		}
	}

	if (success == false)
		[gpUserIntf updateDVHSTimecode:@""];
}

///////////////////////////////////////////////////////////////////////////////////////
// GetDVHSDeckTransportState
///////////////////////////////////////////////////////////////////////////////////////
void GetDVHSDeckTransportState(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Preset the transport state var to unknown
	dvhsDeviceTransportState = kDVHSStateUnknown;

	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xD0;
	cmd[3] = 0x7F;
	size = 4;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);

	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		switch (response[2])
		{
			case 0xC1:	// Load medium
				[gpUserIntf updateDVHSState:@"No Tape"];
				dvhsDeviceTransportState = kDVHSStateUnknown;
				break;

			case 0xC2:	// Record
				if ((response[3] >= 0x31) && (response[3] <= 0x38))
				{
					[gpUserIntf updateDVHSState:@"Record Insert"];
					dvhsDeviceTransportState = kDVHSStateRecForward;
				}
				else if ((response[3] >= 0x41) && (response[3] <= 0x48))
				{
					[gpUserIntf updateDVHSState:@"Record Insert Pause"];
					dvhsDeviceTransportState = kDVHSStateRecForward;
				}
				else if (response[3] == 0x75)
				{
					[gpUserIntf updateDVHSState:@"Record"];
					dvhsDeviceTransportState = kDVHSStateRecForward;
				}
				else if (response[3] == 0x7D)
				{
					[gpUserIntf updateDVHSState:@"Record Pause"];
					dvhsDeviceTransportState = kDVHSStateRecPause;
				}
				else
				{
					[gpUserIntf updateDVHSState:@"Unknown Record"];
					dvhsDeviceTransportState = kDVHSStateRecForward;
				}
				break;

			case 0xC3:	// Play
				if (response[3] == 0x30)
				{
					[gpUserIntf updateDVHSState:@"Play Next Frame"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if ((response[3] >= 0x31) && (response[3] <= 0x37))
				{
					[gpUserIntf updateDVHSState:@"Play Fwd Slow"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x38)
				{
					[gpUserIntf updateDVHSState:@"Play Fwd Normal"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if ((response[3] >= 0x39) && (response[3] <= 0x3F))
				{
					[gpUserIntf updateDVHSState:@"Play Fwd Fast"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x40)
				{
					[gpUserIntf updateDVHSState:@"Play Prev Frame"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if ((response[3] >= 0x41) && (response[3] <= 0x47))
				{
					[gpUserIntf updateDVHSState:@"Play Rev Slow"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x48)
				{
					[gpUserIntf updateDVHSState:@"Play Rev Normal"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if ((response[3] >= 0x49) && (response[3] <= 0x4F))
				{
					[gpUserIntf updateDVHSState:@"Play Rev Fast"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x65)
				{
					[gpUserIntf updateDVHSState:@"Play Rev"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x6D)
				{
					[gpUserIntf updateDVHSState:@"Play Rev Pause"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x75)
				{
					[gpUserIntf updateDVHSState:@"Play Fwd"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				else if (response[3] == 0x7D)
				{
					[gpUserIntf updateDVHSState:@"Play Fwd Pause"];
					dvhsDeviceTransportState = kDVHSStatePlayPause;
				}
				else
				{
					[gpUserIntf updateDVHSState:@"Unknown Play"];
					dvhsDeviceTransportState = kDVHSStatePlayForward;
				}
				break;

			case 0xC4:	// Wind
				switch (response[3])
				{
					case 0x45:
						[gpUserIntf updateDVHSState:@"FastRewind"];
						dvhsDeviceTransportState = kDVHSStateFRew;
						break;

					case 0x60:
						[gpUserIntf updateDVHSState:@"Stop"];
						dvhsDeviceTransportState = kDVHSStateStopped;
						break;

					case 0x65:
						[gpUserIntf updateDVHSState:@"Rewind"];
						dvhsDeviceTransportState = kDVHSStateFRew;
						break;

					case 0x75:
						[gpUserIntf updateDVHSState:@"FastForward"];
						dvhsDeviceTransportState = kDVHSStateFFwd;
						break;

					default:
						[gpUserIntf updateDVHSState:@"Unknown Wind"];
						break;
				};
				break;

			default:
				[gpUserIntf updateDVHSState:@"Unknown"];
				break;
		};

	}
	else
		[gpUserIntf updateDVHSState:@""];
}

///////////////////////////////////////////////////////////////////////////////////////
// GetDVHSDeckPowerState
///////////////////////////////////////////////////////////////////////////////////////
void GetDVHSDeckPowerState(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	cmd[0] = kAVCStatusInquiryCommand;
	cmd[1] = kAVCUnitAddress;
	cmd[2] = 0xB2;
	cmd[3] = 0x7F;
	size = 4;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);

	if ((res == kIOReturnSuccess) && (response[0] == kAVCImplementedStatus))
	{
		if (response[3] == 0x70)
			[gpUserIntf updateDVHSPowerState:@"On"];
		else if (response[3] == 0x60)
			[gpUserIntf updateDVHSPowerState:@"Off"];
		else
			[gpUserIntf updateDVHSPowerState:@"Unknown"];
	}
	else
		[gpUserIntf updateDVHSPowerState:@""];
}

//////////////////////////////////////////////
// DVHSStop
//////////////////////////////////////////////
void DVHSStop(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Issue WindStop command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC4;	// Wind
	cmd[3] = 0x60;	// WindStop
	size = 4;
	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
}

//////////////////////////////////////////////
// DVHSPlay
//////////////////////////////////////////////
void DVHSPlay(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Only do something if we are currently in stopped state
	if (dvhsDeviceTransportState != kDVHSStateStopped)
		return;

	// Issue Play command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC3;	// Play
	cmd[3] = 0x75;	// Play normal
	size = 4;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
}

//////////////////////////////////////////////
// DVHSRecord
//////////////////////////////////////////////
void DVHSRecord(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Only do something if we are currently in stopped state
	if (dvhsDeviceTransportState != kDVHSStateStopped)
		return;

	// Issue Record Pause command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC2;	// Record
	cmd[3] = 0x7D;	// Record pause
	size = 4;
	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);

	do
	{
		cmd[0] = kAVCStatusInquiryCommand;
		cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
		cmd[2] = 0xD0; // Transport state command
		cmd[3] = 0x7F;
		size = 4;
		res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);

	}while ((res == kIOReturnSuccess) && (response[0] == 0x0b)); // Wait for transport state stable

	// Issue Record command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC2;	// Record
	cmd[3] = 0x75;	// Record normal
	size = 4;
	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
}

//////////////////////////////////////////////
// DVHSPause
//////////////////////////////////////////////
void DVHSPause(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	if (dvhsDeviceTransportState == kDVHSStateRecPause)
	{
		// Issue RecordFwd Command
		cmd[0] = kAVCControlCommand;
		cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
		cmd[2] = 0xC2;	// Record
		cmd[3] = 0x75;	// Record normal
		size = 4;
		res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
	}
	else if (dvhsDeviceTransportState == kDVHSStateRecForward)
	{
		// Issue RecordPause Command
		cmd[0] = kAVCControlCommand;
		cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
		cmd[2] = 0xC2;	// Record
		cmd[3] = 0x7D;	// Record pause
		size = 4;
		res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
	}
	else if (dvhsDeviceTransportState == kDVHSStatePlayPause)
	{
		// Issue PlayFwd Command
		cmd[0] = kAVCControlCommand;
		cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
		cmd[2] = 0xC3;	// Play
		cmd[3] = 0x75;	// Play normal
		size = 4;
		res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
	}
	else if (dvhsDeviceTransportState == kDVHSStatePlayForward)
	{
		// Issue PlayPause Command
		cmd[0] = kAVCControlCommand;
		cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
		cmd[2] = 0xC3;	// Play
		cmd[3] = 0x7D;	// Play pause
		size = 4;
		res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
	}
}

//////////////////////////////////////////////
// DVHSFFwd
//////////////////////////////////////////////
void DVHSFFwd(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Only do something if we are currently in stopped state
	if (dvhsDeviceTransportState != kDVHSStateStopped)
		return;

	// Issue Wind command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC4;	// Wind
	cmd[3] = 0x75;	// FFwd
	size = 4;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
}

//////////////////////////////////////////////
// DVHSFRew
//////////////////////////////////////////////
void DVHSFRew(AVCDevice *dvhsDevice)
{
    UInt32 size;
    UInt8 cmd[4],response[4];
    IOReturn res;

	// Only do something if we are currently in stopped state
	if (dvhsDeviceTransportState != kDVHSStateStopped)
		return;

	// Issue Wind command
	cmd[0] = kAVCControlCommand;
	cmd[1] = IOAVCAddress(kAVCTapeRecorder, 0);
	cmd[2] = 0xC4;	// Wind
	cmd[3] = 0x65;	// FRew
	size = 4;

	res = (*dvhsDevice->avcInterface)->AVCCommand(dvhsDevice->avcInterface, cmd, 4, response, &size);
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

//////////////////////////////////////////////////////////////////////
//
// TransmitterMessageReceivedProc
//
//////////////////////////////////////////////////////////////////////
void TransmitterMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon)
{
	switch (msg)
	{
		case kMpeg2TransmitterPreparePacketFetcher:
			// If we are in export state already, this call is due to a DCL Overrun
			if (appState != kAppStateExport)
			{
				[gpUserIntf resetDCLOverrunCount];
				packetCount = 0;
				xmitterPrerollCount = kMPEGXmitterPrerollCount;
			}
			if (msg == kMpeg2TransmitterPreparePacketFetcher)
			{
				[gpUserIntf incrementDCLOverrunCount];
				transmitDone = false;
				xmitterFlushMode = false;
				xmitterFlushCnt = 0;
			}
			break;
			
		case kMpeg2TransmitterAllocateIsochPort:
		case kMpeg2TransmitterReleaseIsochPort:
		default:
			break;
	};
}

//////////////////////////////////////////////////////////////////////
//
// ReceiverMessageReceivedProc
//
//////////////////////////////////////////////////////////////////////
void ReceiverMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon)
{
	switch (msg)
	{
		case kMpeg2ReceiverDCLOverrun:
		case kMpeg2ReceiverReceivedBadPacket:
			[gpUserIntf incrementDCLOverrunCount];
			break;

		case kMpeg2ReceiverAllocateIsochPort:
		case kMpeg2ReceiverReleaseIsochPort:
		default:
			break;
	};
}

//////////////////////////////////////////////////////////////////////
//
// StringLoggerHandler
//
//////////////////////////////////////////////////////////////////////
void StringLoggerHandler(char *pString)
{
	NSAutoreleasePool *pool = [[NSAutoreleasePool alloc]init];
	[gpUserIntf addToAVCLog:[NSString stringWithCString:pString]];
	[pool release];
}

//////////////////////////////////////////////////////////////////////
//
// packetDataFetchHandler
//
//////////////////////////////////////////////////////////////////////
IOReturn packetDataFetchHandler (UInt32 **ppBuf, bool *pDiscontinuityFlag, void *pRefCon)
{
	unsigned int cnt;
	IOReturn result = 0;

	// Signal no discontinuity
	*pDiscontinuityFlag = false;

	if (xmitterPrerollCount > 0)
	{
		xmitterPrerollCount -= 1;
		return -1;
	}
	
	if (xmitterFlushMode == false)
	{
		// Read the next TS packet from the input file
		cnt = fread(tsPacketBuf,1,kMPEG2TSPacketSize,inFile);
		if (cnt != kMPEG2TSPacketSize)
		{
			xmitterFlushMode = true;
			result = -1;	// Causes a CIP only cycle to be filled
		}
		else
		{
			packetCount += 1;
			*ppBuf = (UInt32*) tsPacketBuf;
		}
	}
	else
	{
		// This code runs the transmitter for enough additional cycles to
		// flush all the MPEG data from the DCL buffers 
		if (xmitterFlushCnt > ((kCyclesPerTransmitSegment * kNumTransmitSegments) + kTransmitterExtraPacketCount + kTSPacketQueueSizeInPackets  + kFireWireCyclesPerSecond))
			transmitDone = true;
		else
			xmitterFlushCnt += 1;
		result = -1;	// Causes a CIP only cycle to be filled
	}

	return result;
}	

//////////////////////////////////////////////////////////////////////
//
// packetDataStoreHandler
//
//////////////////////////////////////////////////////////////////////
IOReturn packetDataStoreHandler(UInt32 tsPacketCount, UInt32 **ppBuf, void *pRefCon)
{
	unsigned int i;
	unsigned int cnt;
	UInt8 *pTSPacketBytes;

	// Increment packet count for progress display
	packetCount += tsPacketCount;

	// Write packets to file
	for (i=0;i<tsPacketCount;i++)
	{
		if (demuxDuringCapture == false)
		{
			// Write TS packet to m2t file
			cnt = fwrite(ppBuf[i],1,kMPEG2TSPacketSize,outFile);
			if (cnt != kMPEG2TSPacketSize)
			{
				// Stop Capture
				[gpUserIntf stopCapture];
				return kIOReturnError;
			}
		}
		else
		{
			// Pass TS packet to demuxer
			pTSPacketBytes = (UInt8*) (ppBuf[i]);
			deMux->nextTSPacket(pTSPacketBytes);
		}
	}

	return kIOReturnSuccess;
}	

//////////////////////////////////////////////////////////////////////
//
// tsDemuxCallback
//
//////////////////////////////////////////////////////////////////////
IOReturn tsDemuxCallback(TSDemuxerMessage msg, PESPacketBuf* pPESPacket, void *pRefCon)
{
	// Local Vars
	UInt32 i;
	UInt32 strid = 0;
	unsigned int cnt;
	UInt32 pesHeaderLen;

	TSDemuxerStreamType streamType = pPESPacket->streamType;
	UInt8 *pPESBuf = pPESPacket->pPESBuf;
	UInt32 pesBufLen = pPESPacket->pesBufLen;

	if (msg == kTSDemuxerPESReceived)
	{
		// Throw away all PES packets until we find the first I-Frame packet
		if (foundFirstIFrame != true)
		{
			if (streamType == kTSDemuxerStreamTypeVideo)
			{
				// Look for a GOP Header. For MicroMV and JVC Mini-HD Streams,
				// all I-frames start with a GOP header
				for (i = 9+pPESBuf[8]; i < pesBufLen; i++)
				{
					strid = (strid << 8) | pPESBuf[i];
					if (strid == 0x000001B8) // group_start_code
					{
						[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Found First I-Frame\n"]];
						foundFirstIFrame = true;
						break;
					}
				}
			}
		}
		
		// If we've found the first I-Frame, add this PES
		// packet to the PS mux.
		if (foundFirstIFrame == true)
		{
			if (streamType == kTSDemuxerStreamTypeVideo)
			{
				// Write PES packet payload to video es file
				
				pesHeaderLen = 9+pPESBuf[8];
				
				cnt = fwrite(pPESBuf+pesHeaderLen,1,pesBufLen-pesHeaderLen,outVideoFile);
				if (cnt != pesBufLen-pesHeaderLen)
				{
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Error Writing to output video file!\n\n"]];
					[gpUserIntf stopCapture];
				}
			}
			else if (streamType == kTSDemuxerStreamTypeAudio)
			{
				// Write PES packet payload to audio es file
				
				pesHeaderLen = 9+pPESBuf[8];
				
				cnt = fwrite(pPESBuf+pesHeaderLen,1,pesBufLen-pesHeaderLen,outAudioFile);
				if (cnt != pesBufLen-pesHeaderLen)
				{
					[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"Error Writing to output audio file!\n\n"]];
					[gpUserIntf stopCapture];
				}
			}
		}
	}
	
	// Don't forget to release this PES buffer
	deMux->ReleasePESPacketBuf(pPESPacket);

	return kIOReturnSuccess;
}

//////////////////////////////////////////////////////////////////////
//
// MyAVCDeviceControllerNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyAVCDeviceControllerNotification(AVCDeviceController *pAVCDeviceController, void *pRefCon, AVCDevice* pDevice)
{
	IOReturn result = kIOReturnSuccess ;
	AVCDevice *pAVCDevice;
	UInt32 i;

	// If we already have a device, don't do anything
	if (pDVHSDevice != nil)
		return result;

	for (i=0;i<(UInt32)CFArrayGetCount(pAVCDeviceController->avcDeviceArray);i++)
	{
		pAVCDevice = (AVCDevice*) CFArrayGetValueAtIndex(pAVCDeviceController->avcDeviceArray,i);

		// See if this is a device we want to work with
		if ((pAVCDevice->isAttached == true) &&
	  (pAVCDevice->hasTapeSubunit == true) &&
	  (pAVCDevice->isMPEGDevice == true) &&
	  (pAVCDevice->isOpened() == false))
		{
			// Try opening the device
			result = pAVCDevice->openDevice(MyAVCDeviceMessageNotification, nil);
			if (result == kIOReturnSuccess)
			{
				pDVHSDevice = pAVCDevice;

				[gpUserIntf EnableDVHSControllerUI];
				[gpUserIntf addToAVCLog:[NSString stringWithFormat:@"External D-VHS Device Found: %s\n",pAVCDevice->deviceName]];
				[gpUserIntf updateDVHSDeviceName:[NSString stringWithFormat:@"%s\n",pAVCDevice->deviceName]];
				GetDVHSDeckTimeCode(pDVHSDevice);
				GetDVHSDeckTransportState(pDVHSDevice);
				GetDVHSDeckPowerState(pDVHSDevice);
				
			}
			break;
		}
	}

	return result;
}


//////////////////////////////////////////////////////////////////////
//
// MyAVCDeviceMessageNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyAVCDeviceMessageNotification(AVCDevice *pAVCDevice,
										natural_t messageType,
										void * messageArgument,
										void *pRefCon)
{


	switch (messageType)
	{
		case kIOMessageServiceIsRequestingClose:
			// If we have a stream running, stop it
			switch (appState)
			{
				case kAppStateExport:
					[gpUserIntf stopExport];
					break;

				case kAppStateImport:
					[gpUserIntf stopCapture];
					break;

				case kAppStateIdle:
				default:
					break;
			};
			// Close the device
			pDVHSDevice->closeDevice();
			pDVHSDevice = nil;
			break;

		default:
			break;
	};
	


	return kIOReturnSuccess;
}

