/*
	File:		NaviCreatorController.mm
 
 Synopsis: This is the source for the NaviCreatorController object. 
 
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

#import "NaviCreatorController.h"

// Prototypes
IOReturn MyNaviFileCreatorProgressCallback(UInt32 percentageComplete, void *pRefCon);
static void *NaviFileCreationThreadStart(NaviCreatorThreadParams* pParams);

@implementation NaviCreatorController


//////////////////////////////////////////////////////
// init
//////////////////////////////////////////////////////
- (id) init
{
	self = [super initWithWindowNibName:@"NaviCreator"];

	if (self)
	{
		pCreator = nil;
		[self window];	// Does this really do something?
		[progressIndicator setHidden:YES];
		
		// Start a repeating timer to handle log & user-interface updates
		userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:0.5 // 2 times a sec
																	target:self
																  selector:@selector(userInterfaceUpdateTimerExpired:)
																  userInfo:nil repeats:YES];
	}

	return self;
}

//////////////////////////////////////////////////////
// initWithFileName
//////////////////////////////////////////////////////
- (id) initWithFileName:(NSString*)fileName
{
	self = [super initWithWindowNibName:@"NaviCreator"];
	
	if (self)
	{
		pCreator = nil;
		[self window];	// Does this really do something?
		[progressIndicator setHidden:YES];
		
		// Start a repeating timer to handle log & user-interface updates
		userInterfaceUpdateTimer = [NSTimer scheduledTimerWithTimeInterval:0.5 // 2 times a sec
																	target:self
																  selector:@selector(userInterfaceUpdateTimerExpired:)
																  userInfo:nil repeats:YES];
		
		[self startNaviFileCreationProcessing:fileName];
	}
	
	return self;
}	

//////////////////////////////////////////////////////
// windowShouldClose
//////////////////////////////////////////////////////
- (BOOL) windowShouldClose:(id)sender
{
	if (pCreator)
	{
		// Display message discussing why window didn't close
		NSRunAlertPanel(@"Navi-File Creation In Progress",@"Window cannot be closed while processing!",@"OK",nil,nil );
		return NO;
	}
	
	return YES;
}

//////////////////////////////////////////////////////
// startButtonPushed
//////////////////////////////////////////////////////
- (IBAction) startButtonPushed:(id)sender
{
	int status;
	
	//NSLog(@"startButtonPushed");
	
	[startButton setEnabled:NO];
	
	// Use the open panel to get a file-name from the user.
	NSOpenPanel *openPanel = [NSOpenPanel openPanel];
	[openPanel setAllowsMultipleSelection:NO];
	[openPanel setCanChooseDirectories:NO];
	[openPanel setTitle:@"Select MPEG-2 TS File"];
	status = [openPanel runModalForTypes:NULL];

	if (status != NSOKButton)
	{
		[startButton setEnabled:YES];
	}
	else
	{
		[self startNaviFileCreationProcessing:[openPanel filename]];
	}
}

//////////////////////////////////////////////////////
// setProgressPercentage
//////////////////////////////////////////////////////
- (void) setProgressPercentage:(unsigned int) percentage
{
	//NSLog(@"setProgressPercentage. Percent Complete: %d\n",percentage);

	[progressIndicator setDoubleValue:(percentage*1.0)];
}

//////////////////////////////////////////////////////
// startNaviFileCreationProcessing
//////////////////////////////////////////////////////
- (void) startNaviFileCreationProcessing:(NSString*)fileName
{
	// Create the .tsnavi file
	[progressIndicator setDoubleValue:0.0];
	[progressIndicator setHidden:NO];
	[statusText setStringValue:@"In progress"];
	[progressIndicator startAnimation:self];
	
	pCreator = new NaviFileCreator;
	if (pCreator)
	{
		// Disable the start button
		[startButton setEnabled:NO];
		
		// Register for progress notifications
		pCreator->RegisterProgressNotificationCallback(MyNaviFileCreatorProgressCallback,self);
		
		// Initialize Thread Parameters
		threadParams.creationResult = kIOReturnSuccess;
		threadParams.pCreator = pCreator;
		threadParams.pFileName = new char[strlen([fileName cString])+2]; // Slightly overallocate
		strcpy(threadParams.pFileName,[fileName cString]);
		threadParams.isDone = false;
		
		// Create the thread which will start the .tsnavi file creation process
		pthread_attr_init(&threadAttr);
		pthread_create(&creationThread, &threadAttr, (void *(*)(void *))NaviFileCreationThreadStart, &threadParams);
	}
}

//////////////////////////////////////////////////////
// userInterfaceUpdateTimerExpired
//////////////////////////////////////////////////////
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer
{
	if (pCreator != nil)
	{
		// Update statistics
		[statusText setStringValue:[NSString stringWithFormat:@"In progress (%u%% complete)",pCreator->percentageComplete]];
		[horizontalResolution setStringValue:[NSString stringWithFormat:@"%u",pCreator->horizontalResolution]];
		[verticalResolution setStringValue:[NSString stringWithFormat:@"%u",pCreator->verticalResolution]];
		
		switch (pCreator->frameRate)
		{
			case MPEGFrameRate_23_976:
				[frameRate setStringValue:@"23.976"];
				break;
				
			case MPEGFrameRate_24:
				[frameRate setStringValue:@"24.0"];
				break;
				
			case MPEGFrameRate_25:
				[frameRate setStringValue:@"25.0"];
				break;
				
			case MPEGFrameRate_29_97:
				[frameRate setStringValue:@"29.97"];
				break;
				
			case MPEGFrameRate_30:
				[frameRate setStringValue:@"30.0"];
				break;
				
			case MPEGFrameRate_50:
				[frameRate setStringValue:@"50.0"];
				break;
				
			case MPEGFrameRate_59_94:
				[frameRate setStringValue:@"59.94"];
				break;
				
			case MPEGFrameRate_60:
				[frameRate setStringValue:@"60.0"];
				break;
				
			case MPEGFrameRate_Unknown:
			default:
				[frameRate setStringValue:@"Unknown"];
				break;
		};

		[iFrames setStringValue:[NSString stringWithFormat:@"%u",pCreator->iFrames]];
		[pFrames setStringValue:[NSString stringWithFormat:@"%u",pCreator->pFrames]];
		[bFrames setStringValue:[NSString stringWithFormat:@"%u",pCreator->bFrames]];
		[totalFrames setStringValue:[NSString stringWithFormat:@"%u",
			(pCreator->iFrames+pCreator->pFrames+pCreator->bFrames)]];
		
		if (threadParams.isDone == true)
		{
			[progressIndicator stopAnimation:self];
			[progressIndicator setHidden:YES];
			if (threadParams.creationResult == kIOReturnSuccess)
				[statusText setStringValue:@"Done"];
			else
				[statusText setStringValue:[NSString stringWithFormat:@"Failed (error: 0x%08X)",threadParams.creationResult]];
			delete pCreator;
			pCreator = nil;
			delete threadParams.pFileName;
			[startButton setEnabled:YES];
		}
	}
}	

@end

//////////////////////////////////////////////////////
// MyNaviFileCreatorProgressCallback
//////////////////////////////////////////////////////
IOReturn MyNaviFileCreatorProgressCallback(UInt32 percentageComplete, void *pRefCon)
{
	NaviCreatorController *pController = (NaviCreatorController*) pRefCon;
	
	//NSLog(@"MyNaviFileCreatorProgressCallback. Percent Complete: %d\n",percentageComplete);

	[pController setProgressPercentage:(unsigned int)percentageComplete];
}

//////////////////////////////////////////////////////
// NaviFileCreationThreadStart
//////////////////////////////////////////////////////
static void *NaviFileCreationThreadStart(NaviCreatorThreadParams* pParams)
{
	pParams->creationResult = pParams->pCreator->CreateMPEGNavigationFileForTSFile(pParams->pFileName);
	pParams->isDone = true;
	return nil;
}

