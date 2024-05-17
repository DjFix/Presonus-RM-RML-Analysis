/*
	File:		AVHDD.h

 Synopsis: This is the header file for the main application controller object 

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

#pragma mark -
#pragma mark ===================================
#pragma mark Typedefs and Enums
#pragma mark ===================================

// Trick Mode Playback Constants
enum
{
	// Fast Fwd Speed
	kPlayFastFwd1FrameIncrement = 1,		// Not burst mode (2x)
	kPlayFastFwd2FrameIncrement = 2,		// Not burst mode (3x)
	kPlayFastFwd3FrameIncrement = 20,		// Uses burst mode (4x)
	kPlayFastFwd4FrameIncrement = 25,		// Uses burst mode (5x)
	kPlayFastFwd5FrameIncrement = 50,		// Uses burst mode (10x)
	kPlayFastFwd6FrameIncrement = 75,		// Uses burst mode (15x)
	kPlayFastestFwdFrameIncrement = 75,		// Uses burst mode (15x)
	
	// Fast Rev Speed
	kPlayFastRev1FrameDecrement = 3,		// Not burst mode (2x)
	kPlayFastRev2FrameDecrement = 4,		// Not burst mode (3x)
	kPlayFastRev3FrameDecrement = 22,		// Uses burst mode (4x)
	kPlayFastRev4FrameDecrement = 27,		// Uses burst mode (5x)
	kPlayFastRev5FrameDecrement = 52,		// Uses burst mode (10x)
	kPlayFastRev6FrameDecrement = 77,		// Uses burst mode (15x)
	kPlayFastestRevFrameDecrement = 77,		// Uses burst mode (15x)
	
	// High-speed play busrt mode (Fast3,Fast4,Fast5,Fast6,Fastest) 
	// burst frame count
	kPlayHighSpeedPlayBurstCount = 5,
	
	// Slow Fwd/Rev Speed
	kPlaySlow1FrameRepeat = 2,
	kPlaySlow2FrameRepeat = 3,
	kPlaySlow3FrameRepeat = 5,
	kPlaySlow4FrameRepeat = 10,
	kPlaySlow5FrameRepeat = 15,
	kPlaySlow6FrameRepeat = 30,
	kPlaySlowestFrameRepeat = 30
};

// Info specific to each supported DV format
typedef struct DVFormatInfoStruct
{
	UInt8 dvMode;
	UInt32 frameSize;
	NSString *pDVModeName;
	UInt32 averageCyclesPerFrame;
	bool isPal;
	UInt32 numDifSequences;
	UInt32 timeBase;
	char fourcc[4];
}DVFormatInfo, *DVFormatInfoPtr;

@class PreferenceController;

#pragma mark -
#pragma mark ===================================
#pragma mark AVHDD Class Variable Declarations
#pragma mark ===================================

@interface AVHDD : NSObject
{
    IBOutlet NSTextView *avcLog;
    IBOutlet NSTextField *avcMode;
	
    IBOutlet NSTextField *outputPlugChannel;
    IBOutlet NSTextField *outputPlugConnections;
    IBOutlet NSTextField *outputPlugSpeed;

    IBOutlet NSTextField *outputPlugState;
    IBOutlet NSTextField *outputPlugStateExtended;

    IBOutlet NSTextField *outputPlugTimecode;
    IBOutlet NSTextField *outputPlugDCLOverruns;
    IBOutlet NSSlider *streamPositionSlider;

    IBOutlet NSTextField *inputPlugChannel;
    IBOutlet NSTextField *inputPlugConnections;
    IBOutlet NSTextField *inputPlugSpeed;
    IBOutlet NSTextField *inputPlugDCLOverruns;

	IBOutlet NSTextField *dvStreamFileName;
    IBOutlet NSTextField *dvStreamFileSize;
	
    IBOutlet NSButton *verboseAVCLoggingButton;
	
	IBOutlet NSButton *openExistingDVStreamFileButton;
	IBOutlet NSButton *CreateNewDVStreamFileButton;
	IBOutlet NSButton *CloseDVStreamFileButton;
	IBOutlet NSButton *writeProtectDVStreamFileButton;
	IBOutlet NSButton *LoopPlaybackButton;
	
	IBOutlet NSStepper *outputChannelStepper;
	IBOutlet NSStepper *inputChannelStepper;

	// Icon sytle transport control buttons
	IBOutlet NSButton *XmitterPlayButton;
	IBOutlet NSButton *XmitterStopButton;
	IBOutlet NSButton *XmitterPauseButton;
	IBOutlet NSButton *XmitterFFwdButton;
	IBOutlet NSButton *XmitterFRevButton;

	IBOutlet NSButton *XmitterFrameFwdButton;
	IBOutlet NSButton *XmitterFrameRevButton;
	
	IBOutlet NSButton *ReceiverRecButton;

	IBOutlet NSComboBox *timecodeMode;

	// Images for Icon buttons
	NSImage *XmitterPlayButtonNormalImage;
	NSImage *XmitterPlayButtonBlueImage;
	NSImage *XmitterStopButtonNormalImage;
	NSImage *XmitterStopButtonBlueImage;
	NSImage *XmitterPauseButtonNormalImage;
	NSImage *XmitterPauseButtonBlueImage;
	NSImage *XmitterFFwdButtonNormalImage;
	NSImage *XmitterFRevButtonNormalImage;

	NSImage *ReceiverRecButtonNormalImage;
	NSImage *ReceiverRecButtonRecordingImage;

	class AVCTarget *avc;
	class DVTransmitter *xmitter;
	class DVReceiver *receiver;
	class StringLogger *stringLogger;
	pthread_t RTThread;
	pthread_t AVCThread;
	pthread_mutex_t logAccessMutex;
	pthread_mutex_t inFileAccessMutex;
	NSMutableArray *availTStreams;
	NSMutableString *avcLogString;
	NSMutableArray *avcLogUpdateStringArray;
	NSTimer *userInterfaceUpdateTimer;
	NSString *TSFilePath;
	PreferenceController *preferenceController;
	volatile bool AVCThreadReady;
	unsigned int slippedCycleCount;
	float transmitterBufferSizeSliderValue;
	float receiverBufferSizeSliderValue;
}

#pragma mark -
#pragma mark ===================================
#pragma mark AVHDD Class Method Declarations
#pragma mark ===================================

#pragma mark -----------------------------------
#pragma mark Misc Functions
#pragma mark -----------------------------------

- (void) setAVCThreadReady;
- (IBAction) showPreferencePanel:(id)sender;
- (void) inFileMutexLock;
- (void) inFileMutexUnLock;

#pragma mark -----------------------------------
#pragma mark Logging & UI Update Functions
#pragma mark -----------------------------------

- (void) addToAVCLog: (NSString*)s;
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer;
- (IBAction) clearLog:(id)sender;
- (IBAction) verboseAVCButtonPushed:(id)sender;
- (bool) verboseAVCLoggingEnabled;
- (BOOL)isWriteProtect;
- (BOOL)shouldDoTimeCodeInsertion;
- (unsigned int) currentTimeCodeMode;
- (BOOL)shouldLoopPlaBack;

#pragma mark -----------------------------------
#pragma mark DV Transmitter Button Function
#pragma mark -----------------------------------

- (IBAction) XmitterPlayButtonPushed:(id)sender;
- (IBAction) XmitterStopButtonPushed:(id)sender;
- (IBAction) XmitterPauseButtonPushed:(id)sender;
- (IBAction) XmitterFFwdButtonPushed:(id)sender;
- (IBAction) XmitterFRevButtonPushed:(id)sender;
- (IBAction) XmitterFrameFwdButtonPushed:(id)sender;
- (IBAction) XmitterFrameRevButtonPushed:(id)sender;
- (IBAction) streamPositionSliderModified:(id)sender;

#pragma mark -----------------------------------
#pragma mark DV Receiver Button Function
#pragma mark -----------------------------------

- (IBAction) ReceiverRecButtonPushed:(id)sender;

#pragma mark -----------------------------------
#pragma mark Transmitter/Receiver Channel Get/Set Functions
#pragma mark -----------------------------------

- (IBAction) openExistingDVStreamFileButtonPushed:(id)sender;
- (IBAction) CreateNewDVStreamFileButtonPushed:(id)sender;
- (IBAction) CloseDVStreamFileButtonPushed:(id)sender;

- (IBAction) changeInputChannelStepperPushed:(id)sender;
- (IBAction) changeOutputChannelStepperPushed:(id)sender;
- (void) updateInputChannelStepperIntVal: (unsigned int ) chan;
- (void) updateOutputChannelStepperIntVal: (unsigned int ) chan;
- (int) getTransmitterChannel;
- (int) getReceiverChannel;

#pragma mark -----------------------------------
#pragma mark AVC Transport Control Handlers
#pragma mark -----------------------------------

- (void) avcPlayCmdHandler;
- (void) avcStopCmdHandler;
- (void) avcRecordCmdHandler;
- (void) avcRecordStopCmdHandler;

#pragma mark -----------------------------------
#pragma mark DV Stream Prep Functions
#pragma mark -----------------------------------

- (void) prepareTSPacketFetcher;
- (void) prepareTSPacketReceiver;

- (void) adjustTimeCodePosition: (unsigned int) newFrameOffset;  
- (void) adjustTimeCodePositionToEOF;  

#pragma mark -----------------------------------
#pragma mark DV Transmitter UI Update Functions
#pragma mark -----------------------------------

- (void) updateDVStreamFileSize: (UInt64) size;

- (void) updateOutputPlugConnections: (unsigned int) count;
- (void) updateOutputPlugChannel: (unsigned int) channel;
- (void) updateOutputPlugState: (NSString*)s;
- (void) updateOutputPlugStateExtended: (NSString*)s;
- (void) updateOutputPlugSpeed: (NSString*)s;
- (void) updateOutputPlugTimecode: (NSString*)s;
- (void) incrementOutputPlugDCLOverrunCount;

#pragma mark -----------------------------------
#pragma mark DV Receiver UI Update Functions
#pragma mark -----------------------------------

- (void) updateInputPlugConnections: (unsigned int) count;
- (void) updateInputPlugChannel: (unsigned int) channel;
- (void) updateInputPlugSpeed: (NSString*)s;
- (void) incrementInputPlugDCLOverrunCount;

#pragma mark -----------------------------------
#pragma mark Misc UI Update Functions
#pragma mark -----------------------------------

- (void) updateAVCTargetObject: (AVCTarget*) avcObject;
- (void) updateDVTransmitterObject: (DVTransmitter*) xmitterObject;
- (void) updateDVReceiverObject: (DVReceiver*) receiverObject;

#pragma mark -----------------------------------
#pragma mark NSApplication Delagate Functios
#pragma mark -----------------------------------

- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename;
- (void)applicationDidFinishLaunching:(NSNotification *)aNotification;
- (void)applicationWillTerminate:(NSNotification *)aNotification;
- (BOOL)windowShouldClose:(id)sender;

@end

#pragma mark -
#pragma mark ===================================
#pragma mark Extern declarations for global vars
#pragma mark ===================================

extern AVHDD *gpUserIntf;
extern DVFormatInfoPtr gpDVFormatInfo;
extern class AVCTarget *gpAVC;
extern class DVTransmitter *gpXmitter;
extern class DVReceiver *gpReceiver;
