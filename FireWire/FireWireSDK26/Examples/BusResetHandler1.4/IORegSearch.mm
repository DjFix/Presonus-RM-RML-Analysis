/*
	Disclaimer: IMPORTANT:  This Apple software is supplied to you by 
	Apple Inc. ("Apple") in consideration of your agreement to the
	following terms, and your use, installation, modification or
	redistribution of this Apple software constitutes acceptance of these
	terms.  If you do not agree with these terms, please do not use,
	install, modify or redistribute this Apple software.

	In consideration of your agreement to abide by the following terms, and
	subject to these terms, Apple grants you a personal, non-exclusive
	license, under Apple's copyrights in this original Apple software (the
	"Apple Software"), to use, reproduce, modify and redistribute the Apple
	Software, with or without modifications, in source and/or binary forms;
	provided that if you redistribute the Apple Software in its entirety and
	without modifications, you must retain this notice and the following
	text and disclaimers in all such redistributions of the Apple Software. 
	Neither the name, trademarks, service marks or logos of Apple Inc. 
	may be used to endorse or promote products derived from the Apple
	Software without specific prior written permission from Apple.  Except
	as expressly stated in this notice, no other rights or licenses, express
	or implied, are granted by Apple herein, including but not limited to
	any patent rights that may be infringed by your derivative works or by
	other works in which the Apple Software may be incorporated.

	The Apple Software is provided by Apple on an "AS IS" basis.  APPLE
	MAKES NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION
	THE IMPLIED WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS
	FOR A PARTICULAR PURPOSE, REGARDING THE APPLE SOFTWARE OR ITS USE AND
	OPERATION ALONE OR IN COMBINATION WITH YOUR PRODUCTS.

	IN NO EVENT SHALL APPLE BE LIABLE FOR ANY SPECIAL, INDIRECT, INCIDENTAL
	OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
	SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
	INTERRUPTION) ARISING IN ANY WAY OUT OF THE USE, REPRODUCTION,
	MODIFICATION AND/OR DISTRIBUTION OF THE APPLE SOFTWARE, HOWEVER CAUSED
	AND WHETHER UNDER THEORY OF CONTRACT, TORT (INCLUDING NEGLIGENCE),
	STRICT LIABILITY OR OTHERWISE, EVEN IF APPLE HAS BEEN ADVISED OF THE
	POSSIBILITY OF SUCH DAMAGE.

	Copyright (C) 2003-2007 Apple Inc. All Rights Reserved.
*/

#import "IORegSearch.h"

@interface IORegSearch (Private)

- (IOReturn) scanPCIDeviceCount;
- (IONotificationPortRef)getNotificationPort;
- (CFDictionaryRef)createMatchingDictionary;
- (void) buildDictionaryWithDevice:(io_object_t)device;

@end

@implementation IORegSearch

- (id) init
{
    IOReturn status = kIOReturnSuccess;

	if((self = [super init]) != nil)
	{
		fPciLinkEntries = [[NSMutableArray arrayWithCapacity:1] retain];
		fNames = [[NSMutableArray arrayWithCapacity:1] retain];
		status = [self scanPCIDeviceCount];
	}
	return self;
}

- (void) dealloc
{
	for( int i = 0; i < fEntryCount; i++)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:i ];
		[dict release];
	}
	[fPciLinkEntries release];
	[fNames release];
	[super dealloc];
}

