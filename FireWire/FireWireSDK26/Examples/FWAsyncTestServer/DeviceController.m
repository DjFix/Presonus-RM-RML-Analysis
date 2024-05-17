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

#import "DeviceController.h"
#import "SelectorController.h"

#import <IOKit/IOMessage.h>

#include <mach/mach.h>

#define kBufferSize			131072
#define kPageTableSize		4096		// 1 page, more than enough

#define kSpecID				0x27		// Apple
#define kSwVersID			0x05		
#define kFWAddressHiKey	 	0x23
#define kFWAddressLoKey	 	0x24
#define kFWPageTableSizeKey 0x25
#define kFWBufferSizeKey	0x26

enum
{
	kBufferModePhysical = 1000,
	kBufferModePseudo = 1001
};

@interface DeviceController (Private)

- (void)deviceInterest:(io_service_t)service messageType:(natural_t)type messageArgument:(void*)arg;

- (void)windowWillClose:(NSNotification *)aNotification;

- (IOReturn)publishConfigDirectory;
- (void)unpublishConfigDirectory;

- (IOReturn)createPseudoBufferSpace;
- (void)destroyPseudoBufferSpace;

- (IOReturn)startServer;
- (void)stopServer;

- (void)logString:(NSString*)string;

- (IOReturn)createPhysicalBufferSpace;
- (void)destroyPhysicalBufferSpace;

- (IOReturn)createPageTableAddressSpace;
- (void)destroyPageTableAddressSpace;

- (IOReturn)createBuffer;
- (void)destroyBuffer;

- (IOReturn)createPHYPacketListener;
- (void)destroyPHYPacketListener;

@end

void deviceInterestCallback( void *			refcon,
                             io_service_t	service,
                             natural_t		type,
                             void *			arg )
{
    id	object = refcon;    
    [object deviceInterest:service messageType:type messageArgument:arg];
}

@implementation DeviceController

// initWithDeviceReference:withController:
//
//

- (id)initWithDeviceReference:(io_object_t)device withController:(id)selectorController
{	
	io_name_t 				className;
	char					cstr[100];
	IOReturn				status = kIOReturnSuccess;
	CFMutableDictionaryRef	serviceProps = NULL;
	UInt64					guid;
	
	[super init];
			
	fInstantiated = false;
	fDeviceReference = device;
	fSelectorController = selectorController;
    fSuspended = true;

	//
	// get some values from the name registry and generate a name string
	//
	
	status = IOObjectGetClass( device, className );
	if( status == kIOReturnSuccess )
	{			
		status = IORegistryEntryCreateCFProperties( device, &serviceProps,
													kCFAllocatorDefault, kNilOptions );
	}
	 
	if( status == kIOReturnSuccess )
	{
	    CFTypeRef val = CFDictionaryGetValue( serviceProps, CFSTR("GUID") );		
		if (val && CFGetTypeID(val) == CFNumberGetTypeID()) 
		{
			CFNumberGetValue( (CFNumberRef)val, kCFNumberSInt64Type, &guid );
        }
		FWLOG(( "guid = 0x%016llx\n", guid ));
	}
	
	
	if( serviceProps != NULL ) 	
		CFRelease( serviceProps );
	
	// create name string
	sprintf( cstr, "%s <0x%016llx>", className, guid );
	fName = [[NSString stringWithCString:cstr] retain];

    // register device interest notification
    if( status == kIOReturnSuccess )
    {
        IONotificationPortRef	notificationPort;
        
        notificationPort = [fSelectorController getNotificationPort];
        status = IOServiceAddInterestNotification( notificationPort, device, kIOGeneralInterest,
								(IOServiceInterestCallback)deviceInterestCallback, self, &fNotification);

    }
    
    FWLOG(( "DeviceController : initWithDeviceReference, status = 0x%08lx\n", (UInt32)status ));
    
	return self;
}

// awakeFromNib
//
//

- (void)awakeFromNib
{
	// sync buffer mode with UI
	[self changeBufferMode:fBufferModePopup];
}

// dealloc
//
//

- (void)dealloc
{
	FWLOG(( "DeviceController : dealloc\n" ));
		
    if( fNotification ) 
	{
        IOObjectRelease( fNotification );
        fNotification = 0;
    }
	
	[fName release];
	
	[super dealloc];
}

