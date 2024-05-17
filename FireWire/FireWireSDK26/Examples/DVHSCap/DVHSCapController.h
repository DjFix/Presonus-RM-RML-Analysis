/*
	File:		DVHSCapController.h

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


@interface DVHSCapController : NSObject {

    IBOutlet NSTextField *DVHSTimecode;
    IBOutlet NSTextField *DVHSState;
    IBOutlet NSTextField *DVHSDeviceName;
    IBOutlet NSTextField *DVHSPowerState;

	// DVHS Controller Buttons
	IBOutlet NSButton *DVHSPlayButton;
	IBOutlet NSButton *DVHSStopButton;
	IBOutlet NSButton *DVHSPauseButton;
	IBOutlet NSButton *DVHSFFwdButton;
	IBOutlet NSButton *DVHSFRevButton;
	IBOutlet NSButton *DVHSRecButton;
	IBOutlet NSButton *DVHSPowerButton;

	IBOutlet NSButton *CaptureButton;
	IBOutlet NSButton *ExportButton;
	IBOutlet NSButton *ExportPreviewModeButton;
	IBOutlet NSButton *CaptureDemuxModeButton;
	
    IBOutlet NSTextField *PacketCount;
    IBOutlet NSTextField *Bitrate;
    IBOutlet NSTextField *Overruns;
    IBOutlet NSTextField *FileName;
    IBOutlet NSTextView *avcLog;
	
	NSImage *DVHSPlayButtonNormalImage;
	NSImage *DVHSStopButtonNormalImage;
	NSImage *DVHSPauseButtonNormalImage;
	NSImage *DVHSFFwdButtonNormalImage;
	NSImage *DVHSFRevButtonNormalImage;
	NSImage *DVHSRecButtonNormalImage;

	NSMutableString *avcLogString;
	NSTimer *userInterfaceUpdateTimer;
}

- (IBAction) DVHSPlayButtonPushed:(id)sender;
- (IBAction) DVHSStopButtonPushed:(id)sender;
- (IBAction) DVHSPauseButtonPushed:(id)sender;
- (IBAction) DVHSFFwdButtonPushed:(id)sender;
- (IBAction) DVHSFRevButtonPushed:(id)sender;
- (IBAction) DVHSRecButtonPushed:(id)sender;
- (IBAction) DVHSPowerButtonPushed:(id)sender;

- (void) EnableDVHSControllerUI;
- (void) DisableDVHSControllerUI;
- (void) addToAVCLog:(NSString*)string;

- (void) updateDVHSTimecode: (NSString*)s;
- (void) updateDVHSState: (NSString*)s;
- (void) updateDVHSDeviceName: (NSString*)s;
- (void) updateDVHSPowerState: (NSString*)s;

- (IBAction) CaptureButtonPushed:(id)sender;
- (IBAction) ExportButtonPushed:(id)sender;
- (void) stopCapture;
- (void) stopExport;
- (void) userInterfaceUpdateTimerExpired:(NSTimer*)timer;
- (void) incrementDCLOverrunCount;
- (void) resetDCLOverrunCount;

@end
