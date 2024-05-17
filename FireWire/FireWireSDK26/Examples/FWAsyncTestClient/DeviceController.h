/*
	Copyright: 	© Copyright 2007 Apple Computer, Inc. All rights reserved.

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
*/

#import "FWDebugging.h"

#import <Cocoa/Cocoa.h>
#import <IOKit/IOKitLib.h> 
#import <IOKit/IOCFPlugIn.h>
#import <IOKit/firewire/IOFireWireLib.h>

#import "FWBlockCommand.h"
#import "FWCompareSwapCommand.h"

#define kSpecID				0x27		// Apple
#define kSwVersID			0x05		
#define kFWAddressHiKey	 	0x23
#define kFWAddressLoKey	 	0x24
#define kFWPageTableSizeKey 0x25
#define kFWBufferSizeKey	0x26

typedef enum
{
	kCompareSwapStateInitialSubmit,
	kCompareSwapStateSecondSubmit
} CompareSwapState;

typedef struct 
{
	UInt64 address;
	UInt32 length;
} __attribute__((__packed__)) PTE;
// without the __packed__ attribute gcc will pad this structure with an extra 32 bits at the end

typedef struct 
{
	UInt32	pte_count;
	PTE		ptes[];
} PageTable;

void deviceInterestCallback( void *			refcon,
                             io_service_t	service,
                             natural_t		type,
                             void *			arg );

@interface DeviceController : NSObject <CommandDelegate>
{
    IBOutlet id		fWindow;
 	IBOutlet id		fStartStopToggle;
    IBOutlet id		fTextView;
    IBOutlet id		fTestModePopup;
	IBOutlet id		fPacketSizePopup;

    id								fSelectorController;
	io_object_t 					fDeviceReference;
 	NSString *						fName;
	Boolean							fInstantiated;
	IOCFPlugInInterface 	**		fCFPlugInInterface;
	IOFireWireDeviceInterface **	fFWDeviceInterface;
    io_object_t 					fNotification;
    
	UInt32							fQuadBuffer;
	
    BOOL							fSuspended;
	BOOL							fClientStarted;
	BOOL							fStopRequested;
	
	FWAddress						fPageTableAddress;
	UInt32							fPageTableSize;
	UInt32							fBufferSize;
	PageTable *						fPageTable;

	UInt32 *			fReadBuffer;
	UInt32 *			fWriteBuffer;
	
	NSMutableSet *		fWriteCommandSet;
	NSMutableSet *		fReadCommandSet;
	NSMutableArray *		fVectorCommandArray;
	
	UInt32			fPTE_index;
	UInt32			fPTE_offset;
	UInt32			fBuffer_offset;
	UInt32			fInflightCount;
	
	AbsoluteTime	fStartTime;
	FWCommand *		fLastCommand;
	UInt32			fCommandsComplete;
	UInt32			fTimeLoops;
	
	UInt32			fTestMode;
	UInt32			fPacketSize;
	
	CompareSwapState		fCompareSwapState;
	FWCompareSwapCommand *	fCompareSwapCommand;
 }

- (id)initWithDeviceReference:(io_object_t)device withController:(id)selectorController;

- (NSString*)getName;

- (void)instantiateDeviceConnection;

- (IBAction)toggleAction:(id)sender;


- (IBAction)changeTestMode:(id)sender;
- (IBAction)changePacketSize:(id)sender;

@end
