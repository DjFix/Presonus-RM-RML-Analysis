//
//  IORegSearch.h
//  OHCIPicker
//
//  Created on 5/22/07.
//  Copyright 2007 Apple Inc. All rights reserved.
//

#import <Cocoa/Cocoa.h>
#import <IOKit/firewire/IOFireWireLib.h>
#import "LinkName.h"


@interface IORegSearch : NSObject 
{

	io_service_t services [10];
	
	NSMutableArray * fPciLinkEntries; // an array of NSMutableDictionary(s)
	NSMutableArray * fNames;

	int fEntryCount;
}

- (int) getTotalEntryCount;
- (NSArray *) getNameArray;
- (UInt16) getVendorIDAtIndex: (int) index;
- (UInt16) getDeviceIDAtIndex: (int) index;
- (NSString *) getRevisionIDAtIndex: (int) index;
- (NSString *) getNameAtIndex: (int) index;
- (UInt32) getBaseAddressAtIndex: (int) index;
- (UInt32) getIsochTransmitContextCountAtIndex: (int) index;

- (IOReturn) createIOFireWireLibDeviceRefAtIndex:(int)index returnDevice:(IOFireWireLibDeviceRef *)localNodeDevice;

@end
