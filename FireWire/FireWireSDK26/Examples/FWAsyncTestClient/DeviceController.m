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

#import "DeviceController.h"
#import "SelectorController.h"

#import "FWReadCommand.h"
#import "FWWriteCommand.h"
#import "FWVectorCommand.h"
#import "FWPHYCommand.h"

#import <IOKit/IOMessage.h>

#include <mach/mach.h>

#define kVectorCommandCount 2
#define kVectorSubcommandCount 16

#define kCommandCount 32
#define kCommandSize 4096
#define kTimeLoops 1000

enum
{
	kTestModeWrite = 1000,
	kTestModeRead = 1001,
	kTestModeCompareSwap = 1004,
	kTestModeVectorWrite = 1005,
	kTestModeVectorRead = 1006,
	kTestModePHYTransmit = 1007,
	kTestModeVectorPHYTransmit = 1008
};

@interface DeviceController (Private)

- (void)deviceInterest:(io_service_t)service messageType:(natural_t)type messageArgument:(void*)arg;

- (void)windowWillClose:(NSNotification *)aNotification;

- (IOReturn)startCompareSwapTest;
- (void)completeCompareSwap;
- (void)finishCompareSwap;

- (IOReturn)submitInitialCommandsType:(UInt32)type;
- (BOOL)submitNextCommand:(FWBlockCommand*)command type:(UInt32)type;

- (void)stopClient;
- (void)stopComplete;
- (IOReturn)startClient;
- (void)logString:(NSString*)string;
- (IOReturn)readConfigDirectory;

- (IOReturn)createWriteBuffer;
- (void)destroyWriteBuffer;
- (IOReturn)createReadBuffer;
- (void)destroyReadBuffer;

- (NSString*)stringForTestMode:(UInt32)test_mode;
- (void)commandFinalize:(FWBlockCommand*)command withStatus:(IOReturn)status;
- (void)finishCommand:(FWBlockCommand*)command withStatus:(IOReturn)status;

- (IOReturn)submitInitialVectorCommandsOfType:(UInt32)type;

- (BOOL)submitNextVectorCommand:(id)vector_command type:(UInt32)type;
- (void)vectorCommandFinalize:(id)vector_command withStatus:(IOReturn)status;
- (void)finishVectorCommand:(id)vector_command withStatus:(IOReturn)status;

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
			
	fInstantiated = NO;
	fClientStarted = NO;
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
	fName = [[NSString stringWithUTF8String:cstr] retain];

    // register device interest notification
    if( status == kIOReturnSuccess )
    {
        IONotificationPortRef	notificationPort;
        
        notificationPort = [fSelectorController getNotificationPort];
        status = IOServiceAddInterestNotification( notificationPort, device, kIOGeneralInterest,
								(IOServiceInterestCallback)deviceInterestCallback, self, &fNotification);

    }
    
	#ifdef __LP64__
		FWLOG(( "DeviceController : initWithDeviceReference, status = 0x%08x\n", (UInt32)status ));
    #else
		FWLOG(( "DeviceController : initWithDeviceReference, status = 0x%08lx\n", (UInt32)status ));
    #endif
	
	return self;
}

// awakeFromNib
//
//

- (void)awakeFromNib
{
	// sync buffer mode with UI
	[self changeTestMode:fTestModePopup];
	[self changePacketSize:fPacketSizePopup];
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
            
			[self logString:@"kIOMessageServiceIsTerminated (device removed)\n"];

			[fSelectorController removeObject:self];
        	
            break;
        
        case kIOMessageServiceIsSuspended:
		
            FWLOG(( "kIOMessageServiceIsSuspended bus reset start\n" ));
		
			[self logString:@"kIOMessageServiceIsSuspended bus reset start\n"];
	
			if( fInstantiated )
			{
            }
			
			break;
            
        case kIOMessageServiceIsResumed:
            
			FWLOG(( "kIOMessageServiceIsResumed bus reset complete\n" ));
		
			[self logString:@"kIOMessageServiceIsResumed bus reset complete\n"];
	
			if( fInstantiated )
            {
			}
			
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

// instantiateDeviceConnection
//
// load plugin and get important interfaces
//

- (void)instantiateDeviceConnection
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

#ifdef __LP64__
		[self logString:@"Running in 64 bit mode.\n"];
#else
		[self logString:@"Running in 32 bit mode.\n"];
#endif

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
			mach_port_t port = (*fFWDeviceInterface)->GetIsochAsyncPort( fFWDeviceInterface );
			NSLog( @"mach_port = 0x%08lx\n", port );
		}

		if( status == kIOReturnSuccess )
		{
			status = (*fFWDeviceInterface)->AddCallbackDispatcherToRunLoop( fFWDeviceInterface, CFRunLoopGetCurrent() );
		}
		
		if( status == kIOReturnSuccess )
		{
			mach_port_t port = (*fFWDeviceInterface)->GetIsochAsyncPort( fFWDeviceInterface );
			NSLog( @"mach_port 2 = 0x%08lx\n", port );
		}
	}
	
	if( status == kIOReturnSuccess )
	{
		status = [self readConfigDirectory];
	}
	
	if( status == kIOReturnSuccess )
	{
		status = [self createWriteBuffer];
	}
	
	if( status == kIOReturnSuccess )
	{
		status = [self createReadBuffer];
	}	
	
	//
	// activate window
	//
	
	[fWindow makeKeyAndOrderFront:self];

	#if __LP64__
		FWLOG(( "DeviceController : instantiateDeviceConnection, status = 0x%08x\n", (UInt32)status ));
	#else
		FWLOG(( "DeviceController : instantiateDeviceConnection, status = 0x%08lx\n", (UInt32)status ));
	#endif
}