- (IOReturn) scanPCIDeviceCount
{
    IOReturn status = kIOReturnSuccess;
    mach_port_t masterPort;
    io_iterator_t existing;
    io_registry_entry_t pciDevice = 0;
    CFDataRef prop;
    UInt16 vendorID, deviceID;
	char *revisionID;
	UInt32 baseAddress;
	UInt32 isocContexts;
	NSMutableDictionary *entryDictionary;

    fEntryCount = 0;

    if (status = :: IOMasterPort (MACH_PORT_NULL, &masterPort))
        NSLog (@"Error 0x%08x from IOMasterPort\n", status);

    if (status = :: IOServiceGetMatchingServices (masterPort, :: IOServiceMatching ("IOFireWireLocalNode"), &existing))
        NSLog (@"Error 0x%08x from IOServiceGetMatchingServices\n", status);
        
    while (services [fEntryCount] = :: IOIteratorNext (existing))
    {
	    prop = reinterpret_cast<CFDataRef>( IORegistryEntrySearchCFProperty( services [fEntryCount], kIOServicePlane, CFSTR("vendor-id"),
												kCFAllocatorDefault, kIORegistryIterateRecursively | kIORegistryIterateParents ));		
        vendorID = 0;
        if (prop)
        {
            vendorID = *(UInt32 *) :: CFDataGetBytePtr (prop);
           CFRelease (prop);
        }
            
	    prop = reinterpret_cast<CFDataRef>( IORegistryEntrySearchCFProperty( services [fEntryCount], kIOServicePlane, CFSTR("device-id"),
												kCFAllocatorDefault, kIORegistryIterateRecursively | kIORegistryIterateParents ));		
        deviceID = 0;
        if (prop)
        {
            deviceID = *(UInt32 *) :: CFDataGetBytePtr (prop);
            CFRelease (prop);
        }
        
	    prop = reinterpret_cast<CFDataRef>( IORegistryEntrySearchCFProperty( services [fEntryCount], kIOServicePlane, CFSTR("revision-id"),
												kCFAllocatorDefault, kIORegistryIterateRecursively | kIORegistryIterateParents ));		
        revisionID = 0;
        if (prop)
        {
            revisionID = (char *) :: CFDataGetBytePtr (prop);
            CFRelease (prop);
        }
		NSString *revString = [NSString stringWithCString:revisionID];
        
	    prop = reinterpret_cast<CFDataRef>( IORegistryEntrySearchCFProperty( services [fEntryCount], kIOServicePlane, CFSTR("assigned-addresses"),
												kCFAllocatorDefault, kIORegistryIterateRecursively | kIORegistryIterateParents ));		
        baseAddress = 0;
        if (prop)
        {
            // zzz how do I know this is big enough to dereference with [2]?
            
            baseAddress = ((UInt32 *) :: CFDataGetBytePtr (prop)) [2];		// Uni-N's base address is always here.
            CFRelease (prop);
        }
        
	    prop = reinterpret_cast<CFDataRef>( IORegistryEntrySearchCFProperty( services [fEntryCount], kIOServicePlane, CFSTR("IsochTransmitContextCount"),
												kCFAllocatorDefault, kIORegistryIterateRecursively | kIORegistryIterateParents ));		
        isocContexts = 4;
        if (prop)
        {
			if (prop && CFGetTypeID(prop) == CFNumberGetTypeID())
			{
				CFNumberGetValue( (CFNumberRef)prop, kCFNumberSInt32Type, &isocContexts );
			}
			CFRelease (prop);
		}
        
		NSString *linkNameString = [NSString stringWithFormat: @"FireWire Bus#%d", fEntryCount+1];

		entryDictionary = [[NSMutableDictionary dictionaryWithCapacity:1] retain];
		[entryDictionary setObject:linkNameString forKey:@"Name"];
		[entryDictionary setObject:[NSNumber numberWithUnsignedInt:vendorID]	forKey:@"VendorID"];
		[entryDictionary setObject:[NSNumber numberWithUnsignedInt:deviceID] forKey:@"DeviceID"];
		[entryDictionary setObject:revString	forKey:@"RevisionID"];
		[entryDictionary setObject:[NSNumber numberWithUnsignedLong:baseAddress]	forKey:@"BaseAddress"];
		[entryDictionary setObject:[NSNumber numberWithUnsignedLong:isocContexts]	forKey:@"IsochTransmitContextCount"];
 
		// store each dictionary in an array element
		[fPciLinkEntries addObject:entryDictionary];

		// create an array for Link Names
		[fNames addObject:linkNameString];
		
		fEntryCount++;

        if (pciDevice && (status = IOObjectRelease (pciDevice)))
            NSLog (@"Error 0x%08x from IOObjectRelease pciDevice (Glue :: listInterfaces)\n", status);
		
    }
    
    if (status = IOObjectRelease (existing))
        NSLog (@"Error 0x%08x from IOObjectRelease existing (Glue :: listInterfaces)\n", status);

    if (status = IOObjectRelease (masterPort))
        NSLog (@"Error 0x%08x from IOObjectRelease masterPort (Glue :: listInterfaces)\n", status);

	return status;
}