/////////////////////////////////////////////////////

// deviceInterest:messageType:messageArgument:
//
//

- (void)deviceInterest:(io_service_t)service messageType:(natural_t)type messageArgument:(void*)arg
{
	switch( type )
	{
		case kIOMessageServiceIsTerminated:
        
			// handle device removed here
			FWLOG(( "kIOMessageServiceIsTerminated (device removed)\n" ));
            
			[fSelectorController removeObject:self];
        	
            break;
        
        case kIOMessageServiceIsSuspended:
		
            FWLOG(( "kIOMessageServiceIsSuspended bus reset start\n" ));
			
			break;
            
        case kIOMessageServiceIsResumed:
            
			FWLOG(( "kIOMessageServiceIsResumed bus reset complete\n" ));
			
			break;
            
        default:
			break;
	}
}

/////////////////////////////////////////////////////
// accessors
//

// getName
//
//

- (NSString*)getName
{
	return fName;
}

/////////////////////////////////////////////////////

// instantiateDeviceWindow
//
// load plugin and get important interfaces
//

- (void)instantiateDeviceWindow
{
	IOReturn				status = kIOReturnSuccess;

	if( !fInstantiated )
	{
		fInstantiated = true;
            
		//
		// load GUI (opens a new window)
		//
				
		if( ![NSBundle loadNibNamed:@"DeviceWindow" owner:self] )
		{
			FWLOG(( "DeviceController : Failed to load DeviceWindow.nib\n" ));
			status = kIOReturnError;
		}
		
		if( status == kIOReturnSuccess )
		{
			[fWindow setTitle:fName];
		}
	}
	
	//
	// activate window
	//
	
	[fWindow makeKeyAndOrderFront:self];
    
	FWLOG(( "DeviceController : instantiateDeviceWindow, status = 0x%08lx\n", (UInt32)status ));

}

// windowWillClose
//
//

- (void)windowWillClose:(NSNotification *)aNotification
{
	FWLOG(( "DeviceController : windowWillClose\n" ));
	fInstantiated = false;

	if( fServerStarted )
	{
		[self stopServer];
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// publishConfigDirectory
//
//

- (IOReturn)publishConfigDirectory
{
	IOReturn status = kIOReturnSuccess;
	
	if( status == kIOReturnSuccess )
	{
		fUnitDirectory = (*fFWDeviceInterface)->CreateLocalUnitDirectory( fFWDeviceInterface, CFUUIDGetUUIDBytes(kIOFireWireLocalUnitDirectoryInterfaceID) );
		if( fUnitDirectory == NULL )
		{
			status = kIOReturnError;
		}
	}
	
    if ( status == kIOReturnSuccess) 
	{
        status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kConfigUnitSpecIdKey, kSpecID, NULL );
    }
        
    if( status == kIOReturnSuccess ) 
	{
        status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kConfigUnitSwVersionKey, kSwVersID, NULL );
    }

    if( status == kIOReturnSuccess ) 
	{
        UInt32 fwHi = (((UInt32)fPageTableAddress.addressHi) << 8) + (fPageTableAddress.addressLo >> 24);
        UInt32 fwLo = (fPageTableAddress.addressLo << 8) >> 8;
        
		status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kFWAddressHiKey, fwHi, NULL );
        status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kFWAddressLoKey, fwLo, NULL );
        status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kFWPageTableSizeKey, kPageTableSize, NULL );
        status = (*fUnitDirectory)->AddEntry_UInt32( fUnitDirectory, kFWBufferSizeKey, kBufferSize, NULL );
	}

    if( status == kIOReturnSuccess ) 
	{
        status = (*fUnitDirectory)->Publish( fUnitDirectory );
    }

	return status;
}

// unpublishConfigDirectory
//
//

- (void)unpublishConfigDirectory
{
	if( fUnitDirectory ) 
	{
        (*fUnitDirectory)->Unpublish( fUnitDirectory );
		(*fUnitDirectory)->Release( fUnitDirectory );
		fUnitDirectory = NULL;
	}
	
}


/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// createBuffer
//
//

- (IOReturn)createBuffer
{
	IOReturn status = kIOReturnSuccess;

	fBuffer = NULL;
	vm_allocate( mach_task_self(), (vm_address_t*)&fBuffer, kBufferSize, true /*anywhere*/ );
	if( fBuffer == NULL )
		status = kIOReturnError;

	return status;
}

