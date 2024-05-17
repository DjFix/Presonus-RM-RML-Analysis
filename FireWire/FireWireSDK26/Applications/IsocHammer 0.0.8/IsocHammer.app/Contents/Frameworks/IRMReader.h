//
//  IRMReader.h
//   IsocHammer
//
//  Created by Russvogel on 5/29/07.
//  Copyright 2007 Apple Inc. All rights reserved.
//

#import <Cocoa/Cocoa.h>
#include <IOKit/firewire/IOFireWireLib.h>
#import "resetHandler.h"


@interface IRMReader : NSObject <ResetHandlerProtocol>
{
	UInt32 newBandwidth, oldBandwidth;
	UnsignedWide newChannels;
	IOFWSpeed fMaxSpeed; 

	IOFireWireLibDeviceRef fwLib;
	UInt16 theIRM, theLocalNode;

	IOCFPlugInInterface ** cfPlugInInterfaceFW;
	
	ResetHandler *fResetHandler;
}

- (id) initWithDevice:(IOFireWireLibDeviceRef)device;
- (IOReturn) readIRMRegisters;
- (UnsignedWide *) getAllocatedChannels;
- (UInt32) getRemainingBandwidth;
- (UInt32) getAllocatedBandwidth;
- (SInt32) getChangedBandwidth;
- (IOFWSpeed) getMaxSpeed;

- (void)logTheReset;


@end
