/*
	File:		VirtualDVHSController.mm
 
 Synopsis: This is the source for the VirtualDVHSController object. 
 
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

#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#import "VirtualDVHSController.h"
#import "NaviCreatorController.h"

@implementation VirtualDVHSController

//////////////////////////////////////////////////////
// initialize
//////////////////////////////////////////////////////
+ (void)initialize
{
    NSMutableDictionary *defaultValues = [NSMutableDictionary dictionary];
    [defaultValues setObject:[[NSFileManager defaultManager] currentDirectoryPath] forKey:@"DefaultRecordingDirectory"];
	[[NSUserDefaults standardUserDefaults] registerDefaults:defaultValues];
}

//////////////////////////////////////////////////////
// awakeFromNib
//////////////////////////////////////////////////////
- (void)awakeFromNib
{
	//NSLog(@"awakeFromNib");

	NSBundle *appBundle = [NSBundle mainBundle];
	
	// Initialize class vars
	uiUpdateCounter = 0;

	// Load the images from the resource directory
	PlayButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Normal" ofType: @"tif"]];
	PlayButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PlayButton-Running-Blue" ofType: @"tif"]];
	StopButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Normal" ofType: @"tif"]];
	StopButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"StopButton-Hilighted-Blue" ofType: @"tif"]];
	PauseButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Normal" ofType: @"tif"]];
	PauseButtonBlueImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"PauseButton-Hilighted-Blue" ofType: @"tif"]];
	FFwdButtonNormalImage  = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"FastForwardButton-Normal" ofType: @"tif"]];
	FRevButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"RewindButton-Normal" ofType: @"tif"]];
	RecButtonNormalImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-0N" ofType: @"tiff"]];
	RecButtonRecordingImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"record-1H" ofType: @"tiff"]];
	
	InOffOutOff = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"InOffOutOff" ofType: @"tif"]];
	InOnOutOff = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"InOnOutOff" ofType: @"tif"]];
	InOffOutOn = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"InOffOutOn" ofType: @"tif"]];
	InOnOutOn = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"InOnOutOn" ofType: @"tif"]];
	
	BackgroundImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"background" ofType: @"tif"]];

	numImages[0] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num0" ofType: @"tif"]];
	numImages[1] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num1" ofType: @"tif"]];
	numImages[2] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num2" ofType: @"tif"]];
	numImages[3] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num3" ofType: @"tif"]];
	numImages[4] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num4" ofType: @"tif"]];
	numImages[5] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num5" ofType: @"tif"]];
	numImages[6] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num6" ofType: @"tif"]];
	numImages[7] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num7" ofType: @"tif"]];
	numImages[8] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num8" ofType: @"tif"]];
	numImages[9] = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"num9" ofType: @"tif"]];
	timeBackground = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"timeBackground" ofType: @"tif"]];
	timeColon = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"numColon" ofType: @"tif"]];
		
	WriteProtectOnImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"writeProtectOn" ofType: @"tif"]];
	WriteProtectOffImage = [[NSImage alloc]initWithContentsOfFile:[appBundle pathForResource: @"writeProtectOff" ofType: @"tif"]];
	
	// Initialize the image based views
	[PlayButton setImage:PlayButtonNormalImage];
	[StopButton setImage:StopButtonNormalImage];
	[PauseButton setImage:PauseButtonNormalImage];
	[FwdButton setImage:FFwdButtonNormalImage];
	[RewButton setImage:FRevButtonNormalImage];	
	[RecordButton setImage:RecButtonNormalImage];

	[WriteProtectButton  setImage:WriteProtectOffImage];
	
	[BackgroundImageView setImage:BackgroundImage];
	[InOutView setImage:InOffOutOff];

	[timeBackgroundView setImage:timeBackground];
	[hoursHiView setImage:numImages[0]];
	[hoursLoView setImage:numImages[0]];
	[minutesHiView setImage:numImages[0]];
	[minutesLoView setImage:numImages[0]];
	[secondsHiView setImage:numImages[0]];
	[secondsLoView setImage:numImages[0]];
	[hoursMinutesSeparatorView setImage:timeColon];
	[minutesSecondsSeparatorView setImage:timeColon];
	
	// Initialize the stream position slider position
	[StreamPositionSlider setFloatValue:0.0];
	
	// Hide the current slider position text
	[currentSliderPositionInHMS setHidden:YES];
}	

//////////////////////////////////////////////////////
// userInterfaceUpdateTimerExpired
//////////////////////////////////////////////////////
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	UInt32 hours;
	UInt32 minutes;
	UInt32 seconds;
	UInt32 frames;
	double currentMPEGDataRate;
	UInt32 currentFrame;
	double newPositionValue;
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	UInt32 hoursHi;
	UInt32 hoursLo;
	UInt32 minutesHi;
	UInt32 minutesLo;
	UInt32 secondsHi;
	UInt32 secondsLo;
	UInt32 framesPerHour;
	UInt32 framesPerMinute;
	UInt32 framesPerSecond;
	UInt32 h,m,s,f;
				
	// Account for this iteration
	uiUpdateCounter += 1;
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	// Get all the useful info from the VirtualDVHS engine
	pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
	pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
	pDVHS->getTapeSubunitTimeCodeFrameCountInHMSF(&hours, &minutes, &seconds, &frames);
	pDVHS->getPlugInformation(&inputPlugConnectionCount,
							  &inputPlugChannel,
							  &outputPlugConnectionCount,
							  &outputPlugChannel,
							  &outputPlugSpeed);
	
	// Display the playback file name
	if (pDVHS->getPlaybackFileName() != nil)
		[FileName setStringValue:[NSString stringWithCString:pDVHS->getPlaybackFileName()]];
	else
		[FileName setStringValue:@"none selected"];

	// Set the write-protect state
	if (pDVHS->isRecordInhibited())
	{
		if ([WriteProtectButton image] != WriteProtectOnImage)
			[WriteProtectButton setImage:WriteProtectOnImage];
	}
	else
	{
		if ([WriteProtectButton image] != WriteProtectOffImage)
			[WriteProtectButton setImage:WriteProtectOffImage];
	}

	// Update the "file length in HMS" text field
	if ((numFrames > 0) && (frameRate != MPEGFrameRate_Unknown))
	{
		UInt32 h,m,s,f;

		// convert the number of frames and the frame-rate to a total time in hms
		framesPerSecond = FramesPerSecond(frameRate);
		framesPerMinute = 60*framesPerSecond;
		framesPerHour = 3600*framesPerSecond;
		f = numFrames;
		h = f / framesPerHour;
		f -= (h*framesPerHour);
		m = f / framesPerMinute;
		f -= (m*framesPerMinute);
		s = f / framesPerSecond;
		f -= (s*framesPerSecond);
		[FileLengthInHMS setStringValue:[NSString stringWithFormat:@"%02d:%02d:%02d",h,m,s]];
	}
	else
		[FileLengthInHMS setStringValue:@"00:00:00"];
	
	// Update various UI elements based on the transport mode/state
	if (currentTransportMode == kAVCTapeTportModePlay)
	{
		if (numFrames > 0)
			[StreamPositionSlider setEnabled:YES];
		else
			[StreamPositionSlider setEnabled:NO];
		
		[WriteProtectButton setEnabled:YES];

		if ([StopButton image] != StopButtonNormalImage)
			[StopButton setImage:StopButtonNormalImage];

		if ([PlayButton image] != PlayButtonBlueImage)		
			[PlayButton setImage:PlayButtonBlueImage];

		if ([RecordButton image] != RecButtonNormalImage)
			[RecordButton setImage:RecButtonNormalImage];

		if (currentTransportState == kAVCTapePlayFwdPause)
		{
			if ([PauseButton image] != PauseButtonBlueImage)
				[PauseButton setImage:PauseButtonBlueImage];
		}
		else
		{
			if ([PauseButton image] != PauseButtonNormalImage)
				[PauseButton setImage:PauseButtonNormalImage];
		}
	}
	else if (currentTransportMode == kAVCTapeTportModeRecord)
	{
		[StreamPositionSlider setEnabled:NO];
		[WriteProtectButton setEnabled:NO];
		
		if ([StopButton image] != StopButtonNormalImage)
			[StopButton setImage:StopButtonNormalImage];
		
		if (uiUpdateCounter & 1)
		{
			// Blink the record button
			if ([RecordButton image] == RecButtonRecordingImage)
				[RecordButton setImage:RecButtonNormalImage];
			else
				[RecordButton setImage:RecButtonRecordingImage];
		}
		
		if (currentTransportState == kAVCTapeRecordRecordPause)
		{
			if ([PauseButton image] != PauseButtonBlueImage)
				[PauseButton setImage:PauseButtonBlueImage];

			if ([PlayButton image] != PlayButtonNormalImage)		
				[PlayButton setImage:PlayButtonNormalImage];
		}
		else
		{
			if ([PauseButton image] != PauseButtonNormalImage)
				[PauseButton setImage:PauseButtonNormalImage];

			if ([PlayButton image] != PlayButtonBlueImage)		
				[PlayButton setImage:PlayButtonBlueImage];
		}
	}
	else if (currentTransportMode == kAVCTapeTportModeWind)
	{
		
		if (numFrames > 0)
			[StreamPositionSlider setEnabled:YES];
		else
			[StreamPositionSlider setEnabled:NO];
		
		[WriteProtectButton setEnabled:YES];

		if ([StopButton image] != StopButtonBlueImage)
			[StopButton setImage:StopButtonBlueImage];
		
		if ([PlayButton image] != PlayButtonNormalImage)		
			[PlayButton setImage:PlayButtonNormalImage];
		
		if ([RecordButton image] != RecButtonNormalImage)
			[RecordButton setImage:RecButtonNormalImage];
		

		if ([PauseButton image] != PauseButtonNormalImage)
			[PauseButton setImage:PauseButtonNormalImage];
	}
	
	// Only update the fields in the drawer view if the drawer is open.
	if ([statsDrawer state] == NSDrawerOpenState)
	{
		if (numFrames > 0)
			[NaviAvailable setStringValue:@"Yes"];
		else
			[NaviAvailable setStringValue:@"No"];
		
		// Set the overrun count value
		[Overruns setIntValue:pDVHS->getOverrunCount()];
		
		[PacketCount setIntValue:numTSPackets];
		[FrameCount setIntValue:numFrames];
		[BitRate setIntValue:(unsigned int)currentMPEGDataRate];
		
		[HRes setIntValue:frameHorizontalSize];
		[VRes setIntValue:frameVerticalSize];
		
		switch (frameRate)
		{
			case MPEGFrameRate_23_976:
				[FrameRate setStringValue:@"23.976"];
				break;
			case MPEGFrameRate_24:
				[FrameRate setStringValue:@"24.0"];
				break;
			case MPEGFrameRate_25:
				[FrameRate setStringValue:@"25.0"];
				break;
			case MPEGFrameRate_29_97:
				[FrameRate setStringValue:@"29.97"];
				break;
			case MPEGFrameRate_30:
				[FrameRate setStringValue:@"30.0"];
				break;
			case MPEGFrameRate_50:
				[FrameRate setStringValue:@"50.0"];
				break;
			case MPEGFrameRate_59_94:
				[FrameRate setStringValue:@"59.94"];
				break;
			case MPEGFrameRate_60:
				[FrameRate setStringValue:@"60.0"];
				break;
			case MPEGFrameRate_Unknown:
			default:
				[FrameRate setStringValue:@"unknown"];
				break;
		};
		
		[InputConnections setIntValue:inputPlugConnectionCount];
		[InputChannel setIntValue:inputPlugChannel];
		[OutputConnections setIntValue:outputPlugConnectionCount];
		[OutputChannel setIntValue:outputPlugChannel];
		
		switch (outputPlugSpeed)
		{
			case 0:
				[OutputSpeed setStringValue:@"100"];
				break;
			case 1:
				[OutputSpeed setStringValue:@"200"];
				break;
			case 2:
				[OutputSpeed setStringValue:@"400"];
				break;
			case 3:
				[OutputSpeed setStringValue:@"800"];
				break;
				
			default:
				[OutputSpeed setStringValue:@"0"];
				break;
		};
	}
	
	// Set the state of the InOut connections graphic
	if ((inputPlugConnectionCount == 0) && (outputPlugConnectionCount == 0))
	{
		if ([InOutView image] != InOffOutOff)
			[InOutView setImage:InOffOutOff];
	}
	else if ((inputPlugConnectionCount > 0) && (outputPlugConnectionCount == 0))
	{
		if ([InOutView image] != InOnOutOff)
			[InOutView setImage:InOnOutOff];
	}
	else if ((inputPlugConnectionCount == 0) && (outputPlugConnectionCount > 0))
	{
		if ([InOutView image] != InOffOutOn)
			[InOutView setImage:InOffOutOn];
	}
	else
	{
		if ([InOutView image] != InOnOutOn)
			[InOutView setImage:InOnOutOn];
	}
	
	// Update the time counter graphics
	hoursHi = hours/10;
	hoursLo = hours%10;
	minutesHi = minutes/10;
	minutesLo = minutes%10;
	secondsHi = seconds/10;
	secondsLo = seconds%10;
	if ([secondsHiView image] != numImages[secondsHi])
		[secondsHiView setImage:numImages[secondsHi]];
	if ([secondsLoView image] != numImages[secondsLo])
		[secondsLoView setImage:numImages[secondsLo]];
	if ([minutesHiView image] != numImages[minutesHi])
		[minutesHiView setImage:numImages[minutesHi]];
	if ([minutesLoView image] != numImages[minutesLo])
		[minutesLoView setImage:numImages[minutesLo]];
	if ([hoursHiView image] != numImages[hoursHi])
		[hoursHiView setImage:numImages[hoursHi]];
	if ([hoursLoView image] != numImages[hoursLo])
		[hoursLoView setImage:numImages[hoursLo]];

	// Blink the colons in the time counter field
	if ((uiUpdateCounter%4) == 0)
	{
		if ([hoursMinutesSeparatorView image] == nil)
			[hoursMinutesSeparatorView setImage:timeColon];
		else
			[hoursMinutesSeparatorView setImage:nil];
		
		if ([minutesSecondsSeparatorView image] == nil)
			[minutesSecondsSeparatorView setImage:timeColon];
		else
			[minutesSecondsSeparatorView setImage:nil];
	}
	
	// Update the slider position, unless we're in playback and we have a pending reposition
	if (pDVHS->isRepositionPending() == false)
	{
		if (numFrames > 0)
		{
			currentFrame = pDVHS->getTapeSubunitTimeCodeFrameCount();
			newPositionValue = (100.0*(double)((double)(currentFrame)/(double)(numFrames)));
			[StreamPositionSlider setFloatValue:newPositionValue];
		}
		else
		{
			[StreamPositionSlider setFloatValue:0.0];
		}
		[currentSliderPositionInHMS setHidden:YES];
	}
}

//////////////////////////////////////////////////////
// LoadFileButtonPushed
//////////////////////////////////////////////////////
- (IBAction) LoadFileButtonPushed:(id)sender
{
	int status;
	NSOpenPanel *openPanel = [NSOpenPanel openPanel];

	//NSLog(@"LoadFileButtonPushed\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	[openPanel setAllowsMultipleSelection:NO];
	[openPanel setCanChooseDirectories:NO];
	[openPanel setTitle:@"Select MPEG Transport-Stream File"];
	status = [openPanel runModalForTypes:NULL];
	if (status == NSOKButton)
	{
		pDVHS->setPlaybackFileName((char*)[[openPanel filename] cString]);
		if (pDVHS->isNaviFileEnabled() == false)
			[self alertNoNaviFile:[openPanel filename]];
	}
}

//////////////////////////////////////////////////////
// StopButtonPushed
//////////////////////////////////////////////////////
- (IBAction) StopButtonPushed:(id)sender
{
	//NSLog(@"StopButtonPushed\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->tapeTransportStateChange(kAVCTapeTportModeWind, kAVCTapeWindStop);
}

//////////////////////////////////////////////////////
// PlayButtonPushed
//////////////////////////////////////////////////////
- (IBAction) PlayButtonPushed:(id)sender
{
	//NSLog(@"PlayButtonPushed\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->tapeTransportStateChange(kAVCTapeTportModePlay, kAVCTapePlayFwd);
}

//////////////////////////////////////////////////////
// PauseButtonPushed
//////////////////////////////////////////////////////
- (IBAction) PauseButtonPushed:(id)sender
{
	// Locals
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	
	//NSLog(@"PauseButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
	if (currentTransportMode == kAVCTapeTportModePlay)
	{
		if (currentTransportState == kAVCTapePlayFwd)
			pDVHS->tapeTransportStateChange(kAVCTapeTportModePlay, kAVCTapePlayFwdPause);
		else
			pDVHS->tapeTransportStateChange(kAVCTapeTportModePlay, kAVCTapePlayFwd);
	}
	else if (currentTransportMode == kAVCTapeTportModeRecord)
	{
		if (currentTransportState == kAVCTapeRecRecord)
			pDVHS->tapeTransportStateChange(kAVCTapeTportModeRecord, kAVCTapeRecordRecordPause);
		else
			pDVHS->tapeTransportStateChange(kAVCTapeTportModeRecord, kAVCTapeRecRecord);
	}
}

//////////////////////////////////////////////////////
// RecordButtonPushed
//////////////////////////////////////////////////////
- (IBAction) RecordButtonPushed:(id)sender
{
	//NSLog(@"RecordButtonPushed\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->tapeTransportStateChange(kAVCTapeTportModeRecord, kAVCTapeRecRecord);
}

//////////////////////////////////////////////////////
// RewButtonPushed
//////////////////////////////////////////////////////
- (IBAction) RewButtonPushed:(id)sender
{
	// Locals
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	
	//NSLog(@"RewButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
	if (currentTransportMode == kAVCTapeTportModePlay)
	{
		pDVHS->tapeTransportStateChange(kAVCTapeTportModePlay, kAVCTapePlayFastRev1);
	}
}

//////////////////////////////////////////////////////
// FwdButtonPushed
//////////////////////////////////////////////////////
- (IBAction) FwdButtonPushed:(id)sender
{
	// Locals
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	
	//NSLog(@"FwdButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
	if (currentTransportMode == kAVCTapeTportModePlay)
	{
		pDVHS->tapeTransportStateChange(kAVCTapeTportModePlay, kAVCTapePlayFastFwd1);
	}
}

//////////////////////////////////////////////////////
// SetRecordDirectoryButtonPushed
//////////////////////////////////////////////////////
- (IBAction) SetRecordDirectoryButtonPushed:(id)sender
{
	int status;
	NSOpenPanel *openPanel = [NSOpenPanel openPanel];
	
	//NSLog(@"SetRecordDirectoryButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	[openPanel setAllowsMultipleSelection:NO];
	[openPanel setCanChooseDirectories:YES];
	[openPanel setCanChooseFiles:NO];
	[openPanel setTitle:@"Select directory for new recordings"];
	status = [openPanel runModalForTypes:NULL];
	if (status == NSOKButton)
	{
		pDVHS->setRecordFileDirectoryPath((char*)[[openPanel filename] cString]);

		// Update the user preferences for target record directory
		[[NSUserDefaults standardUserDefaults] setObject: [openPanel filename]  forKey:@"DefaultRecordingDirectory"];
	}
}

//////////////////////////////////////////////////////
// CreateNaviFileButtonPushed
//////////////////////////////////////////////////////
- (IBAction) CreateNaviFileButtonPushed:(id)sender
{
	//NSLog(@"CreateNaviFileButtonPushed\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	NaviCreatorController *pNaviController = [[NaviCreatorController alloc] init];
	[pNaviController showWindow:self];
}

//////////////////////////////////////////////////////
// statsDrawerButtonPushed
//////////////////////////////////////////////////////
- (IBAction) statsDrawerButtonPushed:(id)sender
{
	//NSLog(@"statsDrawerButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;
	
	if (([statsDrawer state] == NSDrawerOpeningState) || ([statsDrawer state] == NSDrawerOpenState))
		[statsDrawer close];
	else
		[statsDrawer openOnEdge:NSMinYEdge];
}

//////////////////////////////////////////////////////
// RecordInhibitButtonPushed
//////////////////////////////////////////////////////
- (IBAction) RecordInhibitButtonPushed:(id)sender
{
	//NSLog(@"RecordInhibitButtonPushed\n");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;

	if (pDVHS->isRecordInhibited())
	{
		pDVHS->setRecordInhibit(false);

		if ([WriteProtectButton image] != WriteProtectOffImage)
			[WriteProtectButton setImage:WriteProtectOffImage];
	}
	else
	{
		pDVHS->setRecordInhibit(true);

		if ([WriteProtectButton image] != WriteProtectOnImage)
			[WriteProtectButton setImage:WriteProtectOnImage];
	}
}

//////////////////////////////////////////////////////
// StreamPositionSliderModified
//////////////////////////////////////////////////////
- (IBAction) StreamPositionSliderModified:(id)sender
{
	// Locals
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	UInt32 targetFrame;
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	UInt32 framesPerHour;
	UInt32 framesPerMinute;
	UInt32 framesPerSecond;
	UInt32 h,m,s,f;
	NSRect curPosHMSRect;
	NSRect sliderRect;
	float sliderWidth;
	float curPosHMSWidth;
	float curStreamPosSlider;
	float newPosX;
	
	//(@"StreamPositionSliderModified\n");

	// Make sure the VirtualMPEGTapePlayerRecorder exists! 
	if (!pDVHS)
		return;

	pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
	if ((currentTransportMode == kAVCTapeTportModePlay) || (currentTransportMode == kAVCTapeTportModeWind))
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);

		targetFrame = (UInt32)(([StreamPositionSlider floatValue]/100.0) * numFrames);
		pDVHS->repositionPlayer(targetFrame);

		[currentSliderPositionInHMS setHidden:YES];
		
		curPosHMSRect = [currentSliderPositionInHMS frame];
		sliderRect = [StreamPositionSlider frame];
		sliderWidth = sliderRect.size.width;
		curPosHMSWidth = curPosHMSRect.size.width;
		curStreamPosSlider = ([StreamPositionSlider floatValue] / 100.0);
		newPosX = ((sliderRect.origin.x) + (sliderWidth*curStreamPosSlider))  - (curPosHMSWidth/2.0);
	
		if (newPosX < sliderRect.origin.x)
			curPosHMSRect.origin.x = sliderRect.origin.x;
		else if ((newPosX+curPosHMSWidth) > (sliderRect.origin.x+sliderWidth))
			curPosHMSRect.origin.x = (sliderRect.origin.x + sliderWidth - curPosHMSWidth);
		else
			curPosHMSRect.origin.x = newPosX;

		[currentSliderPositionInHMS setFrame:curPosHMSRect];
		
		framesPerSecond = FramesPerSecond(frameRate);
		framesPerMinute = 60*framesPerSecond;
		framesPerHour = 3600*framesPerSecond;
		f = (UInt32)(numFrames * curStreamPosSlider);
		h = f / framesPerHour;
		f -= (h*framesPerHour);
		m = f / framesPerMinute;
		f -= (m*framesPerMinute);
		s = f / framesPerSecond;
		f -= (s*framesPerSecond);
		[currentSliderPositionInHMS setStringValue:[NSString stringWithFormat:@"%02d:%02d:%02d",h,m,s]];
		
		[currentSliderPositionInHMS setNeedsDisplay:YES];
		[currentSliderPositionInHMS setHidden:NO];
	}
}

//////////////////////////////////////////////////////
// NewPlayerBroadcastIsochChannel
//////////////////////////////////////////////////////
- (IBAction) NewPlayerBroadcastIsochChannel:(id)sender
{
	//NSLog(@"NewPlayerBroadcastIsochChannel: %d",[[[DefaultPlaybackChannel selectedItem] title] intValue]);
	pDVHS->setTransmitterBroadcastIsochChannel([[[DefaultPlaybackChannel selectedItem] title] intValue]);
}

//////////////////////////////////////////////////////
// NewRecorderBroadcastIsochChannel
//////////////////////////////////////////////////////
- (IBAction) NewRecorderBroadcastIsochChannel:(id)sender
{
	//NSLog(@"NewRecorderBroadcastIsochChannel: %d",[[[DefaultRecordChannel selectedItem] title] intValue]);
	pDVHS->setReceiverBroadcastIsochChannel([[[DefaultRecordChannel selectedItem] title] intValue]);
}

//////////////////////////////////////////////////////
// alertNoNaviFile
//////////////////////////////////////////////////////
- (void) alertNoNaviFile:(NSString*)fileName
{
	int result =
		NSRunAlertPanel(@"Warning, No Navigation Data-File Detected",@"Timecode and random-access playback will be disabled. Would you like start the NaviFileCreator to process this file?",@"Create Navi Data",@"Continue without Navi",nil);

	if (result == NSAlertDefaultReturn)
	{
		NaviCreatorController *pNaviController = [[NaviCreatorController alloc] initWithFileName:fileName];
		[pNaviController showWindow:self];
	}
}

//////////////////////////////////////////////////////
// drawerWillResizeContents
//////////////////////////////////////////////////////
- (NSSize)drawerWillResizeContents:(NSDrawer *)sender toSize:(NSSize)contentSize;
{
	return [statsDrawer contentSize];
}

//////////////////////////////////////////////////////
// drawerShouldClose
//////////////////////////////////////////////////////
- (BOOL)drawerShouldClose:(NSDrawer *)sender
{
	return false;
}

//////////////////////////////////////////////////////
// application:openFile:
//////////////////////////////////////////////////////
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
	// TODO

	//NSLog(@"application:openFile");
	
	// Make sure the VirtualMPEGTapePlayerRecorder exists first! 
	if (pDVHS)
	{
		pDVHS->setPlaybackFileName((char*)[filename cString]);
		if (pDVHS->isNaviFileEnabled() == false)
			[self alertNoNaviFile:filename];
	}
	return YES;
}

//////////////////////////////////////////////////////
// applicationWillTerminate
//////////////////////////////////////////////////////
- (void)applicationWillTerminate:(NSNotification *)aNotification
{

}

//////////////////////////////////////////////////////
// applicationWillFinishLaunching
//////////////////////////////////////////////////////
- (void)applicationWillFinishLaunching:(NSNotification *)aNotification
{
	//NSLog(@"applicationWillFinishLaunching");

	// Create the VirtualMPEGTapePlayerRecorder
	pDVHS = new VirtualMPEGTapePlayerRecorder;
	if (!pDVHS)
	{
		NSRunAlertPanel(@"VirtualDVHS Error",@"Error creating VirtualMPEGTapePlayerRecorder. Program will exit!",@"OK",nil,nil);
		exit(-1);
	}
	else
	{
		// Initialize the VirtualMPEGTapePlayerRecorder
		printf("VirtualDVHS: Initializing VirtualMPEGTapePlayerRecorder\n");
		if (pDVHS->initWithFileName(nil,nil) != kIOReturnSuccess)
		{
			NSRunAlertPanel(@"VirtualDVHS Error",@"Error initializing VirtualMPEGTapePlayerRecorder. Program will exit!",@"OK",nil,nil);
			delete pDVHS;
			pDVHS = nil;
			exit(-1);
		}
		else
		{
			// Enable looping
			pDVHS->setLoopModeState(true);
		}
	}
	
	// Retrieve the default recording directory from the preferences
	pDVHS->setRecordFileDirectoryPath((char*)[[[NSUserDefaults standardUserDefaults] objectForKey:@"DefaultRecordingDirectory"] cString]);
	
	// Start a repeating timer to handle log & user-interface updates
	userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:0.25 target:self selector:@selector(userInterfaceUpdateTimerExpired:) userInfo:nil repeats:YES];
}

//////////////////////////////////////////////////////
// applicationDidFinishLaunching
//////////////////////////////////////////////////////
- (void)applicationDidFinishLaunching:(NSNotification *)aNotification
{

}

//////////////////////////////////////////////////////
// windowShouldClose
//////////////////////////////////////////////////////
- (BOOL)windowShouldClose:(id)sender
{
	// Don't let the user close the main window. Only quitting allowed!
	return NO;
}

#pragma mark -
#pragma mark ======================================
#pragma mark Apple Script Attributes and Commands
#pragma mark ======================================

//////////////////////////////////////////////////////
// application:delegateHandlesKey
//////////////////////////////////////////////////////
- (BOOL)application:(NSApplication *)sender delegateHandlesKey:(NSString  *)key 
{     
    if ([key isEqual:@"currentfile"])         
        return YES;        
    else if ([key isEqual:@"timecode"])         
        return YES;        
    else if ([key isEqual:@"transportstate"])         
        return YES;        
    else if ([key isEqual:@"hrez"])         
        return YES;        
    else if ([key isEqual:@"vrez"])         
        return YES;        
    else if ([key isEqual:@"bitrate"])         
        return YES;        
    else if ([key isEqual:@"framerate"])         
        return YES;        
    else if ([key isEqual:@"hasnavi"])         
        return YES;        
    else if ([key isEqual:@"numframes"])         
        return YES;        
    else if ([key isEqual:@"inconnections"])         
        return YES;        
    else if ([key isEqual:@"outconnections"])         
        return YES;        
    else if ([key isEqual:@"inchannel"])         
        return YES;        
    else if ([key isEqual:@"outchannel"])         
        return YES;        
    else if ([key isEqual:@"outspeed"])         
        return YES;        
    else if ([key isEqual:@"overruns"])         
        return YES;        
    else if ([key isEqual:@"inbroadcastchannel"])         
        return YES;        
    else if ([key isEqual:@"outbroadcastchannel"])         
        return YES;        
	else
		return NO; 
} 

//////////////////////////////////////////////////////
// currentfile
//////////////////////////////////////////////////////
- (NSString *)currentfile 
{     
	if (pDVHS)
		if (pDVHS->getPlaybackFileName())
			return [NSString stringWithCString:pDVHS->getPlaybackFileName()];
		else
			return @"No File Selected";
	else
		return @" ";
}

//////////////////////////////////////////////////////
// setCurrentfile
//////////////////////////////////////////////////////
- (void)setCurrentfile:(NSString *)s 
{     
	// Make sure the VirtualMPEGTapePlayerRecorder exists first! 
	if (pDVHS)
	{
		pDVHS->setPlaybackFileName((char*)[s cString]);

		// TODO: What do we do if there's no navi file here?
		//if (pDVHS->isNaviFileEnabled() == false)
		//	[self alertNoNaviFile:filename];
	}
} 

//////////////////////////////////////////////////////
// timecode
//////////////////////////////////////////////////////
- (NSString *)timecode 
{     
	UInt32 hours = 0;
	UInt32 minutes = 0;
	UInt32 seconds = 0;
	UInt32 frames = 0;
	
	if (pDVHS)
		pDVHS->getTapeSubunitTimeCodeFrameCountInHMSF(&hours, &minutes, &seconds, &frames);

	return [NSString stringWithFormat:@"%02u:%02u:%02u",hours,minutes,seconds];
}

//////////////////////////////////////////////////////
// transportstate
//////////////////////////////////////////////////////
- (NSString *)transportstate 
{     	
	UInt8 currentTransportMode;
	UInt8 currentTransportState;
	bool isStable;
	
	if (pDVHS)
	{
		pDVHS->getTransportState(&currentTransportMode, &currentTransportState, &isStable);
		if (currentTransportMode == kAVCTapeTportModePlay)
		{
			if (currentTransportState == kAVCTapePlayFwdPause)
				return @"Play-Pause";
			else
				return @"Play";
		}
		else if (currentTransportMode == kAVCTapeTportModeRecord)
		{		
			if (currentTransportState == kAVCTapeRecordRecordPause)
				return @"Record-Pause";
			else
				return @"Record";
		}
		else if (currentTransportMode == kAVCTapeTportModeWind)
			return @"Stop";
		else
			return @"Invalid";
	}
	else	
		return @"Invalid";
}

//////////////////////////////////////////////////////
// hrez
//////////////////////////////////////////////////////
- (NSNumber *)hrez 
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	if (pDVHS)
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
		return [NSNumber numberWithUnsignedInt:frameHorizontalSize];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// vrez
//////////////////////////////////////////////////////
- (NSNumber *)vrez 
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	if (pDVHS)
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
		return [NSNumber numberWithUnsignedInt:frameVerticalSize];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// bitrate
//////////////////////////////////////////////////////
- (NSNumber *)bitrate 
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	if (pDVHS)
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
		return [NSNumber numberWithDouble:currentMPEGDataRate];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// framerate
//////////////////////////////////////////////////////
- (NSNumber *)framerate 
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	if (pDVHS)
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
		switch (frameRate)
		{
			case MPEGFrameRate_23_976:
				return [NSNumber numberWithDouble:23.976];
				break;
			case MPEGFrameRate_24:
				return [NSNumber numberWithDouble:24.0];
				break;
			case MPEGFrameRate_25:
				return [NSNumber numberWithDouble:25.0];
				break;
			case MPEGFrameRate_29_97:
				return [NSNumber numberWithDouble:29.97];
				break;
			case MPEGFrameRate_30:
				return [NSNumber numberWithDouble:30.0];
				break;
			case MPEGFrameRate_50:
				return [NSNumber numberWithDouble:50.0];
				break;
			case MPEGFrameRate_59_94:
				return [NSNumber numberWithDouble:59.94];
				break;
			case MPEGFrameRate_60:
				return [NSNumber numberWithDouble:60.0];
				break;
			case MPEGFrameRate_Unknown:
			default:
				return [NSNumber numberWithDouble:0.0];
				break;
		};
	}
	else
		return [NSNumber numberWithDouble:0.0];
}	

//////////////////////////////////////////////////////
// hasnavi
//////////////////////////////////////////////////////
- (NSString *)hasnavi 
{
	if (pDVHS)
	{
		if (pDVHS->isNaviFileEnabled() == false)
			return @"No";
		else
			return @"Yes";
	}
	else
		return @"Unknown";
}	

//////////////////////////////////////////////////////
// numframes
//////////////////////////////////////////////////////
- (NSNumber *)numframes 
{
	UInt32 frameHorizontalSize;
	UInt32 frameVerticalSize;
	UInt32 bitRate;
	MPEGFrameRate frameRate;
	UInt32 numFrames;
	UInt32 numTSPackets;
	double currentMPEGDataRate;
	
	if (pDVHS)
	{
		pDVHS->getStreamInformation(&frameHorizontalSize,&frameVerticalSize,&bitRate,&frameRate,&numFrames,&numTSPackets,&currentMPEGDataRate);
		return [NSNumber numberWithUnsignedInt:numFrames];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// inconnections
//////////////////////////////////////////////////////
- (NSNumber *)inconnections 
{
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	
	if (pDVHS)
	{
		pDVHS->getPlugInformation(&inputPlugConnectionCount,
								  &inputPlugChannel,
								  &outputPlugConnectionCount,
								  &outputPlugChannel,
								  &outputPlugSpeed);
		return [NSNumber numberWithUnsignedInt:inputPlugConnectionCount];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// outconnections
//////////////////////////////////////////////////////
- (NSNumber *)outconnections 
{
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	
	if (pDVHS)
	{
		pDVHS->getPlugInformation(&inputPlugConnectionCount,
								  &inputPlugChannel,
								  &outputPlugConnectionCount,
								  &outputPlugChannel,
								  &outputPlugSpeed);
		return [NSNumber numberWithUnsignedInt:outputPlugConnectionCount];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// inchannel
//////////////////////////////////////////////////////
- (NSNumber *)inchannel 
{
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	
	if (pDVHS)
	{
		pDVHS->getPlugInformation(&inputPlugConnectionCount,
								  &inputPlugChannel,
								  &outputPlugConnectionCount,
								  &outputPlugChannel,
								  &outputPlugSpeed);
		return [NSNumber numberWithUnsignedInt:inputPlugChannel];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// outchannel
//////////////////////////////////////////////////////
- (NSNumber *)outchannel 
{
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	
	if (pDVHS)
	{
		pDVHS->getPlugInformation(&inputPlugConnectionCount,
								  &inputPlugChannel,
								  &outputPlugConnectionCount,
								  &outputPlugChannel,
								  &outputPlugSpeed);
		return [NSNumber numberWithUnsignedInt:outputPlugChannel];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// outspeed
//////////////////////////////////////////////////////
- (NSNumber *)outspeed 
{
	UInt32 inputPlugConnectionCount;
	UInt32 inputPlugChannel;
	UInt32 outputPlugConnectionCount;
	UInt32 outputPlugChannel;
	UInt32 outputPlugSpeed;
	
	if (pDVHS)
	{
		pDVHS->getPlugInformation(&inputPlugConnectionCount,
								  &inputPlugChannel,
								  &outputPlugConnectionCount,
								  &outputPlugChannel,
								  &outputPlugSpeed);
		if (outputPlugSpeed == 0)
			return [NSNumber numberWithUnsignedInt:100];
		else if (outputPlugSpeed == 1)
			return [NSNumber numberWithUnsignedInt:200];
		else if (outputPlugSpeed == 2)
			return [NSNumber numberWithUnsignedInt:400];
		else
			return [NSNumber numberWithUnsignedInt:0];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// overruns
//////////////////////////////////////////////////////
- (NSNumber *)overruns 
{
	if (pDVHS)
	{
		return [NSNumber numberWithUnsignedInt:pDVHS->getOverrunCount()];
	}
	else
		return [NSNumber numberWithUnsignedInt:0];
}	

//////////////////////////////////////////////////////
// inbroadcastchannel
//////////////////////////////////////////////////////
- (NSNumber *)inbroadcastchannel 
{
	return [NSNumber numberWithUnsignedInt:[[[DefaultRecordChannel selectedItem] title] intValue]];
}	

//////////////////////////////////////////////////////
// outbroadcastchannel
//////////////////////////////////////////////////////
- (NSNumber *)outbroadcastchannel 
{
	return [NSNumber numberWithUnsignedInt:[[[DefaultPlaybackChannel selectedItem] title] intValue]];
}	

//////////////////////////////////////////////////////
// setInbroadcastchannel
//////////////////////////////////////////////////////
- (void) setInbroadcastchannel: (NSNumber*)n 
{
	if (pDVHS)
	{
		pDVHS->setReceiverBroadcastIsochChannel([n intValue] & 0x3F);
		[DefaultRecordChannel selectItemAtIndex:([n intValue] & 0x3F)];
	}
}	

//////////////////////////////////////////////////////
// setOutbroadcastchannel
//////////////////////////////////////////////////////
- (void) setOutbroadcastchannel: (NSNumber*)n 
{
	if (pDVHS)
	{
		pDVHS->setTransmitterBroadcastIsochChannel([n intValue] & 0x3F);
		[DefaultPlaybackChannel selectItemAtIndex:([n intValue] & 0x3F)];
	}
}	

@end