// readConfigDirectory
//
//

- (IOReturn)readConfigDirectory
{
	IOReturn status = kIOReturnSuccess;
	
	IOFireWireLibConfigDirectoryRef unitDirectory;

	unitDirectory = (*fFWDeviceInterface)->GetConfigDirectory( fFWDeviceInterface, 
										CFUUIDGetUUIDBytes(kIOFireWireConfigDirectoryInterfaceID));
	if( unitDirectory == NULL )
	{
		status = kIOReturnError;
	}
	
	if( status == kIOReturnSuccess )
    {    
        status = (*unitDirectory)->GetKeyValue_UInt32( unitDirectory, 
                                                       kFWPageTableSizeKey, 
                                                       &fPageTableSize,
                                                       NULL);
    }

	if( status == kIOReturnSuccess )
    {    
        status = (*unitDirectory)->GetKeyValue_UInt32( unitDirectory, 
                                                       kFWBufferSizeKey, 
                                                       &fBufferSize,
                                                       NULL);
    }
	
	if( status == kIOReturnSuccess )
    {    
		[self logString:[NSString stringWithFormat:@"Remote buffer size = %ld\n", fBufferSize]];
        
		UInt32 address_lo;
        status = (*unitDirectory)->GetKeyValue_UInt32( unitDirectory, 
                                                       kFWAddressLoKey, 
                                                       &address_lo,
                                                       NULL);
        fPageTableAddress.addressLo = (0x00ffffff & address_lo);
    }
	
	if( status == kIOReturnSuccess )
    {    
        UInt32 address_hi;
        status = (*unitDirectory)->GetKeyValue_UInt32( unitDirectory, 
                                                       kFWAddressHiKey, 
                                                       &address_hi,
                                                       NULL);
        
		fPageTableAddress.addressLo |= (address_hi & 0x000000ff) << 24;
		fPageTableAddress.addressHi = address_hi >> 8;

		[self logString:[NSString stringWithFormat:@"Remote Page Table @ 0x%04lx.%08lx len %d\n", fPageTableAddress.addressHi, fPageTableAddress.addressLo, fPageTableSize]];

    }

	if( status == kIOReturnSuccess )
	{
		// create buffer for page table
		fPageTable = malloc( fPageTableSize );
		if( fPageTable == NULL )
			status = kIOReturnError;
	}
	
	if( status == kIOReturnSuccess )
	{
		// read page table
		UInt32 size = fPageTableSize;

		status = (*fFWDeviceInterface)->Read( fFWDeviceInterface, fDeviceReference, &fPageTableAddress, fPageTable, &size, false, 0 );
	}
	
	// swap the page table
	if( status == kIOReturnSuccess )
	{
		fPageTable->pte_count = EndianU32_BtoN( fPageTable->pte_count );
		
		[self logString:[NSString stringWithFormat:@"Remote PTE count = %ld\n", fPageTable->pte_count]];

		UInt32 i;
 		for( i = 0; i < fPageTable->pte_count; i++ )
		{
			fPageTable->ptes[i].address = EndianU64_BtoN( fPageTable->ptes[i].address );
			fPageTable->ptes[i].length = EndianU32_BtoN( fPageTable->ptes[i].length );
			
			UInt16 address_hi = (fPageTable->ptes[i].address >> 32) & 0x0000ffff;
			UInt32 address_lo = fPageTable->ptes[i].address & 0x00000000ffffffff;
			
			[self logString:[NSString stringWithFormat:@"Remote Buffer Segment %d @ 0x%04x.%08lx len %d\n", i, address_hi, address_lo, fPageTable->ptes[i].length]];
		}
	}
	
	if( status != kIOReturnSuccess )
	{
		[self logString:[NSString stringWithFormat:@"Error reading remote config directory 0x%08lx\n", status]];
	}
	
    //
    // cleanup
    //
    
    if( unitDirectory != NULL )
    {
        (*unitDirectory)->Release(unitDirectory);
		unitDirectory = NULL;
	} 
		
	return status;
}