// destroyBuffer
//
//

- (void)destroyBuffer
{
	if( fBuffer )
	{
		vm_deallocate( mach_task_self(), (vm_address_t)fBuffer, kBufferSize );
		fBuffer = NULL;
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// createPHYPacketListener
//
//

- (IOReturn)createPHYPacketListener
{
	IOReturn status = kIOReturnSuccess;

	if( status == kIOReturnSuccess )
	{
		fPHYRacketListener = [[FWPHYPacketListener alloc] initWithDevice: fFWDeviceInterface queueCount:50];
		if( fPHYRacketListener == NULL )
			status = kIOReturnError;
	}


	if( status == kIOReturnSuccess )
	{
		[fPHYRacketListener setDelegate:self];
	}
	
	if( status == kIOReturnSuccess )
	{
		status = [fPHYRacketListener turnOnNotification];
	}
	
	return status;
}

// destroyPHYPacketListener
//
//

- (void)destroyPHYPacketListener
{
	[fPHYRacketListener turnOffNotification];
	[fPHYRacketListener release];
	fPHYRacketListener = NULL;
}

// PHYPacketDataCallback:commandID:data1:data2:
//
//

- (void)PHYPacketDataCallback:(id)listener commandID:(FWClientCommandID)commandID data1:(UInt32)data1 data2:(UInt32)data2
{
	[self logString:[NSString stringWithFormat:@"PHYRx - 0x%08lx %08lx\n", data1, data2]];

	[listener clientCommandIsComplete:commandID];
}

// PHYPacketSkippedCallback:commandID:skippedPacketCount:
//
//

- (void)PHYPacketSkippedCallback:(id)listener commandID:(FWClientCommandID)commandID skippedPacketCount:(UInt32)count
{
	[self logString:[NSString stringWithFormat:@"PHYRx - Skipped %d packets\n", count]];

	[listener clientCommandIsComplete:commandID];	
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// createPhysicalBufferSpace
//
//

- (IOReturn)createPhysicalBufferSpace
{
	IOReturn status = kIOReturnSuccess;

	[self logString:@"Creating a physical buffer address space.\n"];

	[self logString:[NSString stringWithFormat:@"Buffer size = %d\n", kBufferSize]];

	if( status == kIOReturnSuccess )
	{
		fPhysicalBufferSpace =  (*fFWDeviceInterface)->CreatePhysicalAddressSpace( fFWDeviceInterface, kBufferSize, 
																fBuffer, 0, CFUUIDGetUUIDBytes(kIOFireWirePhysicalAddressSpaceInterfaceID) );
		if( fPhysicalBufferSpace == NULL )
			status = kIOReturnError;
	}
	
	if( status == kIOReturnSuccess )
	{
		IOByteCount offset = 0;
		UInt32 index = 0;
 		while( offset < kBufferSize )
		{
			IOByteCount segment_length = 0;
			IOPhysicalAddress segment_address = (*fPhysicalBufferSpace)->GetPhysicalSegment( fPhysicalBufferSpace, offset, &segment_length );
			
			fPageTable->ptes[index].address = EndianU64_NtoB( segment_address );
			fPageTable->ptes[index].length = EndianU32_NtoB( segment_length );
			
			[self logString:[NSString stringWithFormat:@"Buffer Segment %d @ 0x0000.%08lx len %d\n", index, segment_address, segment_length]];
			offset += segment_length;
			index++;
		}

		[self logString:[NSString stringWithFormat:@"PTE count = %d\n", index]];
		
		fPageTable->pte_count = EndianU32_NtoB(index);
	}
	
	return status;
}

// destroyPhysicalBufferSpace
//
//

- (void)destroyPhysicalBufferSpace
{
	if( fPhysicalBufferSpace )
	{
		(*fPhysicalBufferSpace)->Release( fPhysicalBufferSpace );
		fPhysicalBufferSpace = NULL;
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// createPseudoBufferSpace
//
//

- (IOReturn)createPseudoBufferSpace
{
    IOReturn							status = kIOReturnSuccess;
    
	[self logString:@"Creating a software buffer address space.\n"];

	[self logString:[NSString stringWithFormat:@"Buffer size = %d\n", kBufferSize]];

    fPseudoBufferSpace = (*fFWDeviceInterface)->CreatePseudoAddressSpace( fFWDeviceInterface, kBufferSize, 
									self, kBufferSize * 2, fBuffer, kFWAddressSpaceAutoWriteReply | kFWAddressSpaceAutoReadReply, 
									CFUUIDGetUUIDBytes(kIOFireWirePseudoAddressSpaceInterfaceID) );
    if( fPseudoBufferSpace == NULL )
	{
		status = kIOReturnError;
	}

	if( status == kIOReturnSuccess )
	{
        (*fPseudoBufferSpace)->GetFWAddress( fPseudoBufferSpace, &fBufferAddress );
		UInt64 segment_address = ((UInt64)fBufferAddress.addressHi << 32) | fBufferAddress.addressLo;
		fPageTable->ptes[0].address = EndianU64_NtoB( segment_address );
		fPageTable->ptes[0].length = EndianU32_NtoB( kBufferSize );
		
		[self logString:[NSString stringWithFormat:@"Buffer Segment %d : 0x%04x.%08lx len %d\n", 1, fBufferAddress.addressHi, fBufferAddress.addressLo, kBufferSize]];
		
		fPageTable->pte_count = EndianU32_NtoB( 1 );
	}

	[self logString:[NSString stringWithFormat:@"PTE count = %d\n", 1]];
	
	return status;
}

// destroyPseudoBufferSpace
//
//

- (void)destroyPseudoBufferSpace
{
	if( fPseudoBufferSpace )
	{
		(*fPseudoBufferSpace)->Release( fPseudoBufferSpace );
		fPseudoBufferSpace = NULL;
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// createPageTableAddressSpace
//
//

- (IOReturn)createPageTableAddressSpace
{
	IOReturn status = kIOReturnSuccess;
	
	// create buffer for page table
	fPageTable = malloc( kPageTableSize );
	if( fPageTable == NULL )
		status = kIOReturnError;
	
	// create address space for page table
	if( status == kIOReturnSuccess )
	{
	    fPageTableAddressSpace = (*fFWDeviceInterface)->CreatePseudoAddressSpace( fFWDeviceInterface, kPageTableSize, 
									self, 0, fPageTable, (kFWAddressSpaceAutoWriteReply | kFWAddressSpaceAutoReadReply), 
									CFUUIDGetUUIDBytes(kIOFireWirePseudoAddressSpaceInterfaceID) );
		if( fPageTableAddressSpace == NULL )
		{
			status = kIOReturnError;
		}
	}

	if( status == kIOReturnSuccess ) 
	{
        (*fPageTableAddressSpace)->GetFWAddress( fPageTableAddressSpace, &fPageTableAddress );
	
		[self logString:[NSString stringWithFormat:@"Page Table @ 0x%04x.%08lx len %d\n", fPageTableAddress.addressHi, fPageTableAddress.addressLo, kPageTableSize]];
	}
		
	return status;
}

// destroyPageTableAddressSpace
//
//

- (void)destroyPageTableAddressSpace
{
	if( fPageTableAddressSpace )
	{
		(*fPageTableAddressSpace)->Release( fPageTableAddressSpace );
		fPageTableAddressSpace = NULL;
	}
	
	if( fPageTable )
	{
		free( fPageTable );
		fPageTable = NULL;
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// startServer
//
//

- (IOReturn)startServer
{
	IOReturn status = kIOReturnSuccess;
	
	if( !fServerStarted )
	{
		// create plugin
		//
		// load the plugin and get the CFPlugin interface
		//
			
		if( status == kIOReturnSuccess )
		{
			SInt32 	score; // dummy
		
			status = IOCreatePlugInInterfaceForService( fDeviceReference,
														kIOFireWireLibTypeID, 
														kIOCFPlugInInterfaceID,
														&fCFPlugInInterface,
														&score );	// calls Start method
			FWLOG(( "DeviceController : IOCreatePlugInInterfaceForService status = 0x%08x\n", status ));
		}
		
		//
		// get the sample driver interface from the CFPlugin interface
		//
		
		if( status == kIOReturnSuccess )
		{
			HRESULT res;
			res = (*fCFPlugInInterface)->QueryInterface( fCFPlugInInterface, 
											CFUUIDGetUUIDBytes(kIOFireWireDeviceInterfaceID_v9),
											(LPVOID) &fFWDeviceInterface );
			
			if( res != S_OK )
				status = kIOReturnError;
		}

		//
		// open
		//
		
		if( status == kIOReturnSuccess )
		{
			status = (*fFWDeviceInterface)->Open( fFWDeviceInterface );
		}
		
		//
		// attach callbacks to the current runloop
		//
		
		if( status == kIOReturnSuccess )
		{
			status = (*fFWDeviceInterface)->AddCallbackDispatcherToRunLoop( fFWDeviceInterface, CFRunLoopGetCurrent() );
		}
		
		if( status == kIOReturnSuccess )
		{
			status = [self createPageTableAddressSpace];
		}

		if( status == kIOReturnSuccess )
		{
			status = [self createBuffer];
		}

		if( status == kIOReturnSuccess )
		{
			if( fBufferMode == kBufferModePseudo )
			{
				status = [self createPseudoBufferSpace];
			}
			else
			{
				status = [self createPhysicalBufferSpace];
			}
		}
		
		if( status == kIOReturnSuccess )
		{
			IOReturn phy_rx_status = [self createPHYPacketListener];
			if(  phy_rx_status == kIOReturnUnsupported )
			{
				[self logString:@"PHY packet receive not supported on this hardware.\n" ];
			}
			else
			{
				status = kIOReturnSuccess;
			}
		}
			
		if( status == kIOReturnSuccess )
		{
			status = [self publishConfigDirectory];
		}

		if( status == kIOReturnSuccess )
		{
			[fBufferModePopup setEnabled:NO];
		}
		
		if( status == kIOReturnSuccess )
		{
			fServerStarted = YES;
			[fStartStopToggle setTitle:@"Stop"];
			[self logString:@"Server started\n" ];	
		}
		else
		{
			[self logString:[NSString stringWithFormat:@"Error 0x%08lx starting server\n", status]];
		}		
	}
	
	return status;
}

// stopServer
//
//

- (void)stopServer
{
	if( fServerStarted )
	{
		[self unpublishConfigDirectory];
		
		[self destroyPHYPacketListener];
		
		[self destroyPhysicalBufferSpace];
		
		[self destroyPseudoBufferSpace];
		
		[self destroyPageTableAddressSpace];

		[self destroyBuffer];
		
		//
		// release driver interface
		//
		
		if( fFWDeviceInterface != NULL )
		{
			(*fFWDeviceInterface)->RemoveCallbackDispatcherFromRunLoop(fFWDeviceInterface);
			(*fFWDeviceInterface)->Close(fFWDeviceInterface);
			(*fFWDeviceInterface)->Release(fFWDeviceInterface);
			fFWDeviceInterface = NULL;
		}
		
		//	
		// release plugin interface
		//
		
		if( fCFPlugInInterface != NULL )
		{	
			IOReturn status = kIOReturnSuccess;
			status = IODestroyPlugInInterface(fCFPlugInInterface); 		// calls Stop method
			FWLOG(( "DeviceController : IODestroyPlugInInterface status = 0x%08x\n", status ));
			fCFPlugInInterface = NULL;
		}

		[fBufferModePopup setEnabled:YES];
		
		fServerStarted = NO;
		[fStartStopToggle setTitle:@"Start"];
		
		[self logString:@"Server stopped\n" ];
	}
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// toggleAction:
//
//

- (IBAction)toggleAction:(id)sender
{
	if( fServerStarted )
	{
		[self stopServer];
	}
	else
	{
		[self startServer];
	}
}

// changeBufferMode:
//
//

- (IBAction)changeBufferMode:(id)sender
{
	fBufferMode = [[sender selectedItem] tag];
}

// logString:
//
//

- (void)logString:(NSString*)string
{
    NSRange 	endMarker;
    BOOL	editFlag;

    endMarker = NSMakeRange([[fTextView string] length], 0);
    
    [fTextView setSelectedRange:endMarker];
    editFlag = [fTextView isEditable];
    if( !editFlag )
        [fTextView setEditable:YES];
        
    [fTextView insertText:string];
    
    if( !editFlag )
        [fTextView setEditable:NO];
        
    endMarker.location += [string length];
    [fTextView scrollRangeToVisible:endMarker];
}

@end