/*
	File:		AVCDeviceControlPanelController.h
 
 Synopsis: This is the header file for the AVCDevice Control-Panel Controller 
 
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


#import <Cocoa/Cocoa.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/uio.h>
#include <unistd.h>

// A structure to hold the fields of iPCR/oPCR registers!
struct PCRPlugValues
{
	// These are for both iPCR and oPCR
	UInt32 online;
	UInt32 broadcast;
	UInt32 p2pCount;
	UInt32 channel;

	// These are only for oPCR
	UInt32 rate;
	UInt32 overhead;
	UInt32 payloadInQuads;
};

@interface AVCDeviceControlPanelController : NSObject {

	IBOutlet NSWindow *deviceControlPanelWindow;
	IBOutlet NSTabView *deviceControlPanelTabView;
	
    IBOutlet NSTextField *GUID;
    IBOutlet NSTextField *openedByThisApp;

	IBOutlet NSTableView *InputPlugsTable;
	IBOutlet NSTableView *OutputPlugsTable;

	IBOutlet NSTextField *InputPlugsCount;
	IBOutlet NSTextField *OutputPlugsCount;

	IBOutlet NSTextField *subunitInfoPage;
	IBOutlet NSTextField *outputPlugSigFmtPlugNum;
	IBOutlet NSTextField *inputPlugSigFmtPlugNum;
	IBOutlet NSTextField *avcCommandBytes;
	IBOutlet NSPopUpButton *inputPlugChannel;
	IBOutlet NSPopUpButton *outputPlugChannel;
	IBOutlet NSPopUpButton *outputPlugRate;
	IBOutlet NSButton *eia775Info;
	IBOutlet NSButton *openCloseDeviceButton;

	IBOutlet NSButton *inputPlugConnectButton;
	IBOutlet NSButton *inputPlugDisconnectButton;
	IBOutlet NSButton *outputPlugConnectButton;
	IBOutlet NSButton *outputPlugDisconnectButton;
	IBOutlet NSButton *rereadPlugsButton;
	IBOutlet NSButton *PollPlugRegistersButton;
	
	IBOutlet NSButton *TapePlayButton;
	IBOutlet NSButton *TapeStopButton;
	IBOutlet NSButton *TapePauseButton;
	IBOutlet NSButton *TapeFFwdButton;
	IBOutlet NSButton *TapeFRevButton;
	IBOutlet NSButton *TapeRecButton;
	
	IBOutlet NSTextField *TapeTransportState;
	IBOutlet NSTextField *TapeMediumInfoState;
	IBOutlet NSTextField *TapeTimeCodeState;
	IBOutlet NSButton *PollTapeSubunitButton;
	IBOutlet NSButton *LogTapeSubunitPollingButton;
	IBOutlet NSMatrix *TapeTimeCodeType;
	
	IBOutlet NSTextView *avcLog;
	NSMutableString *avcLogString;

	IBOutlet NSTextField *CEA931DeterministicChannelNumber;
	IBOutlet NSMatrix *CEA931PassThroughCommandType;
	IBOutlet NSButton *ViewerButton;
	
	NSImage *TapePlayButtonNormalImage;
	NSImage *TapeStopButtonNormalImage;
	NSImage *TapePauseButtonNormalImage;
	NSImage *TapeFFwdButtonNormalImage;
	NSImage *TapeFRevButtonNormalImage;
	NSImage *TapeRecButtonNormalImage;
	IBOutlet NSPopUpButton *tapePlayMode;
	IBOutlet NSPopUpButton *tapeRecMode;
	IBOutlet NSPopUpButton *tapeWindMode;
	
	AVCDevice *pAVCDevice;
	AVCDeviceCommandInterface *pAVCDeviceCommandInterface;
	AVCDeviceStream* pAVCDeviceStream;
	
	struct sockaddr_in socketAddr;
	int viewerSocket;
	NSTask *viewerTask;

	UInt32 numInputPCRs;
	UInt32 numOutputPCRs;
	PCRPlugValues iPCRValues[32];
	PCRPlugValues oPCRValues[32];

	// TImer for UI updates
	NSTimer *userInterfaceUpdateTimer;
}

+(AVCDeviceControlPanelController *)withDevice:(AVCDevice*) pAVCdevice;
-(void)WindowDeminiaturizeAndBringToFront;
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer;
- (void) addToAVCLog:(NSString*)string;
-(void)DeviceHasGoneAway;
-(void)LogBusResetMessage;
-(AVCDeviceCommandInterface*)GetAVCDeviceCommandInterface;
-(AVCDevice*)GetAVCDevice;
-(bool)isAVCDeviceOpenedByThisApp;
-(void)updateAVCCommandBytesView:(NSString*)commandByteString;

// Buttons not in tab-view
- (IBAction)sendAVCCommandBytes:(id)sender;
- (IBAction)clearLog:(id)sender;
- (IBAction)openCloseDeviceButtonPushed:(id)sender;

// Buttons on General tab
- (IBAction)UnitInfoCommand:(id)sender;
- (IBAction)PlugInfoCommand:(id)sender;
- (IBAction)SubunitInfoCommand:(id)sender;
- (IBAction)outputPlugSigFmtCommand:(id)sender;
- (IBAction)inputPlugSigFmtCommand:(id)sender;

// Buttons on CEA 775/931 tab
- (IBAction)getEIA775Info:(id)sender;
- (IBAction)getDTCPInfo:(id)sender;
- (IBAction) UpButtonPushed:(id)sender;
- (IBAction) DownButtonPushed:(id)sender;
- (IBAction) SetChannelButtonPushed:(id)sender;
- (IBAction) Num0ButtonPushed:(id)sender;
- (IBAction) Num1ButtonPushed:(id)sender;
- (IBAction) Num2ButtonPushed:(id)sender;
- (IBAction) Num3ButtonPushed:(id)sender;
- (IBAction) Num4ButtonPushed:(id)sender;
- (IBAction) Num5ButtonPushed:(id)sender;
- (IBAction) Num6ButtonPushed:(id)sender;
- (IBAction) Num7ButtonPushed:(id)sender;
- (IBAction) Num8ButtonPushed:(id)sender;
- (IBAction) Num9ButtonPushed:(id)sender;
- (IBAction) DotButtonPushed:(id)sender;
- (IBAction) EnterButtonPushed:(id)sender;
- (IBAction) ChanUpButtonPushed:(id)sender;
- (IBAction) ChanDownButtonPushed:(id)sender;
- (IBAction) PrevChanButtonPushed:(id)sender;
- (IBAction) VolUpButtonPushed:(id)sender;
- (IBAction) VolDownButtonPushed:(id)sender;
- (IBAction) MuteButtonPushed:(id)sender;
- (IBAction) ArrowUpButtonPushed:(id)sender;
- (IBAction) ArrowDownButtonPushed:(id)sender;
- (IBAction) ArrowLeftButtonPushed:(id)sender;
- (IBAction) ArrowRightButtonPushed:(id)sender;
- (IBAction) SelectButtonPushed:(id)sender;
- (void) SendCEA931PassThroughCommand:(int)operationID;
- (void) SendChannelChangeCommand:(int)channel;
- (IBAction) ViewerButtonPushed:(id)sender;

// Buttons on Plug tab
- (IBAction)makeInputPlugConnection:(id)sender;
- (IBAction)breakInputPlugConnection:(id)sender;
- (IBAction)makeOutputPlugConnection:(id)sender;
- (IBAction)breakOutputPlugConnection:(id)sender;
- (IBAction)rereadPlugs:(id)sender;

// Buttons on Tape tab
- (IBAction) TapePlugInfoButtonPushed:(id)sender;
- (IBAction) TapeInputSignalModeButtonPushed:(id)sender;
- (IBAction) TapeOutputSignalModeButtonPushed:(id)sender;
- (IBAction) TapeMediumInfoButtonPushed:(id)sender;
- (IBAction) TapeTransportStateButtonPushed:(id)sender;
- (IBAction) TapeATNButtonPushed:(id)sender;
- (IBAction) TapeEjectButtonPushed:(id)sender;
- (IBAction) TapePlaySpecificModeButtonPushed:(id)sender;
- (IBAction) TapeRecSpecificModeButtonPushed:(id)sender;
- (IBAction) TapeWindSpecificModeButtonPushed:(id)sender;
- (IBAction) TapePlayButtonPushed:(id)sender;
- (IBAction) TapeStopButtonPushed:(id)sender;
- (IBAction) TapePauseButtonPushed:(id)sender;
- (IBAction) TapeFFwdButtonPushed:(id)sender;
- (IBAction) TapeFRevButtonPushed:(id)sender;
- (IBAction) TapeRecButtonPushed:(id)sender;
- (IBAction) TapeStatusOneShotButtonPushed:(id)sender;
-(void) PollTapeStatus;

// Buttons on Music tab
- (IBAction) MusicPlugInfoButtonPushed:(id)sender;
- (IBAction) FullDeviceAnalysisButtonPushed:(id)sender;

#pragma mark -----------------------------------
#pragma mark TableView Delagate Functios
#pragma mark -----------------------------------

- (int) numberOfRowsInTableView: (NSTableView*) aTableView;

- (id) tableView: (NSTableView*) aTableView
objectValueForTableColumn: (NSTableColumn*) aTableColumn
			 row: (int) rowIndex;

- (void) tableView: (NSTableView*) aTableView
	setObjectValue: (id) anObject
	forTableColumn: (NSTableColumn*) aTableColumn
			   row: (int) rowIndex;

@end
