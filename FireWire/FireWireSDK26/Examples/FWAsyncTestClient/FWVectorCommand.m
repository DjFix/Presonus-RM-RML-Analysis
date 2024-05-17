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

#import "FWVectorCommand.h"

void FWVectorCommandCallback( void * refCon, IOReturn completionStatus )
{
    id	object = refCon;    
    [object commandCallback:completionStatus];
}

@interface FWVectorCommand (Private)
- (void)commandCallback:(IOReturn)completionStatus;
@end

@implementation FWVectorCommand

// initWithDevice
//
//

- (id)initWithDevice:(IOFireWireLibDeviceRef)device
{
	self = [super init];
	
	if( self )
	{
		IOFireWireLibVectorCommandRef interface;
		
		interface = (*device)->CreateVectorCommand( 
									device, 
									&FWVectorCommandCallback, 
									self, 
									CFUUIDGetUUIDBytes( kIOFireWireVectorCommandInterfaceID ) );
			
		_cmdRef = interface;
	}
	
	return self;
}

// dealloc
//
//

- (void)dealloc
{
	[self removeAllCommands];
		
	if( _cmdRef )
	{
		(*_cmdRef)->Release( _cmdRef );
		_cmdRef = NULL;
	}
	
	[super dealloc];
}

// submit
//
//

- (IOReturn)submit
{	
	return (*_cmdRef)->Submit( _cmdRef );
}

// isExecuting:
//
//

- (BOOL)isExecuting;
{
	return (*_cmdRef)->IsExecuting( _cmdRef );
}

// setRefCon:
//
//

- (void)setRefCon:(void*)refcon
{
	_refcon = refcon;
}

// getRefCon
//
//

- (void*)getRefCon
{
	return _refcon;
}

// setDelegate:
//
//

- (void)setDelegate:(id)delegate
{
	[delegate retain];
	[_delegate release];
	_delegate = delegate;
}

// setFlags:
//
//

- (void)setFlags:(UInt32)flags
{
	(*_cmdRef)->SetFlags( _cmdRef, flags );
}

// getFlags
//
//

- (UInt32)getFlags
{
	return (*_cmdRef)->GetFlags( _cmdRef );
}

// ensureCapacity:
//
//

- (IOReturn)ensureCapacity:(UInt32)capacity
{
	return (*_cmdRef)->EnsureCapacity( _cmdRef, capacity);
}

// addCommand:
//
//

- (void)addCommand:(FWCommand*)command
{
	[command retain];
	(*_cmdRef)->AddCommand( _cmdRef, [command getCmdRef] );
}

// removeCommand:
//
//

- (void)removeCommand:(FWCommand*)command
{
	(*_cmdRef)->RemoveCommand( _cmdRef, [command getCmdRef] );
	[command release];
}

// insertCommand:atIndex:
//
//

- (void)insertCommand:(FWCommand*)command atIndex:(UInt32)index
{
	[command retain];
	(*_cmdRef)->InsertCommandAtIndex( _cmdRef, [command getCmdRef], index );
}

// getCommandAtIndex:
//
//

- (FWCommand*)getCommandAtIndex:(UInt32)index
{
	IOFireWireLibCommandRef ref = (*_cmdRef)->GetCommandAtIndex( _cmdRef, index );
	return (*ref)->GetRefCon( ref );
}

// getIndexOfCommand:
//
//

- (UInt32)getIndexOfCommand:(FWCommand*)command
{
	return (*_cmdRef)->GetIndexOfCommand( _cmdRef, [command getCmdRef] );
}

// removeCommandAtIndex:
//
//

- (void)removeCommandAtIndex:(UInt32)index
{
	IOFireWireLibCommandRef ref = (*_cmdRef)->GetCommandAtIndex( _cmdRef, index );
	FWCommand * command = (*ref)->GetRefCon( ref );
	(*_cmdRef)->RemoveCommandAtIndex( _cmdRef, index );
	[command release];
}

// removeAllCommands
//
//

- (void)removeAllCommands
{
	while( [self getCommandCount] > 0 )
	{
		[self removeCommandAtIndex:0];
	}

//	(*_cmdRef)->RemoveAllCommands( _cmdRef );	
}

// getCommandCount
//
//

- (UInt32)getCommandCount
{
	return (*_cmdRef)->GetCommandCount( _cmdRef );
}

// commandCallback
//
//

- (void)commandCallback:(IOReturn)completionStatus
{
	[_delegate completedCommand:(id)self withStatus:completionStatus];
}

@end
