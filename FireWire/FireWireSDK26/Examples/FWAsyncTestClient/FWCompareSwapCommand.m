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

#import "FWCompareSwapCommand.h"

@implementation FWCompareSwapCommand

// init
//
//

- (id)initWithDevice:(IOFireWireLibDeviceRef)device withAddress:(FWAddress*)addr oldValue:(UInt32)old_value newValue:(UInt32)new_value 
			withDelegate:(id)delegate absolute:(BOOL)abs failOnReset:(BOOL)failOnReset generation:(UInt32)generation;
{
	_interface = (IOFireWireLibCompareSwapCommandRef)(*device)->CreateCompareSwapCommand( 
								device, 
								abs ? 0 : (*device)->GetDevice( device ), 
								addr, 
								old_value, 
								new_value, 
								FWCommandCallback, 
								failOnReset, 
								generation, 
								self, 
								CFUUIDGetUUIDBytes( kIOFireWireCompareSwapCommandInterfaceID_v3 ) );
			
	[super initWithInterface:(IOFireWireLibCommandRef)_interface];
	
	[self setDelegate:delegate];
	
	return self;
}

// setOldValue:newValue:
//
//

- (void)setOldValue:(UInt32)old_value newValue:(UInt32)new_value
{
	(*_interface)->SetValues( _interface, old_value, new_value );
}

// setOldValue64:newValue:
//
//

- (void)setOldValue64:(UInt64)old_value newValue:(UInt64)new_value
{
	(*_interface)->SetValues64( _interface, old_value, new_value );
}

// didLock
//
//

- (BOOL)didLock
{
	return (*_interface)->DidLock( _interface );
}

// locked:
//
//

- (IOReturn)locked:(UInt32*)old_value;
{
	return (*_interface)->Locked( _interface, old_value );
}

// locked64:
//
//

- (IOReturn)locked64:(UInt64*)old_value;
{
	return (*_interface)->Locked64( _interface, old_value );
}

// setFlags:
//
//

// v2 compare swaps but setFlags in a different spot in the vtable 
// than the superclasses so we need to override setFlags here

- (void)setFlags:(UInt32)flags
{
	return (*_interface)->SetFlags( _interface, flags );
}
	
@end
