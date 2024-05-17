/*
	File:		VirtualDVHSController.h
 
 Synopsis: This is the header for the VirtualDVHSController object. 
 
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

#import <Cocoa/Cocoa.h>

@interface VirtualDVHSController : NSObject {

	// The status drawer
	IBOutlet NSDrawer *statsDrawer;
	
	// The position slider
	IBOutlet NSSlider *StreamPositionSlider;
	
	// Lots of text fields
    IBOutlet NSTextField *FileName;
    IBOutlet NSTextField *NaviAvailable;
    IBOutlet NSTextField *PacketCount;
    IBOutlet NSTextField *BitRate;
    IBOutlet NSTextField *FrameCount;
    IBOutlet NSTextField *Overruns;
    IBOutlet NSTextField *HRes;
    IBOutlet NSTextField *VRes;
    IBOutlet NSTextField *FrameRate;
    IBOutlet NSTextField *InputConnections;
    IBOutlet NSTextField *InputChannel;
    IBOutlet NSTextField *OutputConnections;
    IBOutlet NSTextField *OutputChannel;
    IBOutlet NSTextField *OutputSpeed;
    IBOutlet NSTextField *FileLengthInHMS;
    IBOutlet NSTextField *currentSliderPositionInHMS;
	
	// Buttons
	IBOutlet NSButton *LoadFileButton;
	IBOutlet NSButton *StopButton;
	IBOutlet NSButton *PlayButton;
	IBOutlet NSButton *PauseButton;
	IBOutlet NSButton *RecordButton;
	IBOutlet NSButton *RewButton;
	IBOutlet NSButton *FwdButton;
	IBOutlet NSButton *statsDrawerButton;
	IBOutlet NSButton *WriteProtectButton;
	IBOutlet NSButton *SetRecordDirectoryButton;
	IBOutlet NSButton *CreateNaviFileButton;

	IBOutlet NSPopUpButton *DefaultPlaybackChannel;
	IBOutlet NSPopUpButton *DefaultRecordChannel;
	
	// Images 
	NSImage *PlayButtonNormalImage;
	NSImage *PlayButtonBlueImage;
	NSImage *StopButtonNormalImage;
	NSImage *StopButtonBlueImage;
	NSImage *PauseButtonNormalImage;
	NSImage *PauseButtonBlueImage;
	NSImage *FFwdButtonNormalImage;
	NSImage *FRevButtonNormalImage;
	NSImage *RecButtonNormalImage;
	NSImage *RecButtonRecordingImage;
	NSImage *WriteProtectOnImage;
	NSImage *WriteProtectOffImage;
	NSImage *InOffOutOff;
	NSImage *InOnOutOff;
	NSImage *InOffOutOn;
	NSImage *InOnOutOn;
	NSImage *numImages[10];
	NSImage *timeBackground;
	NSImage *timeColon;
	NSImage *BackgroundImage;

	// Image views
	IBOutlet NSImageView *InOutView;
	IBOutlet NSImageView *timeBackgroundView;
	IBOutlet NSImageView *hoursHiView;
	IBOutlet NSImageView *hoursLoView;
	IBOutlet NSImageView *minutesHiView;
	IBOutlet NSImageView *minutesLoView;
	IBOutlet NSImageView *secondsHiView;
	IBOutlet NSImageView *secondsLoView;
	IBOutlet NSImageView *hoursMinutesSeparatorView;
	IBOutlet NSImageView *minutesSecondsSeparatorView;
	IBOutlet NSImageView *BackgroundImageView;
	
	// TImer for UI updates
	NSTimer *userInterfaceUpdateTimer;
	
	// Misc
	VirtualMPEGTapePlayerRecorder *pDVHS;
	UInt32 uiUpdateCounter;
}

// Button Pushes
- (IBAction) LoadFileButtonPushed:(id)sender;
- (IBAction) StopButtonPushed:(id)sender;
- (IBAction) PlayButtonPushed:(id)sender;
- (IBAction) PauseButtonPushed:(id)sender;
- (IBAction) RecordButtonPushed:(id)sender;
- (IBAction) RewButtonPushed:(id)sender;
- (IBAction) FwdButtonPushed:(id)sender;
- (IBAction) statsDrawerButtonPushed:(id)sender;
- (IBAction) SetRecordDirectoryButtonPushed:(id)sender;
- (IBAction) CreateNaviFileButtonPushed:(id)sender;
- (IBAction) RecordInhibitButtonPushed:(id)sender;

// User interaction with broadcast channel widget
- (IBAction) NewPlayerBroadcastIsochChannel:(id)sender;
- (IBAction) NewRecorderBroadcastIsochChannel:(id)sender;

// Slider updates
- (IBAction) StreamPositionSliderModified:(id)sender;

// Timer callback for UI updates
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer;

// NSDrawer Delagate Functios
- (NSSize)drawerWillResizeContents:(NSDrawer *)sender toSize:(NSSize)contentSize;
- (BOOL)drawerShouldClose:(NSDrawer *)sender;

// NSApplication Delagate Functios
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename;
- (void)applicationWillFinishLaunching:(NSNotification *)aNotification;
- (void)applicationDidFinishLaunching:(NSNotification *)aNotification;
- (void)applicationWillTerminate:(NSNotification *)aNotification;
- (BOOL)windowShouldClose:(id)sender;

- (void) alertNoNaviFile:(NSString*)fileName;

@end
