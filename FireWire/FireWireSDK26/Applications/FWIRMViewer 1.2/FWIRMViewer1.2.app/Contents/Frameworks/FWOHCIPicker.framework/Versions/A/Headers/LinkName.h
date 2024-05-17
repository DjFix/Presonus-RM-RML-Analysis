//
//  LinkName.h
//   FWAPITester
//
//  Created on 2/22/07.
//  Copyright 2007 Apple Inc. All rights reserved.
//

#import <Cocoa/Cocoa.h>


@interface LinkName : NSObject {

	NSString *	fNameString;
}

- (NSString *) nameFromVendor:(int)vendorID;

- (NSString *) nameFromVendor:(int)vendorID andDevice:(int)deviceID;

- (NSString *) phyVendorName:(int)vendorID;

@end
