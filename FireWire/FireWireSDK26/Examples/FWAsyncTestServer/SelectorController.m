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
				ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

#import "SelectorController.h"
#import "DeviceController.h"
#import <mach/mach.h>

@interface SelectorController (Private)

- (CFDictionaryRef)createMatchingDictionary;
- (void)deviceAdded:(io_iterator_t)iterator;

@end

void remoteDeviceAddedCallback( void* refCon, io_iterator_t iterator );

void remoteDeviceAddedCallback( void* refCon, io_iterator_t iterator )
{
    id	object = refCon;    
    [object deviceAdded:iterator];
}

@implementation SelectorController

// init
//
//

- (id)init
{
    CFDictionaryRef matchDictionary = 0;
	kern_return_t 	status = kIOReturnSuccess;

	FWLOG(( "SelectorController : init\n" ));

	[super init];
	
	fDeviceArray = [[NSMutableArray alloc] init];
		
	// get master port
	status = IOMasterPort( bootstrap_port, &fMasterPort );

	if( status == kIOReturnSuccess )
	{
		fNotificationPort = IONotificationPortCreate( fMasterPort );
        if( fNotificationPort == NULL )
		{
			FWLOG(( "SelectorController : failed to create notification port!\n" ));
			status = kIOReturnError;
		}
	}	
    
	if( status == kIOReturnSuccess )
    {
		CFRunLoopSourceRef runLoopSource;

		FWLOG(( "SelectorController : got master port\n" ));
        
        runLoopSource = IONotificationPortGetRunLoopSource( fNotificationPort );
		CFRunLoopAddSource( CFRunLoopGetCurrent(), runLoopSource, kCFRunLoopDefaultMode );
		CFRelease( runLoopSource );
	}
	
	//
	// get matching devices
	//
	
	if( status == kIOReturnSuccess )
	{
		matchDictionary = [self createMatchingDictionary];
		if( matchDictionary == NULL )
			status = kIOReturnError;
	}

    if( status == kIOReturnSuccess )
    {
        CFRetain( matchDictionary );
		status = IOServiceAddMatchingNotification( fNotificationPort, kIOMatchedNotification,
                                    matchDictionary, remoteDeviceAddedCallback, (void*)self, &fMatchingIterator );
        CFRelease( matchDictionary );
    }

    [self deviceAdded:fMatchingIterator];
  
	return self;
}

// createMatchingDictionary
//
//

- (CFDictionaryRef)createMatchingDictionary
{
	// create a matching dictionary
	CFMutableDictionaryRef	matchingDictionary = CFDictionaryCreateMutable(kCFAllocatorDefault, 
														0, &kCFTypeDictionaryKeyCallBacks, 
														&kCFTypeDictionaryValueCallBacks);

	// specify class type
	CFDictionaryAddValue(matchingDictionary, CFSTR("IOProviderClass"), CFSTR("IOFireWireLocalNode"));

	return matchingDictionary;
}

// removeObject
//
//

-(void)removeObject:(id)object
{
    [fDeviceArray removeObject:object];
    [fBrowser reloadColumn:0];
}

// deviceAdded
//
//

- (void)deviceAdded:(io_iterator_t)iterator
{
    IOReturn 		status = kIOReturnSuccess;

	if( status == kIOReturnSuccess )
	{
		io_object_t 	deviceReference = 0;
	
		IOIteratorReset( iterator );
		while ( (deviceReference = IOIteratorNext( iterator )) )
		{
			DeviceController * device = [[DeviceController alloc] initWithDeviceReference:deviceReference withController:self];
			[fDeviceArray addObject:device];
            [device release];
	
			FWLOG(( "SelectorController : DeviceController = 0x%08lx\n", (UInt32)device ));
		}
	}

    [fBrowser reloadColumn:0];
	[fBrowser selectRow:0 inColumn:0];
}

// getNotificationPort
//
//

- (IONotificationPortRef)getNotificationPort
{
    return fNotificationPort;
}

// awakeFromNib
//
//

- (void)awakeFromNib
{
	[fBrowser setTarget:self];
	[fBrowser setDoubleAction:@selector(selectItem:)];
	[fWindow makeKeyAndOrderFront:self];
	[fBrowser selectRow:0 inColumn:0];
}

// windowWillClose
//
//

- (void)windowWillClose:(NSNotification *)aNotification
{
	FWLOG(( "SelectorController : windowWillClose\n" ));
}

// dealloc
//
//

- (void)dealloc
{
	FWLOG(( "SelectorController : dealloc\n" ));

    if( fMatchingIterator ) 
	{
        IOObjectRelease(fMatchingIterator);
        fMatchingIterator = 0;
    }
    
	if( fNotificationPort != NULL )
    {
		IONotificationPortDestroy( fNotificationPort );
        fNotificationPort = NULL;
    }

	// release master port
    if( fMasterPort ) 
	{
        mach_port_deallocate( mach_task_self(), fMasterPort );
        fMasterPort = 0;
    }
        
	[fDeviceArray removeAllObjects];
	[fDeviceArray release];

	[super dealloc];
}

// browser:numberOfRowsInColumn
//
//

- (int)browser:(NSBrowser *)sender numberOfRowsInColumn:(int)column
{
	if( column == 0 )
		return [fDeviceArray count];
	else
		return 0;
}

// browser:willDisplayCell:row:column:
//
//

- (void)browser:(NSBrowser *)sender willDisplayCell:(id)cell atRow:(int)row column:(int)column
{
	DeviceController *	device = NULL;
	IOReturn		status = kIOReturnSuccess;
	
	if( fDeviceArray == NULL || row >= [fDeviceArray count])
		status = kIOReturnError;
		
	if( status == kIOReturnSuccess )
	{	
		device = [fDeviceArray objectAtIndex:row];
		if( device == NULL )
			status = kIOReturnError;
	}
 	
	if( status == kIOReturnSuccess )
	{
		[cell setStringValue:[device getName]];
		[cell setLeaf:true];
		[cell setRepresentedObject:device];
	}
}

// selectItem
//
//

- (void)selectItem:(id)sender
{
	id cell;
	cell = [fBrowser selectedCell];
	[[cell representedObject] instantiateDeviceWindow];
}

@end
