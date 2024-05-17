/*
	File:		AVHDD.mm

 Synopsis: This is the source file for the main application controller object

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

//
// Header Files
//
#include <stdio.h>
#include <pthread.h>
#include <mach/mach.h>
#include <mach/mach_port.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/fcntl.h>

#include <ApplicationServices/ApplicationServices.h>
#include <CoreServices/CoreServices.h>

#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/IOMessage.h>
#include <IOKit/firewire/IOFireWireLib.h>
#include <IOKit/firewire/IOFireWireLibIsoch.h>
#include <IOKit/avc/IOFireWireAVCLib.h>
#include <IOKit/avc/IOFireWireAVCConsts.h>

#import "AVHDD.h"
#import "PreferenceController.h"

#include "avcTarget.h"

#include "AVCTapeTgt.h"


#pragma mark -
#pragma mark ===================================
#pragma mark Defines
#pragma mark ===================================

#define kAVCMessageLogSize 100000

#define kMaxExtraTransmitCyclesPerSegment 600
#define kMaxExtraReceiveCyclesPerSegment 600

// Error Codes
#define kDVHSControllerErrorBase -5000
#define kDVHSControllerErrorInitializationError (kDVHSControllerErrorBase+0)

// Note: Must be in same order as items in preferences dialog combo-box!!!
DVFormatInfo pDVFormatTable[] =
{
	{0x00, 120000, @"DV25 NTSC",267,false,10,30,'dvc '},
	{0x80, 144000, @"DV25 PAL",320,true,12,25,'dvcp'},
	{0x78, 120000, @"DVCPro25 NTSC",267,false,10,30,'dvc '},
	{0xF8, 144000, @"DVCPro25 PAL",320,true,12,25,'dvpp'},
	{0x74, 240000, @"DVCPro50 NTSC",267,false,20,30,'dv5n'},
	{0xF4, 288000, @"DVCPro50 PAL",320,true,24,25,'dv5p'},
	{0x70, 480000, @"DVCProHD 1080i/60",267,false,40,30,'dvh6'},
	{0xF0, 576000, @"DVCProHD 1080i/50",320,true,48,25,'dvh5'},
	{0x70, 480000, @"DVCProHD 720p/60",267,false,40,30,'dvhp'}
};

// Time Code Modes - Index of items in the timecodeMode combo box
#define kTimeCodeMode_None 0
#define kTimeCodeMode_Insertion 1
#define kTimeCodeMode_Extraction 2

#pragma mark -
#pragma mark ===================================
#pragma mark Local Function Prototypes
#pragma mark ===================================

// Explicity add this prototype here, since
// it doesn't seem to be anywhere else!
extern "C" void MKGetTimeBaseInfo(unsigned int *delta,
								  unsigned int *abs_to_ns_num,
								  unsigned int *abs_to_ns_denom,
								  unsigned int *proc_to_abs_num,
								  unsigned int *proc_to_abs_denom);

// Prototpes
void *AVCThreadStart(AVHDD *uiObject);
void StringLoggerHandler(char *pString);
void TransmitterMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon);
void ReceiverMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon);
IOReturn DVFramePullProcHandler(UInt32 *pFrameIndex, void *pRefCon);
IOReturn DVFrameReleaseProcHandler(UInt32 frameIndex, void *pRefCon);
IOReturn DVFrameReceivedProcHandler(DVFrameReceiveMessage msg, DVReceiveFrame* pFrame, void *pRefCon);
void initialzeTransmitterFrameQueue(void);

// This function not in this source file
int DVInsertTimeCodeIntoFrame( void *pFrameData, int numDIFSequences, Boolean isPAL, void *pSubcodeData, unsigned int *pFrameCount, 
							   unsigned int *pHours, unsigned int *pMinutes, unsigned int *pSeconds, unsigned int *pFrames, Boolean *pIsDropFrame);

int DVExtractTimeCodeFromFrame( void * pFrameData, int numDIFSequences, Boolean ntscRate, long timeBase, void *pReturnSubcode,
								int *pFrameCount, int *pHours, int *pMinutes, int *pSeconds, int *pFrames, Boolean *pIsDropFrame);


// Global Vars
FILE *inoutFile = nil;
UInt64 inoutFileSize;
UInt32 inoutFileSizeInFrames;
UInt32 dvTransmitterLatencyInFrames;
NSString *inFileName;
AVHDD *gpUserIntf;
AVCTarget *gpAVC;
DVFormatInfoPtr gpDVFormatInfo;
DVTransmitter *gpXmitter;
DVReceiver *gpReceiver;
NSDate *recordStartTime;
volatile bool startAVCCommandProcessing = false;
UInt32 timeCodeInFrames = 0;

UInt32 numTransmitterFrames;
DVTransmitFrame* pFrameQueueHead;

#pragma mark -
#pragma mark ===================================
#pragma mark AVHDD Class Method Implementations
#pragma mark ===================================

@implementation AVHDD

#pragma mark -----------------------------------
#pragma mark Initialization/Destruction Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// initialize
//////////////////////////////////////////////////////
+ (void)initialize
{
    NSMutableDictionary *defaultValues = [NSMutableDictionary dictionary];
	[defaultValues setObject: [NSNumber numberWithInt:0] forKey:@"DVMode"];
	[defaultValues setObject: [NSNumber numberWithFloat:50.0] forKey:@"TransmitterBufferSize"];
	[defaultValues setObject: [NSNumber numberWithFloat:50.0] forKey:@"ReceiverBufferSize"];
	[[NSUserDefaults standardUserDefaults] registerDefaults:defaultValues];
}

//////////////////////////////////////////////////////
// awakeFromNib
//////////////////////////////////////////////////////
- (void)awakeFromNib
{
	NSBundle *appBundle = [NSBundle mainBundle];

	// Load the images from the resource directory
	XmitterPlayButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Normal" ofType: @"tif"]];
	XmitterPlayButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Running-Blue" ofType: @"tif"]];
	XmitterStopButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Normal" ofType: @"tif"]];
	XmitterStopButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Hilighted-Blue" ofType: @"tif"]];
	XmitterPauseButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Normal" ofType: @"tif"]];
	XmitterPauseButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Hilighted-Blue" ofType: @"tif"]];
	XmitterFFwdButtonNormalImage  = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"FastForwardButton-Normal" ofType: @"tif"]];
	XmitterFRevButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"RewindButton-Normal" ofType: @"tif"]];

	ReceiverRecButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-0N" ofType: @"tiff"]];
	ReceiverRecButtonRecordingImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-1H" ofType: @"tiff"]];
	
	// Initialize the icon buttons
	[XmitterPlayButton setImage:XmitterPlayButtonNormalImage];
	[XmitterStopButton setImage:XmitterStopButtonBlueImage];
	[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	[XmitterFFwdButton setImage:XmitterFFwdButtonNormalImage];
	[XmitterFRevButton setImage:XmitterFRevButtonNormalImage];	
	[XmitterPauseButton setEnabled:NO];
	[XmitterFFwdButton setEnabled:NO];
	[XmitterFRevButton setEnabled:NO];
	[XmitterFrameFwdButton setEnabled:NO];
	[XmitterFrameRevButton setEnabled:NO];
	[ReceiverRecButton setImage:ReceiverRecButtonNormalImage];

}

//////////////////////////////////////////////////////
// dealloc
//////////////////////////////////////////////////////
- (void) dealloc
{
	// Delete xmitter object
	if (xmitter)
		DestroyDVTransmitter(xmitter);

	// Delete receiver object
	if (receiver)
		DestroyDVReceiver(receiver);
	
	// Delete avc object
	if (avc)
		delete avc;

	[super dealloc];
}

#pragma mark -----------------------------------
#pragma mark Misc Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// setAVCThreadReady
//////////////////////////////////////////////////////
- (void) setAVCThreadReady
{
	AVCThreadReady = true;
}

//////////////////////////////////////////////////////
// showPreferencePanel
//////////////////////////////////////////////////////
- (IBAction) showPreferencePanel:(id)sender
{
	if (!preferenceController)
	{
		preferenceController = [[PreferenceController alloc] init];
	}
	[preferenceController showWindow:self];
}

//////////////////////////////////////////////////////
// inFileMutexLock
//////////////////////////////////////////////////////
- (void) inFileMutexLock
{
	// Get the mutex
	pthread_mutex_lock(&inFileAccessMutex);
}

//////////////////////////////////////////////////////
// inFileMutexUnLock
//////////////////////////////////////////////////////
- (void) inFileMutexUnLock
{
	// Release the mutex
	pthread_mutex_unlock(&inFileAccessMutex);
}

#pragma mark -----------------------------------
#pragma mark Logging & UI Update Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// addToAVCLog
//////////////////////////////////////////////////////
- (void) addToAVCLog: (NSString*)s
{
	// Get the mutex
	pthread_mutex_lock(&logAccessMutex);

	// Add the string to the holding array
	[avcLogUpdateStringArray addObject:s];

	// Release the mutex
	pthread_mutex_unlock(&logAccessMutex);
}

//////////////////////////////////////////////////////
// userInterfaceUpdateTimerExpired
//////////////////////////////////////////////////////
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer
{
	bool didUpdate = false;
	NSRange strRange;
	unsigned int strLen;
	UInt32 timeInFrames;
	UInt32 hours;
	UInt32 minutes;
	UInt32 seconds;
	UInt8 transport_mode,transport_state;

	// Get the mutex
	pthread_mutex_lock(&logAccessMutex);

	// Append the strings in the array to the log string
	while ([avcLogUpdateStringArray count] != 0)
	{
		[avcLogString appendString:[avcLogUpdateStringArray objectAtIndex:0]];
	
		[avcLogUpdateStringArray removeObjectAtIndex:0];
		didUpdate = true;
	}

	// Update if necessary
	if (didUpdate == true)
	{	
		[avcLog setString:avcLogString];

		// Set the range to point to the end of the string
		strRange.length=1;
		strLen = [avcLogString length];
		strRange.location=(strLen > 0) ? strLen-1 : 0;

		// Scroll the view to the end
		[avcLog scrollRangeToVisible:strRange];
	}

	// Release the mutex
	pthread_mutex_unlock(&logAccessMutex);


	// Update the timecode value & position slider & filesize 
	if (inoutFile)
	{
		[self updateDVStreamFileSize:inoutFileSize];
		[streamPositionSlider setFloatValue:(100.0*((ftello(inoutFile)*1.0)/(inoutFileSize*1.0)))];
		timeInFrames = timeCodeInFrames;
		hours = timeInFrames / 108000;
		timeInFrames -= (hours*timeInFrames);
		minutes = timeInFrames / 1800;
		timeInFrames -= (minutes*1800);
		seconds = timeInFrames / 30;
		timeInFrames -= (seconds*30);
		[self updateOutputPlugTimecode:[NSString stringWithFormat:@"%02d:%02d:%02d.%02d",hours,minutes,seconds,timeInFrames]];
	}

	// Update the transport state display
	AVCTapeTgtGetState(&transport_mode,&transport_state);
	if (transport_mode == kAVCTapePlayOpcode)
	{
		[self updateOutputPlugState:@"Playing"];
		switch (transport_state)
		{
			case kAVCTapePlayNextFrame:
				[self updateOutputPlugStateExtended:@"Next Frame"];
				break;
			case kAVCTapePlaySlowestFwd:
				[self updateOutputPlugStateExtended:@"Slowest Forward"];
				break;
			case kAVCTapePlaySlowFwd6:
				[self updateOutputPlugStateExtended:@"Slow Forward 6"];
				break;
			case kAVCTapePlaySlowFwd5:
				[self updateOutputPlugStateExtended:@"Slow Forward 5"];
				break;
			case kAVCTapePlaySlowFwd4:
				[self updateOutputPlugStateExtended:@"Slow Forward 4"];
				break;
			case kAVCTapePlaySlowFwd3:
				[self updateOutputPlugStateExtended:@"Slow Forward 3"];
				break;
			case kAVCTapePlaySlowFwd2:
				[self updateOutputPlugStateExtended:@"Slow Forward 2"];
				break;
			case kAVCTapePlaySlowFwd1:
				[self updateOutputPlugStateExtended:@"Slow Forward 1"];
				break;
			case kAVCTapePlayX1:
			case kAVCTapePlayFwd:
				[self updateOutputPlugStateExtended:@"1x Forward"];
				break;
			case kAVCTapePlayFastFwd1:
				[self updateOutputPlugStateExtended:@"Fast Forward 1"];
				break;
			case kAVCTapePlayFastFwd2:
				[self updateOutputPlugStateExtended:@"Fast Forward 2"];
				break;
			case kAVCTapePlayFastFwd3:
				[self updateOutputPlugStateExtended:@"Fast Forward 3"];
				break;
			case kAVCTapePlayFastFwd4:
				[self updateOutputPlugStateExtended:@"Fast Forward 4"];
				break;
			case kAVCTapePlayFastFwd5:
				[self updateOutputPlugStateExtended:@"Fast Forward 5"];
				break;
			case kAVCTapePlayFastFwd6:
				[self updateOutputPlugStateExtended:@"Fast Forward 6"];
				break;
			case kAVCTapePlayFastestFwd:
				[self updateOutputPlugStateExtended:@"Fastest Forward"];
				break;
			case kAVCTapePlayPrevFrame:
				[self updateOutputPlugStateExtended:@"Previous Frame"];
				break;
			case kAVCTapePlaySlowestRev:
				[self updateOutputPlugStateExtended:@"Slowest Reverse"];
				break;
			case kAVCTapePlaySlowRev6:
				[self updateOutputPlugStateExtended:@"Slow Reverse 6"];
				break;
			case kAVCTapePlaySlowRev5:
				[self updateOutputPlugStateExtended:@"Slow Reverse 5"];
				break;
			case kAVCTapePlaySlowRev4:
				[self updateOutputPlugStateExtended:@"Slow Reverse 4"];
				break;
			case kAVCTapePlaySlowRev3:
				[self updateOutputPlugStateExtended:@"Slow Reverse 3"];
				break;
			case kAVCTapePlaySlowRev2:
				[self updateOutputPlugStateExtended:@"Slow Reverse 2"];
				break;
			case kAVCTapePlaySlowRev1:
				[self updateOutputPlugStateExtended:@"Slow Reverse 1"];
				break;
			case kAVCTapePlayX1Rev:
			case kAVCTapePlayRev:
				[self updateOutputPlugStateExtended:@"1x Reverse"];
				break;
			case kAVCTapePlayFastRev1:
				[self updateOutputPlugStateExtended:@"Fast Reverse 1"];
				break;
			case kAVCTapePlayFastRev2:
				[self updateOutputPlugStateExtended:@"Fast Reverse 2"];
				break;
			case kAVCTapePlayFastRev3:
				[self updateOutputPlugStateExtended:@"Fast Reverse 3"];
				break;
			case kAVCTapePlayFastRev4:
				[self updateOutputPlugStateExtended:@"Fast Reverse 4"];
				break;
			case kAVCTapePlayFastRev5:
				[self updateOutputPlugStateExtended:@"Fast Reverse 5"];
				break;
			case kAVCTapePlayFastRev6:
				[self updateOutputPlugStateExtended:@"Fast Reverse 6"];
				break;
			case kAVCTapePlayFastestRev:
				[self updateOutputPlugStateExtended:@"Fastest Reverse"];
				break;
			case kAVCTapePlayRevPause:
				[self updateOutputPlugStateExtended:@"Reverse Pause"];
				break;
			case kAVCTapePlayFwdPause:
				[self updateOutputPlugStateExtended:@"Forward Pause"];
				break;
			default:
				[self updateOutputPlugStateExtended:@""];
				break;
		};
		
		if ((transport_state == kAVCTapePlayRevPause) || (transport_state == kAVCTapePlayFwdPause))
			[XmitterPauseButton setImage:XmitterPauseButtonBlueImage];
		else
			[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	}
	else if (transport_mode == kAVCTapeRecordOpcode)
	{
		[self updateOutputPlugState:@"Recording"];
		switch (transport_state)
		{
			case kAVCTapeRecRecord:
				[self updateOutputPlugStateExtended:@""];
				break;
				
			case kAVCTapeRecordRecordPause:
				[self updateOutputPlugStateExtended:@"Pause"];
				break;

			default:
				[self updateOutputPlugStateExtended:@"Other"]; // should never see!
				break;
		};
		if (transport_state == kAVCTapeRecordRecordPause)
			[XmitterPauseButton setImage:XmitterPauseButtonBlueImage];
		else
			[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	}
	else
	{
		[self updateOutputPlugState:@"Stopped"];
		[self updateOutputPlugStateExtended:@""];
	}
}

//////////////////////////////////////////////////////
// clearLog
//////////////////////////////////////////////////////
- (IBAction) clearLog:(id)sender
{
	NSRange strRange;
	unsigned int strLen;

	NSLog(@"clearLog button pressed\n");

	// Get the mutex
	pthread_mutex_lock(&logAccessMutex);

	// Start over with an empty log string
	[avcLogString autorelease];
	avcLogString = [[NSMutableString stringWithCapacity:kAVCMessageLogSize] retain];
	NSLog(@"clearing Log...\n");
	[avcLog setString:avcLogString];

	// Set the range to point to the end of the string
	strRange.length=1;
	strLen = [avcLogString length];
	strRange.location=(strLen > 0) ? strLen-1 : 0;

	// Scroll the view to the end
	[avcLog scrollRangeToVisible:strRange];
	[avcLog display];

	// Release the mutex
	pthread_mutex_unlock(&logAccessMutex);
}

//////////////////////////////////////////////////////
// verboseAVCButtonPushed
//////////////////////////////////////////////////////
- (IBAction) verboseAVCButtonPushed:(id)sender
{
	NSLog(@"verboseAVCButtonPushed: %d\n",[verboseAVCLoggingButton state]);
}

//////////////////////////////////////////////////////
// verboseAVCLoggingEnabled
//////////////////////////////////////////////////////
- (bool) verboseAVCLoggingEnabled
{
    if ([verboseAVCLoggingButton state])
        return true;
    else
        return false;
}

//////////////////////////////////////////////////////
// isWriteProtect
//////////////////////////////////////////////////////
- (BOOL)isWriteProtect
{
    if ([writeProtectDVStreamFileButton state])
        return true;
    else
        return false;
}

//////////////////////////////////////////////////////
// shouldLoopPlaBack
//////////////////////////////////////////////////////
- (BOOL)shouldLoopPlaBack
{
    if ([LoopPlaybackButton state])
        return true;
    else
        return false;
}

//////////////////////////////////////////////////////
// shouldDoTimeCodeInsertion
//////////////////////////////////////////////////////
- (BOOL)shouldDoTimeCodeInsertion
{
	if ([timecodeMode indexOfSelectedItem] == kTimeCodeMode_Insertion)
        return true;
    else
        return false;
}

//////////////////////////////////////////////////////
// currentTimeCodeMode
//////////////////////////////////////////////////////
- (unsigned int) currentTimeCodeMode
{
	return [timecodeMode indexOfSelectedItem];
}



#pragma mark -----------------------------------
#pragma mark DV Transmitter Button Function
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// XmitterPlayButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterPlayButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	
	if (avc->transmitStarted == false)
	{
		[self avcPlayCmdHandler];
		AVCTapeTgtSetState(kAVCTapePlayOpcode, kAVCTapePlayFwd);
	}
	else
	{
		AVCTapeTgtGetState(&transport_mode,&transport_state);
		if (transport_mode == kAVCTapePlayOpcode)
			AVCTapeTgtSetState(kAVCTapePlayOpcode, kAVCTapePlayFwd);
	}
}

//////////////////////////////////////////////////////
// XmitterStopButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterStopButtonPushed:(id)sender
{
	if (avc->transmitStarted == true)
		[self avcStopCmdHandler];
	else if (avc->receiveStarted == true)
		[self avcRecordStopCmdHandler];

	AVCTapeTgtSetState(kAVCTapeWindOpcode,kAVCTapeWindStop);
}
//////////////////////////////////////////////////////
// XmitterPauseButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterPauseButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
    if (avc->transmitStarted == true)
    {
		AVCTapeTgtGetState(&transport_mode,&transport_state);
        if ((transport_mode == kAVCTapePlayOpcode) && 
			((transport_state == kAVCTapePlayRevPause) ||(transport_state == kAVCTapePlayFwdPause)))
        {
			AVCTapeTgtSetState(transport_mode,kAVCTapePlayFwd);
		}
        else
        {
			AVCTapeTgtSetState(transport_mode,kAVCTapePlayFwdPause);
        }
    }
	else if (avc->receiveStarted == true)
    {
		AVCTapeTgtGetState(&transport_mode,&transport_state);
		if ((transport_mode == kAVCTapeRecordOpcode) && (transport_state == kAVCTapeRecordRecordPause))
			AVCTapeTgtSetState(transport_mode,kAVCTapeRecRecord);
		else
			AVCTapeTgtSetState(transport_mode,kAVCTapeRecordRecordPause);
	}
}

//////////////////////////////////////////////////////
// XmitterFFwdButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterFFwdButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	AVCTapeTgtGetState(&transport_mode,&transport_state);
	if (transport_mode == kAVCTapePlayOpcode)
	{
		switch (transport_state)
		{
			case kAVCTapePlayNextFrame:
				transport_state = kAVCTapePlayFwdPause;
				break;
			case kAVCTapePlaySlowestFwd:
			case kAVCTapePlaySlowFwd6:
				transport_state = kAVCTapePlaySlowFwd5;
				break;
			case kAVCTapePlaySlowFwd5:
				transport_state = kAVCTapePlaySlowFwd4;
				break;
			case kAVCTapePlaySlowFwd4:
				transport_state = kAVCTapePlaySlowFwd3;
				break;
			case kAVCTapePlaySlowFwd3:
				transport_state = kAVCTapePlaySlowFwd2;
				break;
			case kAVCTapePlaySlowFwd2:
				transport_state = kAVCTapePlaySlowFwd1;
				break;
			case kAVCTapePlaySlowFwd1:
				transport_state = kAVCTapePlayFwd;
				break;
			case kAVCTapePlayX1:
			case kAVCTapePlayFwd:
				transport_state = kAVCTapePlayFastFwd1;
				break;
			case kAVCTapePlayFastFwd1:
				transport_state = kAVCTapePlayFastFwd2;
				break;
			case kAVCTapePlayFastFwd2:
				transport_state = kAVCTapePlayFastFwd3;
				break;
			case kAVCTapePlayFastFwd3:
				transport_state = kAVCTapePlayFastFwd4;
				break;
			case kAVCTapePlayFastFwd4:
				transport_state = kAVCTapePlayFastFwd5;
				break;
			case kAVCTapePlayFastFwd5:
				transport_state = kAVCTapePlayFastFwd6;
				break;
			case kAVCTapePlayFastFwd6:
			case kAVCTapePlayFastestFwd:
				transport_state = kAVCTapePlayFastestFwd;
				break;
			case kAVCTapePlayPrevFrame:
				transport_state = kAVCTapePlayRevPause;
				break;
			case kAVCTapePlaySlowestRev:
			case kAVCTapePlaySlowRev6:
				transport_state = kAVCTapePlayRevPause;
				break;
			case kAVCTapePlaySlowRev5:
				transport_state = kAVCTapePlaySlowRev6;
				break;
			case kAVCTapePlaySlowRev4:
				transport_state = kAVCTapePlaySlowRev5;
				break;
			case kAVCTapePlaySlowRev3:
				transport_state = kAVCTapePlaySlowRev4;
				break;
			case kAVCTapePlaySlowRev2:
				transport_state = kAVCTapePlaySlowRev3;
				break;
			case kAVCTapePlaySlowRev1:
				transport_state = kAVCTapePlaySlowRev2;
				break;
			case kAVCTapePlayX1Rev:
			case kAVCTapePlayRev:
				transport_state = kAVCTapePlaySlowRev1;
				break;
			case kAVCTapePlayFastRev1:
				transport_state = kAVCTapePlayRev;
				break;
			case kAVCTapePlayFastRev2:
				transport_state = kAVCTapePlayFastRev1;
				break;
			case kAVCTapePlayFastRev3:
				transport_state = kAVCTapePlayFastRev2;
				break;
			case kAVCTapePlayFastRev4:
				transport_state = kAVCTapePlayFastRev3;
				break;
			case kAVCTapePlayFastRev5:
				transport_state = kAVCTapePlayFastRev4;
				break;
			case kAVCTapePlayFastRev6:
			case kAVCTapePlayFastestRev:
				transport_state = kAVCTapePlayFastRev5;
				break;
			case kAVCTapePlayRevPause:
				transport_state = kAVCTapePlayFwdPause;
				break;
			case kAVCTapePlayFwdPause:
				transport_state = kAVCTapePlaySlowestFwd;
				break;
			default:
				break;
		};
		AVCTapeTgtSetState(transport_mode,transport_state);
	}
}

//////////////////////////////////////////////////////
// XmitterFRevButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterFRevButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	AVCTapeTgtGetState(&transport_mode,&transport_state);
	if (transport_mode == kAVCTapePlayOpcode)
	{
		switch (transport_state)
		{
			case kAVCTapePlayNextFrame:
				transport_state = kAVCTapePlayFwdPause;
				break;
			case kAVCTapePlaySlowestFwd:
			case kAVCTapePlaySlowFwd6:
				transport_state = kAVCTapePlayFwdPause;
				break;
			case kAVCTapePlaySlowFwd5:
				transport_state = kAVCTapePlaySlowFwd6;
				break;
			case kAVCTapePlaySlowFwd4:
				transport_state = kAVCTapePlaySlowFwd5;
				break;
			case kAVCTapePlaySlowFwd3:
				transport_state = kAVCTapePlaySlowFwd4;
				break;
			case kAVCTapePlaySlowFwd2:
				transport_state = kAVCTapePlaySlowFwd3;
				break;
			case kAVCTapePlaySlowFwd1:
				transport_state = kAVCTapePlaySlowFwd2;
				break;
			case kAVCTapePlayX1:
			case kAVCTapePlayFwd:
				transport_state = kAVCTapePlayRev;
				break;
			case kAVCTapePlayFastFwd1:
				transport_state = kAVCTapePlayFwd;
				break;
			case kAVCTapePlayFastFwd2:
				transport_state = kAVCTapePlayFastFwd1;
				break;
			case kAVCTapePlayFastFwd3:
				transport_state = kAVCTapePlayFastFwd2;
				break;
			case kAVCTapePlayFastFwd4:
				transport_state = kAVCTapePlayFastFwd3;
				break;
			case kAVCTapePlayFastFwd5:
				transport_state = kAVCTapePlayFastFwd4;
				break;
			case kAVCTapePlayFastFwd6:
			case kAVCTapePlayFastestFwd:
				transport_state = kAVCTapePlayFastFwd5;
				break;
			case kAVCTapePlayPrevFrame:
				transport_state = kAVCTapePlayRevPause;
				break;
			case kAVCTapePlaySlowestRev:
			case kAVCTapePlaySlowRev6:
				transport_state = kAVCTapePlaySlowRev5;
				break;
			case kAVCTapePlaySlowRev5:
				transport_state = kAVCTapePlaySlowRev4;
				break;
			case kAVCTapePlaySlowRev4:
				transport_state = kAVCTapePlaySlowRev3;
				break;
			case kAVCTapePlaySlowRev3:
				transport_state = kAVCTapePlaySlowRev2;
				break;
			case kAVCTapePlaySlowRev2:
				transport_state = kAVCTapePlaySlowRev1;
				break;
			case kAVCTapePlaySlowRev1:
				transport_state = kAVCTapePlayRev;
				break;
			case kAVCTapePlayX1Rev:
			case kAVCTapePlayRev:
				transport_state = kAVCTapePlayFastRev1;
				break;
			case kAVCTapePlayFastRev1:
				transport_state = kAVCTapePlayFastRev2;
				break;
			case kAVCTapePlayFastRev2:
				transport_state = kAVCTapePlayFastRev3;
				break;
			case kAVCTapePlayFastRev3:
				transport_state = kAVCTapePlayFastRev4;
				break;
			case kAVCTapePlayFastRev4:
				transport_state = kAVCTapePlayFastRev5;
				break;
			case kAVCTapePlayFastRev5:
				transport_state = kAVCTapePlayFastRev6;
				break;
			case kAVCTapePlayFastRev6:
			case kAVCTapePlayFastestRev:
				transport_state = kAVCTapePlayFastestRev;
				break;
			case kAVCTapePlayRevPause:
				transport_state = kAVCTapePlaySlowestRev;
				break;
			case kAVCTapePlayFwdPause:
				transport_state = kAVCTapePlayRevPause;
				break;
			default:
				break;
		};
		AVCTapeTgtSetState(transport_mode,transport_state);
	}
}

//////////////////////////////////////////////////////
// XmitterFrameFwdButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterFrameFwdButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	AVCTapeTgtGetState(&transport_mode,&transport_state);
	if (transport_mode == kAVCTapePlayOpcode)
		AVCTapeTgtSetState(transport_mode,kAVCTapePlayNextFrame);
}
//////////////////////////////////////////////////////
// XmitterFrameRevButtonPushed
//////////////////////////////////////////////////////
- (IBAction) XmitterFrameRevButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	AVCTapeTgtGetState(&transport_mode,&transport_state);
	if (transport_mode == kAVCTapePlayOpcode)
		AVCTapeTgtSetState(transport_mode,kAVCTapePlayPrevFrame);
}


//////////////////////////////////////////////////////
// streamPositionSliderModified
//////////////////////////////////////////////////////
- (IBAction) streamPositionSliderModified:(id)sender
{
	NSLog(@"streamPositionSliderModified: %f",[streamPositionSlider floatValue]);

	if (inoutFile)
	{
		double newLocationFrame = ([streamPositionSlider floatValue]/100.0) *
		(inoutFileSize / gpDVFormatInfo->frameSize);

		long long seekLocation = (long long) newLocationFrame * gpDVFormatInfo->frameSize;

		NSLog(@"seekLocation: %lld",seekLocation);

		[self inFileMutexLock];

		// Adjust the file read pointer
		fseeko(inoutFile,seekLocation,SEEK_SET);
		timeCodeInFrames = (seekLocation/gpDVFormatInfo->frameSize);
		
		// If not in timecode extraction mode, set the timecode based on file position
		if ([self currentTimeCodeMode] != kTimeCodeMode_Extraction)
			AVCTapeTgtSetTimeCode(timeCodeInFrames);

		[self inFileMutexUnLock];
	}
}

#pragma mark -----------------------------------
#pragma mark DV Receiver Button Function
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// ReceiverRecButtonPushed
//////////////////////////////////////////////////////
- (IBAction) ReceiverRecButtonPushed:(id)sender
{
	UInt8 transport_mode,transport_state;
	
	if (avc->receiveStarted == false)
	{
		[self avcRecordCmdHandler];

		AVCTapeTgtSetState(kAVCTapeRecordOpcode,kAVCTapeRecRecord);
	}	
	else
	{
		AVCTapeTgtGetState(&transport_mode,&transport_state);
		if (transport_mode == kAVCTapeRecordOpcode)
			AVCTapeTgtSetState(kAVCTapeRecordOpcode, kAVCTapeRecRecord);
	}
	
}

#pragma mark -----------------------------------
#pragma mark Transmitter/Receiver Channel Get/Set Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// openExistingDVStreamFileButtonPushed
//////////////////////////////////////////////////////
- (IBAction) openExistingDVStreamFileButtonPushed:(id)sender;
{
	int status;
	
	NSOpenPanel *openPanel = [NSOpenPanel openPanel];
	
	[openPanel setAllowsMultipleSelection:NO];
	[openPanel setCanChooseDirectories:NO];
	[openPanel setTitle:@"Open DV Stream File"];
	status = [openPanel runModalForTypes:NULL];
	if (status == NSOKButton)
	{
		[self inFileMutexLock];
		
		// If we have a file already open, close it now
		if (inoutFile != nil)
		{
			fclose(inoutFile);
		}
		
		inoutFile = fopen([[openPanel filename] cString],"rb+");
		if (inoutFile)
		{
			[dvStreamFileName setStringValue:[openPanel filename]];
			[CloseDVStreamFileButton setEnabled:YES];
			
			fseeko(inoutFile,0,SEEK_END);
			inoutFileSize = ftello(inoutFile);
			inoutFileSizeInFrames = inoutFileSize/gpDVFormatInfo->frameSize;
			timeCodeInFrames = 0;
			AVCTapeTgtSetTimeCode(timeCodeInFrames);
			fseeko(inoutFile,0,SEEK_SET);
			[self updateDVStreamFileSize:inoutFileSize];
		}
		else
		{
			[dvStreamFileName setStringValue:@"Unable to open selected file!"];
			[CloseDVStreamFileButton setEnabled:NO];
		}

		[self inFileMutexUnLock];
	}				
}

//////////////////////////////////////////////////////
// CreateNewDVStreamFileButtonPushed
//////////////////////////////////////////////////////
- (IBAction) CreateNewDVStreamFileButtonPushed:(id)sender
{
	int status;
	NSSavePanel *savePanel = [NSSavePanel savePanel];
	
	[savePanel setTitle:@"Create DV Stream File"];
	[savePanel setRequiredFileType:@"dv"];
	status = [savePanel runModal];
	if (status == NSOKButton)
	{
		[self inFileMutexLock];

		// If we have a file already open, close it now
		if (inoutFile != nil)
		{
			fclose(inoutFile);
		}
		
		inoutFile = fopen([[savePanel filename] cString],"wb+");
		if (inoutFile)
		{
			[dvStreamFileName setStringValue:[savePanel filename]];
			[CloseDVStreamFileButton setEnabled:YES];

			fseeko(inoutFile,0,SEEK_END);
			inoutFileSize = ftello(inoutFile);
			inoutFileSizeInFrames = inoutFileSize/gpDVFormatInfo->frameSize;
			timeCodeInFrames = 0;
			AVCTapeTgtSetTimeCode(timeCodeInFrames);
			fseeko(inoutFile,0,SEEK_SET);
			[self updateDVStreamFileSize:inoutFileSize];
		}
		else
		{
			[dvStreamFileName setStringValue:@"Unable to open selected file!"];
			[CloseDVStreamFileButton setEnabled:NO];
		}

		[self inFileMutexUnLock];

	}		
}

//////////////////////////////////////////////////////
// CloseDVStreamFileButtonPushed
//////////////////////////////////////////////////////
- (IBAction) CloseDVStreamFileButtonPushed:(id)sender
{
	[self inFileMutexLock];
	fclose(inoutFile);
	inoutFile = nil;
	inoutFileSize = 0;
	inoutFileSizeInFrames = 0;
	timeCodeInFrames = 0;
	[dvStreamFileName setStringValue:@"No File Selected"];
	[dvStreamFileSize setStringValue:@""];
	[self updateOutputPlugTimecode:[NSString stringWithFormat:@"%02d:%02d:%02d.%02d",0,0,0,0]];
	[CloseDVStreamFileButton setEnabled:NO];
	[self inFileMutexUnLock];
}

//////////////////////////////////////////////////////
// changeOutputChannelStepperPushed
//////////////////////////////////////////////////////
- (IBAction) changeOutputChannelStepperPushed:(id)sender
{
	NSStepper *stepper = (NSStepper*) sender;
	
	NSLog(@"changeOutputChannelStepperPushed Val: %d\n",[stepper intValue]);
	
	if ((avc->transmitStarted == false) && ([outputPlugConnections intValue] == 0))
	{
		xmitter->setTransmitIsochChannel([stepper intValue]);
		[outputPlugChannel setIntValue:[stepper intValue]];
	}
	else
	{
		// Reset stepper value to current channel value
		[stepper setIntValue:[outputPlugChannel intValue]];
	}
}

//////////////////////////////////////////////////////
// changeInputChannelStepperPushed
//////////////////////////////////////////////////////
- (IBAction) changeInputChannelStepperPushed:(id)sender
{
	NSStepper *stepper = (NSStepper*) sender;

	NSLog(@"changeInputChannelStepperPushed Val: %d\n",[stepper intValue]);

	if ((avc->receiveStarted == false) && ([inputPlugConnections intValue] == 0))
	{
		receiver->setReceiveIsochChannel([stepper intValue]);
		[inputPlugChannel setIntValue:[stepper intValue]];
	}
	else
	{
		// Reset stepper value to current channel value
		[stepper setIntValue:[inputPlugChannel intValue]];
	}
}

//////////////////////////////////////////////////////
// updateInputChannelStepperIntVal
//////////////////////////////////////////////////////
- (void) updateInputChannelStepperIntVal: (unsigned int ) chan
{
	[inputChannelStepper setIntValue:chan];
}

//////////////////////////////////////////////////////
// updateOutputChannelStepperIntVal
//////////////////////////////////////////////////////
- (void) updateOutputChannelStepperIntVal: (unsigned int ) chan
{
	[outputChannelStepper setIntValue:chan];
}

//////////////////////////////////////////////////////
// getTransmitterChannel
//////////////////////////////////////////////////////
- (int) getTransmitterChannel
{
	return [outputPlugChannel intValue];
}

//////////////////////////////////////////////////////
// getReceiverChannel
//////////////////////////////////////////////////////
- (int) getReceiverChannel
{
	return [inputPlugChannel intValue];
}

#pragma mark -----------------------------------
#pragma mark AVC Transport Control Handlers
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// avcPlayCmdHandler
//////////////////////////////////////////////////////
- (void) avcPlayCmdHandler
{
	if (inoutFile != nil)
	{	
		fseeko(inoutFile,0,SEEK_CUR);

		// Don't play if file is zero length
		if (inoutFileSize == 0)
		{
			[self addToAVCLog:@"Warning: Attempting to play a zero length file.\n"]; 
			return;
		}
	}
	
	if (xmitter->transportState == kDVTransmitterTransportStopped)
	{
		AVCTapeTgtSetOutputPlugBroadcastConnection(xmitter->getTransmitIsochChannel(), xmitter->getTransmitIsochSpeed());
		xmitter->startTransmit();
	}
	avc->transmitStarted = true;
	[XmitterPlayButton setImage:XmitterPlayButtonBlueImage];
	[XmitterStopButton setImage:XmitterStopButtonNormalImage];
	[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	[XmitterPauseButton setEnabled:YES];
	[XmitterFFwdButton setEnabled:YES];
	[XmitterFRevButton setEnabled:YES];
	[XmitterFrameFwdButton setEnabled:YES];
	[XmitterFrameRevButton setEnabled:YES];
	[outputPlugDCLOverruns setIntValue:0];

	[ReceiverRecButton setEnabled:NO];
}

//////////////////////////////////////////////////////
// avcStopCmdHandler
//////////////////////////////////////////////////////
- (void) avcStopCmdHandler
{
	if (xmitter->transportState == kDVTransmitterTransportPlaying)
	{

		AVCTapeTgtClearOutputPlugBroadcastConnection();
		xmitter->stopTransmit();
	}
	avc->transmitStarted = false;
	[XmitterPlayButton setImage:XmitterPlayButtonNormalImage];
	[XmitterStopButton setImage:XmitterStopButtonBlueImage];
	[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	[XmitterPauseButton setEnabled:NO];
	[XmitterFFwdButton setEnabled:NO];
	[XmitterFRevButton setEnabled:NO];
	[XmitterFrameFwdButton setEnabled:NO];
	[XmitterFrameRevButton setEnabled:NO];

	if (inoutFile != nil)
		fflush(inoutFile);

	[ReceiverRecButton setEnabled:YES];
}

//////////////////////////////////////////////////////
// avcRecordCmdHandler
//////////////////////////////////////////////////////
- (void) avcRecordCmdHandler
{
	if (inoutFile != nil)
		fseeko(inoutFile,0,SEEK_CUR);
	
	[self prepareTSPacketReceiver];
	if (receiver->transportState == kDVReceiverTransportStopped)
		receiver->startReceive();
	avc->receiveStarted = true;
	recordStartTime = [[NSDate date] retain];
	[ReceiverRecButton setImage:ReceiverRecButtonRecordingImage];
	[XmitterStopButton setImage:XmitterStopButtonNormalImage];
	[inputPlugDCLOverruns setIntValue:0];
	
	[XmitterPlayButton setEnabled:NO];
	[XmitterFFwdButton setEnabled:NO];
	[XmitterFRevButton setEnabled:NO];
	[XmitterFrameFwdButton setEnabled:NO];
	[XmitterFrameRevButton setEnabled:NO];
	[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	[XmitterPauseButton setEnabled:YES];
}

//////////////////////////////////////////////////////
// avcRecordStopCmdHandler
//////////////////////////////////////////////////////
- (void) avcRecordStopCmdHandler
{
	if (receiver->transportState == kDVReceiverTransportRecording)
		receiver->stopReceive();
	avc->receiveStarted = false;
	[ReceiverRecButton setImage:ReceiverRecButtonNormalImage];
	[XmitterStopButton setImage:XmitterStopButtonBlueImage];
	
	if (inoutFile != nil)
		fflush(inoutFile);

	[XmitterPlayButton setEnabled:YES];
	[XmitterPauseButton setImage:XmitterPauseButtonNormalImage];
	[XmitterPauseButton setEnabled:NO];
}

#pragma mark -----------------------------------
#pragma mark DV Stream Prep Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// prepareTSPacketReceiver
//////////////////////////////////////////////////////
- (void) prepareTSPacketReceiver
{
	// Nothing to do here anymore
}	

//////////////////////////////////////////////////////
// prepareTSPacketFetcher
//////////////////////////////////////////////////////
- (void) prepareTSPacketFetcher
{
	// Nothing to do here anymore
}

//////////////////////////////////////////////////////
// adjustTimeCodePosition
//////////////////////////////////////////////////////
- (void) adjustTimeCodePosition: (unsigned int) newFrameOffset
{
	if (newFrameOffset > (inoutFileSizeInFrames))
		timeCodeInFrames = (inoutFileSizeInFrames);
	else
		timeCodeInFrames = (UInt32) newFrameOffset;
	fseeko(inoutFile,(UInt64)((UInt64)timeCodeInFrames*(UInt64)gpDVFormatInfo->frameSize),SEEK_SET);

	// If not in timecode extraction mode, set the timecode based on file position
	if ([self currentTimeCodeMode] != kTimeCodeMode_Extraction)
		AVCTapeTgtSetTimeCode(timeCodeInFrames);
}

//////////////////////////////////////////////////////
// adjustTimeCodePosition
//////////////////////////////////////////////////////
- (void) adjustTimeCodePositionToEOF
{
	timeCodeInFrames = (inoutFileSizeInFrames);
	fseeko(inoutFile,(UInt64)((UInt64)timeCodeInFrames*(UInt64)gpDVFormatInfo->frameSize),SEEK_SET);

	// If not in timecode extraction mode, set the timecode based on file position
	if ([self currentTimeCodeMode] != kTimeCodeMode_Extraction)
		AVCTapeTgtSetTimeCode(timeCodeInFrames);
}

#pragma mark -----------------------------------
#pragma mark DV Transmitter UI Update Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// updateOutputPlugConnections
//////////////////////////////////////////////////////
- (void) updateOutputPlugConnections: (unsigned int) count
{
	[outputPlugConnections setIntValue:count];
}

//////////////////////////////////////////////////////
// updateOutputPlugChannel
//////////////////////////////////////////////////////
- (void) updateOutputPlugChannel: (unsigned int) channel
{
	[outputPlugChannel setIntValue:channel];
}

//////////////////////////////////////////////////////
// updateOutputPlugState
//////////////////////////////////////////////////////
- (void) updateOutputPlugState: (NSString*)s
{
    [outputPlugState setStringValue:s];
}

//////////////////////////////////////////////////////
// updateOutputPlugStateExtended
//////////////////////////////////////////////////////
- (void) updateOutputPlugStateExtended: (NSString*)s
{
    [outputPlugStateExtended setStringValue:s];
}

//////////////////////////////////////////////////////
// updateOutputPlugSpeed
//////////////////////////////////////////////////////
- (void) updateOutputPlugSpeed: (NSString*)s
{
    [outputPlugSpeed setStringValue:s];
}

//////////////////////////////////////////////////////
// updateOutputPlugTimecode
//////////////////////////////////////////////////////
- (void) updateOutputPlugTimecode: (NSString*)s
{
    [outputPlugTimecode setStringValue:s];
}

//////////////////////////////////////////////////////
// incrementOutputPlugDCLOverrunCount
//////////////////////////////////////////////////////
- (void) incrementOutputPlugDCLOverrunCount
{
	[outputPlugDCLOverruns setIntValue:([outputPlugDCLOverruns intValue]+1)];
}

#pragma mark -----------------------------------
#pragma mark DV Receiver UI Update Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// updateDVStreamFileSize
//////////////////////////////////////////////////////
- (void) updateDVStreamFileSize: (UInt64) size
{
	UInt32 timeInFrames;
	UInt32 hours;
	UInt32 minutes;
	UInt32 seconds;

	timeInFrames = size / gpDVFormatInfo->frameSize;
	hours = timeInFrames / 108000;
	timeInFrames -= (hours*timeInFrames);
	minutes = timeInFrames / 1800;
	timeInFrames -= (minutes*1800);
	seconds = timeInFrames / 30;
	timeInFrames -= (seconds*30);
	
	[dvStreamFileSize setStringValue:[NSString stringWithFormat:@"%lld (%02d:%02d:%02d.%02d)",size,hours,minutes,seconds,timeInFrames]];
}

//////////////////////////////////////////////////////
// updateInputPlugConnections
//////////////////////////////////////////////////////
- (void) updateInputPlugConnections: (unsigned int) count
{
	[inputPlugConnections setIntValue:count];
}

//////////////////////////////////////////////////////
// updateInputPlugChannel
//////////////////////////////////////////////////////
- (void) updateInputPlugChannel: (unsigned int) channel
{
	[inputPlugChannel setIntValue:channel];
}

//////////////////////////////////////////////////////
// updateInputPlugSpeed
//////////////////////////////////////////////////////
- (void) updateInputPlugSpeed: (NSString*)s
{
    [inputPlugSpeed setStringValue:s];
}

//////////////////////////////////////////////////////
// incrementInputPlugDCLOverrunCount
//////////////////////////////////////////////////////
- (void) incrementInputPlugDCLOverrunCount
{
	[inputPlugDCLOverruns setIntValue:([inputPlugDCLOverruns intValue]+1)];
}

#pragma mark -----------------------------------
#pragma mark Misc UI Update Functions
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// updateAVCTargetObject
//////////////////////////////////////////////////////
- (void) updateAVCTargetObject: (AVCTarget*) avcObject
{
	avc = avcObject;
}

//////////////////////////////////////////////////////
// updateDVTransmitterObject
//////////////////////////////////////////////////////
- (void) updateDVTransmitterObject: (DVTransmitter*) xmitterObject
{
	xmitter = xmitterObject;
}

//////////////////////////////////////////////////////
// updateDVReceiverObject
//////////////////////////////////////////////////////
- (void) updateDVReceiverObject: (DVReceiver*) receiverObject
{
	receiver = receiverObject;
}


#pragma mark -----------------------------------
#pragma mark NSApplication Delagate Functios
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// application:openFile:
//////////////////////////////////////////////////////
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
	return YES;
}

//////////////////////////////////////////////////////
// applicationWillTerminate
//////////////////////////////////////////////////////
- (void)applicationWillTerminate:(NSNotification *)aNotification
{
	// TODO: Now is a good time to destroy DV transmitter/receiver objects
}

//////////////////////////////////////////////////////
// applicationDidFinishLaunching
//////////////////////////////////////////////////////
- (void)applicationDidFinishLaunching:(NSNotification *)aNotification
{
	// Local Vars
	pthread_attr_t avcThreadAttr;
    IOReturn result = kIOReturnSuccess ;
	unsigned int extraPacketCount;
	UInt8 dvMode;

	// Set the global pointer to this object
	gpUserIntf = self;

	// Initialzie some class vars
	AVCThreadReady = false;

	dvMode = [[[NSUserDefaults standardUserDefaults] objectForKey:@"DVMode"] intValue];
	gpDVFormatInfo = &pDVFormatTable[dvMode];
	[avcMode setStringValue:gpDVFormatInfo->pDVModeName];
	
	// Get the values for the transmitter/receiver buffer size sliders in the prefs panel
	transmitterBufferSizeSliderValue = [[[NSUserDefaults standardUserDefaults] objectForKey:@"TransmitterBufferSize"] floatValue];
	receiverBufferSizeSliderValue = [[[NSUserDefaults standardUserDefaults] objectForKey:@"ReceiverBufferSize"] floatValue];

	// Allocate a mutable array for holding availabe transport stream filenames, etc
	availTStreams = [[NSMutableArray alloc] init];

	// Allocate string memory for AVC Log text view
	avcLogString = [[NSMutableString stringWithCapacity:kAVCMessageLogSize] retain];

	// Allocate an array to hold AVC Log pending update strings
	avcLogUpdateStringArray = [[NSMutableArray alloc] init];

	// Set font in AVC Log text view
	[avcLog setFont:[NSFont fontWithName:@"Courier" size:12]];

	// Initialize UI fields
	[self updateOutputPlugConnections:0];
	[self updateOutputPlugChannel:63];
	[self updateOutputPlugTimecode:@"00:00:00:00"];
	[self updateOutputPlugState:@"Stopped"];
	[self updateOutputPlugStateExtended:@""];
	[self updateOutputPlugSpeed:@"100"];
	[outputPlugDCLOverruns setIntValue:0];
	
	[self updateInputPlugConnections:0];
	[self updateInputPlugChannel:63];
	[self updateInputPlugSpeed:@"100"];
	[inputPlugDCLOverruns setIntValue:0];

	// Initialize Channel steppers
	[outputChannelStepper setMinValue:0];
	[outputChannelStepper setMaxValue:63];
	[self updateOutputChannelStepperIntVal:63];
	[outputChannelStepper setValueWraps:YES];
	[outputChannelStepper setAutorepeat:NO];

	[inputChannelStepper setMinValue:0];
	[inputChannelStepper setMaxValue:63];
	[self updateInputChannelStepperIntVal:63];
	[inputChannelStepper setValueWraps:YES];
	[inputChannelStepper setAutorepeat:NO];

	// Initialize the time-code mode combo box
	[timecodeMode selectItemAtIndex:kTimeCodeMode_Insertion];
	
	// Initialize the log acces mutex
    pthread_mutex_init(&logAccessMutex,NULL);

	// Initialize the in-file acces mutex
    pthread_mutex_init(&inFileAccessMutex,NULL);

	[dvStreamFileName setStringValue:@"No File Selected"];
	[CloseDVStreamFileButton setEnabled:NO];
	
	// Add some text to the log
	[self addToAVCLog:@"FireWire DV AV/C Tape Emulator\n"];
	[self addToAVCLog:@"Copyright 2003, Apple Computer, Inc.\n"];
	[self addToAVCLog:@"--------------------------------------------------\n\n"];

	// Create the AVC thread
    pthread_attr_init(&avcThreadAttr);
	pthread_create(&AVCThread, &avcThreadAttr, (void *(*)(void *))AVCThreadStart, (void*) self);
	while (AVCThreadReady != true);	// Wait here for the AVC thread to be ready!

	// Instantiatie the StringLogger object
	stringLogger = new StringLogger(StringLoggerHandler);

	// Calculate number of extra cycles per segment based on pref panel slider val
	extraPacketCount = ((unsigned int)transmitterBufferSizeSliderValue * kMaxExtraTransmitCyclesPerSegment) / 100;

	// Use FireWireDV helper function to instantiate/setup MPEG2Transmitter
	result = CreateDVTransmitter(&xmitter,
		DVFramePullProcHandler,
		nil,
		DVFrameReleaseProcHandler,
		nil,
		TransmitterMessageReceivedProc,
		nil,					  
		stringLogger,
		nil, //gpAVC->nodeNubInterface,
		(kCyclesPerDVTransmitSegment+extraPacketCount),
		kNumDVTransmitSegments,
		gpDVFormatInfo->dvMode,
		8,
		false);

	if (!xmitter)
	{
		// TODO:Handle Error Here!
		[self addToAVCLog:@"Error: Failed to Create DVTransmitter Object\n"];
	}

	dvTransmitterLatencyInFrames = 
		((kCyclesPerDVTransmitSegment+extraPacketCount)*kNumDVTransmitSegments)/gpDVFormatInfo->averageCyclesPerFrame;
	
	numTransmitterFrames = xmitter->getNumFrames();
	xmitter->setTransmitIsochChannel(63);

	if (gpDVFormatInfo->frameSize > 144000)
	{
		xmitter->setTransmitIsochSpeed(kFWSpeed400MBit);
		[self updateOutputPlugSpeed:@"400"];
	}
	
	// Calculate number of extra cycles per segment based on pref panel slider val
	extraPacketCount = ((unsigned int)receiverBufferSizeSliderValue * kMaxExtraReceiveCyclesPerSegment) / 100;
	
	result = CreateDVReceiver(&receiver,
		DVFrameReceivedProcHandler,
		nil,
		ReceiverMessageReceivedProc,
		nil,
		stringLogger,
		nil, //gpAVC->nodeNubInterface,
		(kCyclesPerDVReceiveSegment+extraPacketCount),
		kNumDVReceiveSegments,
		gpDVFormatInfo->dvMode,
		kDVReceiveNumFrames,
		false);

	if (!receiver)
	{
		// TODO:Handle Error Here!
		[self addToAVCLog:@"Error: Failed to Create DVReceiver Object\n"];
	}

	receiver->setReceiveIsochChannel(63);

	if (gpDVFormatInfo->frameSize > 144000)
	{
		receiver->setReceiveIsochSpeed(kFWSpeed400MBit);
		[self updateInputPlugSpeed:@"400"];
	}
	
	// Start a repeating timer to handle log & user-interface updates
	userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:0.5 // 2 times a sec
																					 target:self
																				   selector:@selector(userInterfaceUpdateTimerExpired:)
																				   userInfo:nil repeats:YES];

	// Update the global pointers to the receiver and xmitter objects
	gpXmitter = xmitter;
	gpReceiver = receiver;

	// Set the flag that lets the AVC command handling begin
	startAVCCommandProcessing = true;

	// Publish the FireWire config ROM changes
	gpAVC->publishConfigRom();
}

//////////////////////////////////////////////////////
// windowShouldClose
//////////////////////////////////////////////////////
- (BOOL)windowShouldClose:(id)sender
{
	// Don't let the user close the main window. Only quitting allowed!
	return NO;
}

@end

///////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////
////////////
////////////  The following functions are not part of the AVHDD object!
////////////
///////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////

#pragma mark -
#pragma mark ===================================
#pragma mark Local Function Implementations
#pragma mark ===================================

#pragma mark -----------------------------------
#pragma mark Thread Start Function
#pragma mark -----------------------------------

//////////////////////////////////////////////////////////////////////
//
// AVCThreadStart
//
//////////////////////////////////////////////////////////////////////
void *AVCThreadStart(AVHDD *uiObject)
{
	AVCTarget *avc;
   	IOReturn result = kIOReturnSuccess ;

	// Create an autorelease pool for this thread
	NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];

	// Bump this thread's relative priority
	[NSThread setThreadPriority:0.9];
	
	// Setup the local AVC Unit
	avc = new AVCTarget(uiObject);
	result = avc->setupLocalNodeAVC();
    if (result != kIOReturnSuccess)
    {
		[uiObject addToAVCLog:@"Error in setupLocalNodeAVC\n"];
		[uiObject setAVCThreadReady];
		return NULL;
    }

	// Set the global pointer to the avc object
	gpAVC = avc;

	// Set the UI object's pointer to the avc object
	[uiObject updateAVCTargetObject:avc];
	
	// Alert the UI object that the AVC thread is initialized
	[uiObject setAVCThreadReady];

	while (startAVCCommandProcessing != true);	// Wait here for the UI thread to be give us the go ahead to start!
	
	// Run the run loop
	CFRunLoopRun();

	// Release the autorelease pool
	[pool release];

	return NULL;
}

#pragma mark -----------------------------------
#pragma mark Dv Transmitter/Receiver Callbacks
#pragma mark -----------------------------------

//////////////////////////////////////////////////////
// initialzeTransmitterFrameQueue
//////////////////////////////////////////////////////
void initialzeTransmitterFrameQueue(void)
{
	UInt32 i;
	DVTransmitFrame* pFrame;

	pFrameQueueHead = nil;
	for (i=0;i<numTransmitterFrames;i++)
	{
		pFrame = gpXmitter->getFrame(i);
		pFrame->pNext = pFrameQueueHead;
		pFrameQueueHead = pFrame;
	}
}

//////////////////////////////////////////////////////////////////////
//
// RepositionPlaybackFilePointer
//
//////////////////////////////////////////////////////////////////////
static void RepositionPlaybackFilePointer(UInt8 transport_state)
{
	static UInt32 frameRepeatCount = 0;
	int nextFrameIndex = (int)timeCodeInFrames;
	
	switch (transport_state)
	{
		case kAVCTapePlayNextFrame:
			// Set the state to playpause mode
			AVCTapeTgtSetState(kAVCTapePlayOpcode,kAVCTapePlayFwdPause);
			break;
		case kAVCTapePlaySlowestFwd:
			if (++frameRepeatCount < kPlaySlowestFrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd6:
			if (++frameRepeatCount < kPlaySlow6FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd5:
			if (++frameRepeatCount < kPlaySlow5FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd4:
			if (++frameRepeatCount < kPlaySlow4FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd3:
			if (++frameRepeatCount < kPlaySlow3FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd2:
			if (++frameRepeatCount < kPlaySlow2FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowFwd1:
			if (++frameRepeatCount < kPlaySlow1FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayX1:
		case kAVCTapePlayFwd:
			// This function is only called for 
			// these states if it is eof. Just
			// back up to the last frame
			nextFrameIndex -= 1;
			break;
		case kAVCTapePlayFastFwd1:
			nextFrameIndex += kPlayFastFwd1FrameIncrement;
			break;
		case kAVCTapePlayFastFwd2:
			nextFrameIndex += kPlayFastFwd2FrameIncrement;
			break;
		case kAVCTapePlayFastFwd3:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				// Uncomment the next line, to repeat the frame
				// Comment it out to play seq over the repeat count
				//nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex += kPlayFastFwd3FrameIncrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastFwd4:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				// Uncomment the next line, to repeat the frame
				// Comment it out to play seq over the repeat count
				//nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex += kPlayFastFwd4FrameIncrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastFwd5:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				// Uncomment the next line, to repeat the frame
				// Comment it out to play seq over the repeat count
				//nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex += kPlayFastFwd5FrameIncrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastFwd6:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				// Uncomment the next line, to repeat the frame
				// Comment it out to play seq over the repeat count
				//nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex += kPlayFastFwd6FrameIncrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastestFwd:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				// Uncomment the next line, to repeat the frame
				// Comment it out to play seq over the repeat count
				//nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex += kPlayFastestFwdFrameIncrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayPrevFrame:
			nextFrameIndex -= 2;
			AVCTapeTgtSetState(kAVCTapePlayOpcode,kAVCTapePlayRevPause);
			break;
		case kAVCTapePlaySlowestRev:
			if (++frameRepeatCount < kPlaySlowestFrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev6:
			if (++frameRepeatCount < kPlaySlow6FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev5:
			if (++frameRepeatCount < kPlaySlow5FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev4:
			if (++frameRepeatCount < kPlaySlow4FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev3:
			if (++frameRepeatCount < kPlaySlow3FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev2:
			if (++frameRepeatCount < kPlaySlow2FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlaySlowRev1:
			if (++frameRepeatCount < kPlaySlow1FrameRepeat)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= 2;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayX1Rev:
		case kAVCTapePlayRev:
			nextFrameIndex -= 2;
			break;
		case kAVCTapePlayFastRev1:
			nextFrameIndex -= kPlayFastRev1FrameDecrement;
			break;
		case kAVCTapePlayFastRev2:
			nextFrameIndex -= kPlayFastRev2FrameDecrement;
			break;
		case kAVCTapePlayFastRev3:
			nextFrameIndex -= kPlayFastRev3FrameDecrement;
			break;
		case kAVCTapePlayFastRev4:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= kPlayFastRev4FrameDecrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastRev5:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= kPlayFastRev5FrameDecrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastRev6:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= kPlayFastRev6FrameDecrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayFastestRev:
			if (++frameRepeatCount < kPlayHighSpeedPlayBurstCount)
			{
				nextFrameIndex -= 1;
			}
			else
			{
				nextFrameIndex -= kPlayFastestRevFrameDecrement;
				frameRepeatCount = 0;
			}
			break;
		case kAVCTapePlayRevPause:
			nextFrameIndex -= 1;
			break;
		case kAVCTapePlayFwdPause:
			nextFrameIndex -= 1;
			break;
		default:
			break;
	};
	
	// Adjust for file boundaries if needed
	if (nextFrameIndex > (int)(inoutFileSizeInFrames))
		nextFrameIndex = (int)(inoutFileSizeInFrames);
	if (nextFrameIndex < 0)
		nextFrameIndex = 0;

	// Seek if we need to
	if (nextFrameIndex != (int)timeCodeInFrames)
	{
		fseeko(inoutFile,(UInt64)((UInt64)nextFrameIndex*(UInt64)gpDVFormatInfo->frameSize),SEEK_SET);
		//fseeko(inoutFile,(long long)((long long)(nextFrameIndex-(int)timeCodeInFrames)*(long long)gpDVFormatInfo->frameSize),SEEK_CUR);

		timeCodeInFrames = (UInt32) nextFrameIndex;

		// If not in timecode extraction mode, set the timecode based on file position
		if ([gpUserIntf currentTimeCodeMode] != kTimeCodeMode_Extraction)
			AVCTapeTgtSetTimeCode(timeCodeInFrames);
	}
	
	return;
}

//////////////////////////////////////////////////////////////////////
//
// DVFramePullProcHandler
//
//////////////////////////////////////////////////////////////////////
IOReturn DVFramePullProcHandler(UInt32 *pFrameIndex, void *pRefCon)
{
	unsigned int cnt;
	IOReturn result = 0;
	DVTransmitFrame* pFrame;
	UInt64 lastFramePos;
	UInt8 transport_mode,transport_state;
	unsigned int frameCount; 
	unsigned int hours; 
	unsigned int minutes; 
	unsigned int seconds;
	unsigned int frames;
	Boolean isDropFrame;		
	
	// If we have no file open or the file is empty, don't provide a frame
	if ((inoutFile == nil) || (inoutFileSize < gpDVFormatInfo->frameSize))
		return -1;
	
	if (pFrameQueueHead != nil)
	{
		pFrame = pFrameQueueHead;
		pFrameQueueHead = pFrame->pNext;

		// Get the current play state
		AVCTapeTgtGetState(&transport_mode,&transport_state);

		// If looping mode, we should rewind the file
		if (([gpUserIntf shouldLoopPlaBack] == true) && (feof(inoutFile)))
		{
			rewind(inoutFile);
			timeCodeInFrames = 0;
			if ([gpUserIntf currentTimeCodeMode] != kTimeCodeMode_Extraction)
				AVCTapeTgtSetTimeCode(timeCodeInFrames);
		}
		
		// If we're not in play forward 1x mode (or we are, but we 
		// are at the eof, we need to reposition the file pointer
		if (((transport_state != kAVCTapePlayFwd) && (transport_state != kAVCTapePlayX1)) || (feof(inoutFile)))
			RepositionPlaybackFilePointer(transport_state);
		
		// Read the next TS packet from the input file
		cnt = fread(pFrame->pFrameData,1,pFrame->frameLen,inoutFile);
		if (cnt != pFrame->frameLen)
		{
			// Seek to the start of the last frame in the file
			if ([gpUserIntf shouldLoopPlaBack] == true)
			{
				rewind(inoutFile);
				timeCodeInFrames = 0;
				if ([gpUserIntf currentTimeCodeMode] != kTimeCodeMode_Extraction)
					AVCTapeTgtSetTimeCode(timeCodeInFrames);
			}
			else
			{
				lastFramePos = inoutFileSize - gpDVFormatInfo->frameSize;
				timeCodeInFrames -= 1;
				fseeko(inoutFile,lastFramePos,SEEK_SET);
			}

			// Read again
			cnt = fread(pFrame->pFrameData,1,pFrame->frameLen,inoutFile);
			if (cnt != pFrame->frameLen)
			{
				DVFrameReleaseProcHandler(pFrame->frameIndex, nil);
				[gpUserIntf addToAVCLog:@"DV Transmit: Re-transmitting previous frame due file read error\n"];
				result = -1;	// Causes The previous frame to be used
			}
			else
			{
				*pFrameIndex = pFrame->frameIndex;
				timeCodeInFrames += 1;
				
			}
		}
		else
		{
			*pFrameIndex = pFrame->frameIndex;
			timeCodeInFrames += 1;
		}
	}
	else
	{
		[gpUserIntf addToAVCLog:@"DV Transmit: Re-transmitting previous frame due to no Frame Buffers\n"];
		result = -1;	// Causes The previous frame to be used
	}
	
	if (result == 0)
	{
		switch ([gpUserIntf currentTimeCodeMode])
		{
			case kTimeCodeMode_None:
				// Just set the AVC Timecode based on file position
				AVCTapeTgtSetTimeCode(timeCodeInFrames);
				break;
			
			case kTimeCodeMode_Insertion:
				// Set the AVC Timecode based on file position
				AVCTapeTgtSetTimeCode(timeCodeInFrames);
				
				// Insert file-position based time-code into frame data
				// Subtract out the latency of the transmitter
				frameCount = (timeCodeInFrames < dvTransmitterLatencyInFrames) ? 0 : (timeCodeInFrames - dvTransmitterLatencyInFrames); 
				hours = 0; 
				minutes = 0; 
				seconds = 0; 
				frames = 0; 
				isDropFrame = false;		
				DVInsertTimeCodeIntoFrame(
										  pFrame->pFrameData,
										  gpDVFormatInfo->numDifSequences,
										  gpDVFormatInfo->isPal, 
										  nil, 
										  &frameCount, 
										  &hours, 
										  &minutes, 
										  &seconds, 
										  &frames, 
										  &isDropFrame);		
				break;

			case kTimeCodeMode_Extraction:
				// Extract the timecode from the frame data
				// TODO: No error handling here yet! We should revert to the file-position based timecode if unsuccessful with extraction
				DVExtractTimeCodeFromFrame(
										   pFrame->pFrameData,
										   gpDVFormatInfo->numDifSequences,
										   !(gpDVFormatInfo->isPal), 
										   gpDVFormatInfo->timeBase,
										   nil, 
										   (int*) &frameCount, 
										   (int*) &hours, 
										   (int*) &minutes, 
										   (int*) &seconds, 
										   (int*) &frames, 
										   &isDropFrame);		

				// Set the AVC timecode based on extracted timecode value
				AVCTapeTgtSetTimeCode((frameCount < dvTransmitterLatencyInFrames) ? 0 : (frameCount - dvTransmitterLatencyInFrames));
				break;
			
			default:
				break;
		};
	}
	
	return result;
}

//////////////////////////////////////////////////////////////////////
//
// DVFrameReleaseProcHandler
//
//////////////////////////////////////////////////////////////////////
IOReturn DVFrameReleaseProcHandler(UInt32 frameIndex, void *pRefCon)
{
	DVTransmitFrame* pFrame;
	pFrame = gpXmitter->getFrame(frameIndex);
	pFrame->pNext = pFrameQueueHead;
	pFrameQueueHead = pFrame;
	return kIOReturnSuccess;
}

//////////////////////////////////////////////////////////////////////
//
// DVFrameReceivedProcHandler
//
//////////////////////////////////////////////////////////////////////
IOReturn DVFrameReceivedProcHandler(DVFrameReceiveMessage msg, DVReceiveFrame* pFrame, void *pRefCon)
{

	UInt32 cnt;
	UInt64 curFilePos;
	UInt8 transport_mode,transport_state;
	unsigned int frameCount; 
	unsigned int hours; 
	unsigned int minutes; 
	unsigned int seconds;
	unsigned int frames;
	Boolean isDropFrame;		
	
	switch (msg)
	{
		case kDVFrameReceivedSuccessfully:
			// In record pause mode, we don't do anything with this frame
			AVCTapeTgtGetState(&transport_mode,&transport_state);
			if (transport_state == kAVCTapeRecordRecordPause)
				break;

			// Store the frame in the DV file
			if (inoutFile != nil)
			{
				if ([gpUserIntf isWriteProtect] == true)
				{
					// In write-protect mode just move forward in the file, if possible
					fseeko(inoutFile,pFrame->frameLen,SEEK_CUR);
				}
				else
				{
					cnt = fwrite(pFrame->pFrameData,1,pFrame->frameLen,inoutFile);
					if (cnt != pFrame->frameLen)
					{
						// TODO: Handle this error case
						[gpUserIntf addToAVCLog:@"DV Receive: Error Writing DV output File\n"];
					}
				}
				curFilePos = ftello(inoutFile);
				timeCodeInFrames = (curFilePos / gpDVFormatInfo->frameSize);

				switch ([gpUserIntf currentTimeCodeMode])
				{
					case kTimeCodeMode_None:
					case kTimeCodeMode_Insertion:
						// Just set the AVC Timecode based on file position
						AVCTapeTgtSetTimeCode(timeCodeInFrames);
						break;
						
					case kTimeCodeMode_Extraction:
						// Extract the timecode from the frame data
						// TODO: No error handling here yet! We should revert to the file-position based timecode if unsuccessful with extraction
						DVExtractTimeCodeFromFrame(
												   pFrame->pFrameData,
												   gpDVFormatInfo->numDifSequences,
												   !(gpDVFormatInfo->isPal), 
												   gpDVFormatInfo->timeBase,
												   nil, 
												   (int*) &frameCount, 
												   (int*) &hours, 
												   (int*) &minutes, 
												   (int*) &seconds, 
												   (int*) &frames, 
												   &isDropFrame);		
						
						// Set the AVC timecode based on extracted timecode value
						AVCTapeTgtSetTimeCode(frameCount);
						break;
						
					default:
						break;
				};
				
				if (inoutFileSize < curFilePos)
				{
					inoutFileSize = curFilePos;
					inoutFileSizeInFrames = timeCodeInFrames;
				}
			}
			break;

		case kDVFrameDropped:
			[gpUserIntf addToAVCLog:@"DV Receive: kDVFrameDropped\n"];
			break;
		case kDVFrameCorrupted:
			[gpUserIntf addToAVCLog:@"DV Receive: kDVFrameCorrupted\n"];
			break;
		case kDVFrameWrongMode:
			[gpUserIntf addToAVCLog:@"DV Receive: kDVFrameWrongMode\n"];
			break;
		default:
			[gpUserIntf addToAVCLog:@"DV Receive: Unknown Frame Received Message Type\n"];
			break;
	};

	// Return an error here to "release" the frame back to the DVReceiver object
	return kIOReturnError;	
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
// TransmitterMessageReceivedProc
//
//////////////////////////////////////////////////////////////////////
void TransmitterMessageReceivedProc(UInt32 msg, UInt32 param1, UInt32 param2, void *pRefCon)
{
	switch (msg)
	{
		case kDVTransmitterDCLOverrun:
			[gpUserIntf incrementOutputPlugDCLOverrunCount];
			initialzeTransmitterFrameQueue();
			[gpUserIntf prepareTSPacketFetcher];
			break;

		case kDVTransmitterAllocateIsochPort:
		case kDVTransmitterReleaseIsochPort:
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
		case kDVReceiverDCLOverrun:
		case kDVReceiverReceivedBadPacket:
			[gpUserIntf incrementInputPlugDCLOverrunCount];
			break;

		case kDVReceiverAllocateIsochPort:
		case kDVReceiverReleaseIsochPort:
		default:
			break;
	};
}