// windowWillClose
//
//

- (void)windowWillClose:(NSNotification *)aNotification
{
	FWLOG(( "DeviceController : windowWillClose\n" ));
	fInstantiated = false;

	[fWriteCommandSet release];
	fWriteCommandSet = NULL;

	[fReadCommandSet release];
	fReadCommandSet = NULL;
	
  	if( fClientStarted )
	{
		[self stopClient];
	}

	[self destroyWriteBuffer];
	[self destroyReadBuffer];

	if( fPageTable != NULL )
	{
		free( fPageTable );
		fPageTable = NULL;
	}
	
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
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// logString:
//
//

- (void)logString:(NSString*)string
{
	if( fTextView )
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
}


//////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// changeTestMode:
//
//

- (IBAction)changeTestMode:(id)sender
{
	fTestMode = [[sender selectedItem] tag];
}

// changePacketSize:
//
//

- (IBAction)changePacketSize:(id)sender
{
	fPacketSize = [[sender selectedItem] tag];
}

// stringForRestMode:
//
//

- (NSString*)stringForTestMode:(UInt32)test_mode
{
	NSString * string = @"<Unknown Test Mode>";
	
	switch( test_mode )
	{
		case kTestModeWrite:
			string = @"Write";
			break;
		
		case kTestModeRead:
			string = @"Read";
			break;
		
		case kTestModeCompareSwap:
			string = @"Compare And Swap";
			break;
		
		case kTestModeVectorWrite:
			string = @"Vector Write";
			break;

		case kTestModeVectorRead:
			string = @"Vector Read";
			break;

		case kTestModePHYTransmit:
			string = @"PHY Transmit";
			break;

		case kTestModeVectorPHYTransmit:
			string = @"Vector PHY Transmit";
			break;
						
		default:
			NSLog( @"[DeviceController stringForTestMode] - illegal test mode = %d\n", test_mode );
	}
	
	return string;
}

/////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// startClient
//
//

- (IOReturn)startClient
{
	IOReturn status = kIOReturnSuccess;
	
	if( !fClientStarted )
	{	
		if( status == kIOReturnSuccess )
		{
			[fTestModePopup setEnabled:NO];
			[fPacketSizePopup setEnabled:NO];
		}
		
		switch( fTestMode )
		{
			case kTestModeWrite:
			case kTestModeRead:
			case kTestModePHYTransmit:
				{
					status = [self submitInitialCommandsType:fTestMode];
				}
				break;
						
			case kTestModeCompareSwap:
				{
					status = [self startCompareSwapTest];
				}
				break;
			
			case kTestModeVectorRead:
			case kTestModeVectorWrite:
			case kTestModeVectorPHYTransmit:
				{
					status = [self submitInitialVectorCommandsOfType:fTestMode];
				}
				break;
				
			default:
				NSLog( @"[DeviceController startClient] - illegal test mode = %d\n", fTestMode );
		}
		
		if( status == kIOReturnSuccess )
		{
			fClientStarted = YES;
			[fStartStopToggle setTitle:@"Stop"];
		}
		else
		{
			[self logString:[NSString stringWithFormat:@"Error 0x%08lx starting client\n", status]];
		}		
	}
	
	return status;
}

// stopClient
//
//

- (void)stopClient
{
	if( fClientStarted && !fStopRequested )
	{	
		fStopRequested = YES;
		[fStartStopToggle setEnabled:NO];
		
		if( fInflightCount == 0 )
		{
			[self stopComplete];
		}
	}
}

// stopComplete
//
//

- (void)stopComplete
{
	if( fClientStarted && fStopRequested )
	{
		fClientStarted = NO;
		fStopRequested = NO;
		[fStartStopToggle setEnabled:YES];
		[fStartStopToggle setTitle:@"Start"];
		[fTestModePopup setEnabled:YES];
		[fPacketSizePopup setEnabled:YES];

		[self logString:[NSString stringWithFormat:@"%@ Test Stopped.\n", [self stringForTestMode:fTestMode]]];
	}
}

// toggleAction:
//
//

- (IBAction)toggleAction:(id)sender
{
	if( fClientStarted )
	{
		[self stopClient];
	}
	else
	{
		[self startClient];
	}
}

// createWriteBuffer
//
//

- (IOReturn)createWriteBuffer
{
	IOReturn status = kIOReturnSuccess;

	fWriteBuffer = NULL;
	vm_allocate( mach_task_self(), (vm_address_t*)&fWriteBuffer, fBufferSize, true /*anywhere*/ );
	if( fWriteBuffer == NULL )
		status = kIOReturnError;

	// create ascending pattern
	if( status == kIOReturnSuccess )
	{
		UInt32 size = fBufferSize / sizeof(UInt32);
		UInt32 i;
		for( i = 0; i < size; i++ )
		{
			fWriteBuffer[i] = i;
		}
	}
	
	return status;
}

// destroyWriteBuffer
//
//

- (void)destroyWriteBuffer
{
	if( fWriteBuffer )
	{
		vm_deallocate( mach_task_self(), (vm_address_t)fWriteBuffer, fBufferSize );
		fWriteBuffer = NULL;
	}
}

// createReadBuffer
//
//

- (IOReturn)createReadBuffer
{
	IOReturn status = kIOReturnSuccess;

	fReadBuffer = NULL;
	vm_allocate( mach_task_self(), (vm_address_t*)&fReadBuffer, fBufferSize, true /*anywhere*/ );
	if( fReadBuffer == NULL )
		status = kIOReturnError;

	return status;
}

// destroyReadBuffer
//
//

- (void)destroyReadBuffer
{
	if( fReadBuffer )
	{
		vm_deallocate( mach_task_self(), (vm_address_t)fReadBuffer, fBufferSize );
		fReadBuffer = NULL;
	}
}

// completedCommand:withStatus:
//
//

- (void)completedCommand:(id)command withStatus:(IOReturn)completionStatus
{
//	[self logString:[NSString stringWithFormat:@"[DeviceController completeCommand:0x%08lx withStatus:0x%08lx]\n", command, completionStatus]];
	
	switch( fTestMode )
	{
		case kTestModeCompareSwap:
			{
				if( fStopRequested )
				{
					[self finishCompareSwap];
				}
				else
				{
					[self completeCompareSwap];
				}
			}
			break;
		
		case kTestModeRead:
		case kTestModeWrite:
		case kTestModePHYTransmit:
			{
				[self commandFinalize:command withStatus:completionStatus];
				
				if( fStopRequested )
				{
					[self finishCommand:command withStatus:completionStatus];
				}
				else
				{
					[self submitNextCommand:command type:fTestMode];
				}
			}
			break;

		case kTestModeVectorRead:
		case kTestModeVectorWrite:
		case kTestModeVectorPHYTransmit:
			{
				[self vectorCommandFinalize:command withStatus:completionStatus];
				
				if( fStopRequested )
				{
					[self finishVectorCommand:command withStatus:completionStatus];
				}
				else
				{
					[self submitNextVectorCommand:command type:fTestMode];
				}
			}
			break;
	
	
		default:
			NSLog( @"[DeviceController completedCommand:withStatus:] - illegal test mode = %d\n", fTestMode );
	}
}

//////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// startCompareSwapTest
//
//

- (IOReturn)startCompareSwapTest
{	
	IOReturn status = kIOReturnSuccess;
	
	FWAddress address;
	UInt64 address64 = fPageTable->ptes[0].address;
	address.addressHi = (address64 >> 32) & 0x0000ffff;
	address.addressLo = (address64 & 0x00000000ffffffff);
	
	UInt32 old_value = 0x12345678;
	UInt32 new_value = 0x13941394;
	
	// create a new command
	fCompareSwapCommand = [[FWCompareSwapCommand alloc] initWithDevice:fFWDeviceInterface 
													withAddress:&address 
													oldValue:old_value
													newValue:new_value
													withDelegate:self
													absolute:NO
													failOnReset:NO
													generation:0];
	
	fCompareSwapState = kCompareSwapStateInitialSubmit;

	[self logString:@"Compare Swap Test Started.\n"];

	[self logString:[NSString stringWithFormat:@"Submit initial compare swap. Old value = 0x%08lx New Value = 0x%08lx .\n", old_value, new_value]];
	
	status = [fCompareSwapCommand submit];
	
	return status;
}

// completeCompareSwap
//
//

- (void)completeCompareSwap
{
	switch( fCompareSwapState )
	{
		case kCompareSwapStateInitialSubmit:
			{
				// will probably fail
				UInt32 old_value = 0;
				[fCompareSwapCommand locked:&old_value];
				if( [fCompareSwapCommand didLock] )
				{
					// surprise! it worked
					[self logString:[NSString stringWithFormat:@"Intial compare swap succeeded!?. Old value = 0x%08lx\n", old_value]];
					
					// we're done
					[self finishCompareSwap];
				}
				else
				{
					[self logString:[NSString stringWithFormat:@"Intial compare swap failed. Old value = 0x%08lx\n", old_value]];
					
					UInt32 new_value = 0xdededede;
					
					[fCompareSwapCommand setOldValue:old_value newValue:new_value];
									
					fCompareSwapState = kCompareSwapStateSecondSubmit;
	
					[self logString:[NSString stringWithFormat:@"Submit secondary compare swap. Old value = 0x%08lx New Value = 0x%08lx .\n", old_value, new_value]];
				
					[fCompareSwapCommand submit];
				}
			}
			break;
			
		case kCompareSwapStateSecondSubmit:
			{
				// will probably fail
				UInt32 old_value = 0;
				[fCompareSwapCommand locked:&old_value];
				if( [fCompareSwapCommand didLock] )
				{
					// surprise! it worked
					[self logString:[NSString stringWithFormat:@"Second compare swap succeeded!. Old value = 0x%08lx\n", old_value]];
				}
				else
				{
					[self logString:[NSString stringWithFormat:@"Second compare swap failed. Old value = 0x%08lx\n", old_value]];
				}
				
				// either way we're done
				[self finishCompareSwap];
			}
			break;	
	
		default:
			NSLog( @"[DeviceController completeCompareSwap] - illegal state = %d\n", fCompareSwapState );
	}
}

// finishCompareSwap
//
//

- (void)finishCompareSwap
{
	[self logString:[NSString stringWithFormat:@"Compare Swap Test Complete.\n", fPacketSize]];

	[fCompareSwapCommand release];
	fCompareSwapCommand = NULL;
}

//////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// submitInitialCommandsType:
//
//

- (IOReturn)submitInitialCommandsType:(UInt32)type
{
	IOReturn status = kIOReturnSuccess;
	
	switch( type )
	{
		case kTestModeRead:
			[fReadCommandSet release];
			fReadCommandSet = NULL;
			
			fReadCommandSet = [[NSMutableSet setWithCapacity:2] retain];
			if( fReadCommandSet == nil )
			{
				status = kIOReturnError;
			}
			break;
			
		case kTestModeWrite:
		case kTestModePHYTransmit:
			[fWriteCommandSet release];
			fWriteCommandSet = NULL;
			
			fWriteCommandSet = [[NSMutableSet setWithCapacity:2] retain];
			if( fWriteCommandSet == nil )
			{
				status = kIOReturnError;
			}	
			break;
		
		default:
			NSLog( @"[DeviceController submitInitialCommandsType:] - illegal type = %d\n", type );
	}
	
	if( status == kIOReturnSuccess )
	{
		
		fPTE_index = 0;
		fPTE_offset = 0;
		fBuffer_offset = 0;
		fInflightCount = 0;
		fLastCommand = NULL;
		//fStartTime = 0;
		fTimeLoops = 0;
		fCommandsComplete = 0;
		
		int i;
		for( i = 0; i < kCommandCount; i++ )
		{
			BOOL done = [self submitNextCommand:NULL type:type];
			if( !done )
			{
				break;
			}
		}
	}

	[self logString:[NSString stringWithFormat:@"%@ Test Started. Command Size = %d\n", [self stringForTestMode:fTestMode], fPacketSize]];
	
	return status;
}

// submitNextCommand:type:
//
//

- (BOOL)submitNextCommand:(FWBlockCommand*)command type:(UInt32)type
{
	IOReturn status = kIOReturnSuccess;
	
	FWAddress address;
	UInt64 address64 = fPageTable->ptes[fPTE_index].address + fPTE_offset;
	address.addressHi = (address64 >> 32) & 0x0000ffff;
	address.addressLo = (address64 & 0x00000000ffffffff);
	
	UInt32 size = fPageTable->ptes[fPTE_index].length - fPTE_offset;
	if( size > fPacketSize )
		size = fPacketSize;

	switch( type )
	{
		case kTestModeRead:
			{
				void * buffer = (((UInt8*)fReadBuffer) + fBuffer_offset);
					
				if( command )
				{
					// reuse existing command
					[command setBuffer:buffer withSize:size];
					[command setTargetAddress:&address];
					[command setRetryCount:4];
				}
				else
				{
					// or create a new command
					command = [[FWReadCommand alloc] initWithDevice:fFWDeviceInterface 
													withAddress:&address 
													withBuffer:buffer
													withSize:size
													withDelegate:self
													absolute:NO
													failOnReset:NO
													generation:0];
					
					[fReadCommandSet addObject:command];
					[command setRetryCount:4];
					[command release];
				}
			}
			break;
			
		case kTestModeWrite:
			{
				void * buffer = (((UInt8*)fWriteBuffer) + fBuffer_offset);
				
				if( command )
				{
					[command setBuffer:buffer withSize:size];
					[command setTargetAddress:&address];
					[command setRetryCount:4];
				}
				else
				{
					command = [[FWWriteCommand alloc] initWithDevice:fFWDeviceInterface 
													withAddress:&address 
													withBuffer:buffer
													withSize:size
													withDelegate:self
													absolute:NO
													failOnReset:NO
													generation:0];
					
					[fWriteCommandSet addObject:command];
					[command setRetryCount:4];
					[command release];
				}
			}
			break;

		case kTestModePHYTransmit:
			{
				if( command )
				{
					[command setRetryCount:4];
					[(FWPHYCommand*)command setQuadsData1:0x40000000 data2:fBuffer_offset];
				}
				else
				{
					command = [[FWPHYCommand alloc] initWithDevice:fFWDeviceInterface 
													withData1:0x40000000
													withData2:fBuffer_offset
													withDelegate:self
													absolute:NO
													failOnReset:NO
													generation:0];
					
					[fWriteCommandSet addObject:command];
					[command setRetryCount:4];
					[command release];
				}
			}
			break;
				
		default:
			NSLog( @"[DeviceController submitNextCommand:type:] - illegal type = %d\n", type );
	}
	
	// get start time
	if( fBuffer_offset == 0 && fTimeLoops == 0 )
	{
		fStartTime = UpTime(); 
	}
	
	fInflightCount++;
	status = [command submit];
	if( status != kIOReturnSuccess )
	{
		NSLog( @"[submitNextCommand:type:] submit status = 0x%08lx\n", status );
	}
	
	fPTE_offset += size;
	fBuffer_offset += size;
	if( fBuffer_offset > fBufferSize )
	{
		NSLog( @"fBuffer_offset > fBufferSize\n" );
		return NO;
	}
	else if( fBuffer_offset == fBufferSize )
	{
		fBuffer_offset = 0;
		fLastCommand = command;
	}
	
	if( fPTE_offset > fPageTable->ptes[fPTE_index].length )
	{
		NSLog( @"Error : fPTE_offset > fPageTable->ptes[fPTE_index].length\n" );
		
		return NO;
	}
	else if( fPTE_offset == fPageTable->ptes[fPTE_index].length )
	{
		fPTE_offset = 0;
		fPTE_index++;
		if( fPTE_index >= fPageTable->pte_count )
		{
			fPTE_index= 0;
			
			if( fBuffer_offset != 0 )
			{
				NSLog( @"Error : fBuffer_offset != 0\n" );
			}
			
			return NO;
		}
	}
	
	return YES;
}

// commnadFinalize:withStatus:
//
//

- (void)commandFinalize:(FWBlockCommand*)command withStatus:(IOReturn)status
{
	fInflightCount--;
	
	fCommandsComplete++;
	
	if( fLastCommand == command )
	{
		fLastCommand = NULL;
		fTimeLoops++;
	}
	
	if( fTimeLoops == kTimeLoops )
	{
		AbsoluteTime end = UpTime();
		AbsoluteTime duration = SubAbsoluteFromAbsolute( end, fStartTime );
		Nanoseconds nanosec = AbsoluteToNanoseconds( duration );
		float seconds = (float) UnsignedWideToUInt64( nanosec ) / 1000000000.0;
		float megabytes = ((float)(fBufferSize * kTimeLoops)) / (1024.0 * 1024.0);
		float MBps = megabytes / seconds;
		float Cmdps = ((float)fCommandsComplete) / seconds;

		[self logString:@"---\n"];
		[self logString:[NSString stringWithFormat:@"%@ %.1f commands per second\n", [self stringForTestMode:fTestMode], Cmdps ]];
		[self logString:[NSString stringWithFormat:@"%@ %.3f MB per second\n", [self stringForTestMode:fTestMode], MBps ]];
		[self logString:[NSString stringWithFormat:@"%@ %d commands, %.3f MB, duration = %.3f s\n", [self stringForTestMode:fTestMode], fCommandsComplete, megabytes, seconds]];
		
		fTimeLoops = 0;
		fCommandsComplete = 0;
	}
}

// finishCommand:withStatus:
//
//

- (void)finishCommand:(FWBlockCommand*)command withStatus:(IOReturn)status
{
	if( fInflightCount == 0 )
	{
		[self stopComplete];
	}
}

#pragma mark -

//////////////////////////////////////////////////////////////////////////////////////////////////////
#pragma mark -

// submitInitialVectorCommandsOfType:
//
//

- (IOReturn)submitInitialVectorCommandsOfType:(UInt32)type
{
	IOReturn status = kIOReturnSuccess;

	[fVectorCommandArray release];
	fVectorCommandArray = NULL;
	
	fVectorCommandArray = [[NSMutableArray arrayWithCapacity:kVectorCommandCount] retain];
	if( fVectorCommandArray == nil )
	{
		status = kIOReturnError;
	}	
	
	if( status == kIOReturnSuccess )
	{
		
		fPTE_index = 0;
		fPTE_offset = 0;
		fBuffer_offset = 0;
		fInflightCount = 0;
		fLastCommand = NULL;
		fTimeLoops = 0;
		fCommandsComplete = 0;
		
		int i;
		for( i = 0; i < kVectorCommandCount; i++ )
		{
			FWVectorCommand * command = [[FWVectorCommand alloc] initWithDevice:fFWDeviceInterface];	
			[command setDelegate:self];
			[fVectorCommandArray addObject:command];
			
			// dummy buffer, address, and size during initialization
			FWAddress address;
			address.addressHi = 0;
			address.addressLo = 0;			
			void * buffer = (UInt8*)fReadBuffer;
			UInt32 size = fPacketSize;
			
			int j;
			for( j = 0; j < kVectorSubcommandCount; j++ )
			{
				if( type == kTestModeVectorWrite )
				{
					FWBlockCommand * sub_command = [[FWWriteCommand alloc] initWithDevice:fFWDeviceInterface 
														withAddress:&address 
														withBuffer:buffer
														withSize:size
														withDelegate:nil
														absolute:NO
														failOnReset:NO
														generation:0];
					
					[command addCommand:sub_command];
					
					[sub_command release];						
				}
				else if( type == kTestModeVectorRead )
				{
					FWBlockCommand * sub_command = [[FWReadCommand alloc] initWithDevice:fFWDeviceInterface 
														withAddress:&address 
														withBuffer:buffer
														withSize:size
														withDelegate:nil
														absolute:NO
														failOnReset:NO
														generation:0];
					
					[command addCommand:sub_command];
					
					[sub_command release];				
				}
				else if( type == kTestModeVectorPHYTransmit )
				{
					FWBlockCommand * sub_command = [[FWPHYCommand alloc] initWithDevice:fFWDeviceInterface 
														withData1:0x40000000
														withData2:0x00000000
														withDelegate:nil
														absolute:NO
														failOnReset:NO
														generation:0];
					
					[command addCommand:sub_command];
					
					[sub_command release];						
				}
			}
			
			[command release];
		}
		
		{
			int i;
			for( i = 0; i < kVectorCommandCount; i++ )
			{
				id command = [fVectorCommandArray objectAtIndex:i];
				[self submitNextVectorCommand:command type:type];
			}
		}
	}

	[self logString:[NSString stringWithFormat:@"%@ Test Started. Command Size = %d\n", [self stringForTestMode:fTestMode], fPacketSize]];
	
	return status;
}

// submitNextVectorCommand:type:
//
//

- (BOOL)submitNextVectorCommand:(id)vector_command type:(UInt32)type
{
	IOReturn status = kIOReturnSuccess;
	
	int i;
	for( i = 0; i < [vector_command getCommandCount]; i++ )
	{
		FWBlockCommand * sub_command = (FWBlockCommand*)[vector_command getCommandAtIndex:i];
		
		FWAddress address;
		UInt64 address64 = fPageTable->ptes[fPTE_index].address + fPTE_offset;
		address.addressHi = (address64 >> 32) & 0x0000ffff;
		address.addressLo = (address64 & 0x00000000ffffffff);
		
		UInt32 size = fPageTable->ptes[fPTE_index].length - fPTE_offset;
		if( size > fPacketSize )
			size = fPacketSize;
		
		if( (type == kTestModeVectorRead) || (type == kTestModeVectorWrite) )
		{
			void * buffer = nil;
			if( type == kTestModeVectorRead )
			{
				buffer = (((UInt8*)fReadBuffer) + fBuffer_offset);
			}
			else if( type == kTestModeVectorWrite )
			{
				buffer = (((UInt8*)fWriteBuffer) + fBuffer_offset);
			}
									
			if( buffer )
			{
				[sub_command setBuffer:buffer withSize:size];
				[sub_command setTargetAddress:&address];
				[sub_command setRetryCount:4];
			}
		}
		else if( type == kTestModeVectorPHYTransmit )
		{
			[(FWPHYCommand*)sub_command setQuadsData1:0x40000000 data2:fBuffer_offset]; 
		}
			
		// get start time
		if( fBuffer_offset == 0 && fTimeLoops == 0 )
		{
			fStartTime = UpTime(); 
		}
	
		fInflightCount++;
	
		fPTE_offset += size;
		fBuffer_offset += size;
		if( fBuffer_offset > fBufferSize )
		{
			NSLog( @"fBuffer_offset > fBufferSize\n" );
			return NO;
		}
		else if( fBuffer_offset == fBufferSize )
		{
			fBuffer_offset = 0;
			fLastCommand = sub_command;
		}
	
		if( fPTE_offset > fPageTable->ptes[fPTE_index].length )
		{
			NSLog( @"Error : fPTE_offset > fPageTable->ptes[fPTE_index].length\n" );
			
			return NO;
		}
		else if( fPTE_offset == fPageTable->ptes[fPTE_index].length )
		{
			fPTE_offset = 0;
			fPTE_index++;
			if( fPTE_index >= fPageTable->pte_count )
			{
				fPTE_index= 0;
				
				if( fBuffer_offset != 0 )
				{
					NSLog( @"Error : fBuffer_offset != 0\n" );
					return NO;
				}

			//	NSLog( @"Error : fPTE_offset == fPageTable->ptes[fPTE_index].length\n" );
				
			//	return NO;
			}
		}
	}
	
	if( status == kIOReturnSuccess )
	{
		status = [vector_command submit];
		if( status != kIOReturnSuccess )
		{
			NSLog( @"[submitNextCommand:type:] submit status = 0x%08lx\n", status );
		}
	}
	
	return YES;
}

// vectorCommandFinalize:withStatus:
//
//

- (void)vectorCommandFinalize:(id)vector_command withStatus:(IOReturn)status
{
	int i;
	for( i = 0; i < [vector_command getCommandCount]; i++ )
	{
		FWBlockCommand * sub_command = (FWBlockCommand*)[vector_command getCommandAtIndex:i];
		
		fInflightCount--;
		
		fCommandsComplete++;
		
		if( fLastCommand == sub_command )
		{
			fLastCommand = NULL;
			fTimeLoops++;
		//	NSLog( @"vectorCommandFinalize - timeLoops = %d\n", fTimeLoops );
		}
		
		if( fTimeLoops == kTimeLoops )
		{
			AbsoluteTime end = UpTime();
			AbsoluteTime duration = SubAbsoluteFromAbsolute( end, fStartTime );
			Nanoseconds nanosec = AbsoluteToNanoseconds( duration );
			float seconds = (float) UnsignedWideToUInt64( nanosec ) / 1000000000.0;
			float megabytes = ((float)(fBufferSize * kTimeLoops)) / (1024.0 * 1024.0);
			float MBps = megabytes / seconds;
			float Cmdps = ((float)fCommandsComplete) / seconds;

			[self logString:@"---\n"];
			[self logString:[NSString stringWithFormat:@"%@ %.1f commands per second\n", [self stringForTestMode:fTestMode], Cmdps ]];
			[self logString:[NSString stringWithFormat:@"%@ %.3f MB per second\n", [self stringForTestMode:fTestMode], MBps ]];
			[self logString:[NSString stringWithFormat:@"%@ %d commands, %.3f MB, duration = %.3f s\n", [self stringForTestMode:fTestMode], fCommandsComplete, megabytes, seconds]];
			
			fTimeLoops = 0;
			fCommandsComplete = 0;
		}
	}
}

// finishVectorCommand:withStatus:
//
//

- (void)finishVectorCommand:(id)command withStatus:(IOReturn)status
{
	if( fInflightCount == 0 )
	{
		[self stopComplete];
	}
}

@end