- (int) getTotalEntryCount
{
	return fEntryCount;
}

- (NSArray *) getNameArray
{
	return fNames;
}

- (UInt16) getVendorIDAtIndex: (int) index
{
	UInt16 value = 0xFFFF;
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		NSNumber *number = [dict valueForKey:@"VendorID"];
		value = [number unsignedIntValue];
	}
	return value;
}

- (UInt16) getDeviceIDAtIndex: (int) index
{
	UInt16 value = 0xFFFF;
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		NSNumber *number = [dict valueForKey:@"DeviceID"];
		value = [number unsignedIntValue];
	}
	return value;
}

- (NSString *) getRevisionIDAtIndex: (int) index
{
	NSString *rev = @"??";
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		rev = [dict valueForKey:@"RevisionID"];
	}
	return rev;
}

- (NSString *) getNameAtIndex: (int) index
{
	NSString *name = @"??";
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		name = [dict valueForKey:@"Name"];
	}
	return name;
}

- (UInt32) getBaseAddressAtIndex: (int) index
{
	UInt32 value = 0xFFFFFFFF;
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		NSNumber *number = [dict valueForKey:@"BaseAddress"];
		value = [number unsignedLongValue];
	}
	return value;
}

- (UInt32) getIsochTransmitContextCountAtIndex: (int) index
{
	UInt32 value = 0;
	if( index < fEntryCount)
	{
		NSDictionary *dict = [fPciLinkEntries objectAtIndex:index];
		NSNumber *number = [dict valueForKey:@"IsochTransmitContextCount"];
		value = [number unsignedLongValue];
	}
	return value;
}
- (io_service_t) getIOServiceAtIndex:(int)index
{
	io_service_t thisService = nil;
	if( index < fEntryCount && index < 10)
	{
		thisService = services[index];
	}
	return thisService;
}

- (IOReturn) createIOFireWireLibDeviceRefAtIndex:(int)index returnDevice:(IOFireWireLibDeviceRef *)localNodeDevice
{
	IOReturn status = kIOReturnSuccess ;
    io_service_t theService = 0 ;
    SInt32 theScore ;
    IOCFPlugInInterface **nodeCFPlugInInterface;
    IOFireWireLibNubRef nodeNubInterface;
	
	if( index >= fEntryCount)
		status = kIOReturnError;

	// Add a user-interface plugin for the local node
	if (status == kIOReturnSuccess)
	{
		theService = services[index];
		status = IOCreatePlugInInterfaceForService( theService,
													kIOFireWireLibTypeID, kIOCFPlugInInterfaceID,
													&nodeCFPlugInInterface, & theScore) ;
	}
	
	// Use the IUnknown interface to get the FireWireNub Interface
	// and return a pointer to it in the pointer passed into this function
	if (status == kIOReturnSuccess)
		status = (*nodeCFPlugInInterface)->QueryInterface(nodeCFPlugInInterface,
														  CFUUIDGetUUIDBytes( kIOFireWireNubInterfaceID ),
														  (void**) &nodeNubInterface ) ;
	// Destroy the nodeCFPlugInInterface
	if ( status == S_OK )
		if (nodeCFPlugInInterface)
			IODestroyPlugInInterface(nodeCFPlugInInterface) ;

	// Return a pointer to the newly created interface
	if (nodeNubInterface)
		*localNodeDevice = nodeNubInterface;
		
	return status;
}

@end
