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
	
#import "FWCommand.h"

void FWCommandCallback( void * refCon, IOReturn completionStatus )
{
    id	object = refCon;    
    [object commandCallback:completionStatus];
}

@implementation FWCommand

// initWithInterface:
//
//

- (id)initWithInterface:(IOFireWireLibCommandRef)interface
{	
	self = [super init];
    
	_cmdRef = interface;
	
	return self;
}

// dealloc
//
//

- (void)dealloc
{
	if( _cmdRef )
	{
		(*_cmdRef)->Release( _cmdRef );
		_cmdRef = NULL;
	}
	
	[super dealloc];
}

// getCmdRef
//
//

- (IOFireWireLibCommandRef)getCmdRef
{
	return _cmdRef;
}

// getStatus
//
//

- (IOReturn)getStatus
{
	return (*_cmdRef)->GetStatus( _cmdRef );
}

// getTransferredBytes
//
//

- (UInt32)getTransferredBytes
{
	return (*_cmdRef)->GetTransferredBytes( _cmdRef );
}

// getTargetAddress:
//
//

- (void)getTargetAddress:(FWAddress*)addr
{
	return (*_cmdRef)->GetTargetAddress( _cmdRef, addr );
}

// setTargetAddress:
//
//
- (void)setTargetAddress:(FWAddress*)addr
{
	return (*_cmdRef)->SetTarget( _cmdRef, addr );
}

// setGeneration:
//
//

- (void)setGeneration:(UInt32)generation
{
	(*_cmdRef)->SetGeneration( _cmdRef, generation );
}

// isExecuting
//
//

- (BOOL)isExecuting
{
	return (*_cmdRef)->IsExecuting( _cmdRef );
}

// submit
//
//

- (IOReturn)submit
{
	return (*_cmdRef)->SubmitWithRefconAndCallback( _cmdRef, self, FWCommandCallback );
}

// setRetryCount:
//
//

- (void)setRetryCount:(UInt32)count
{
	(*_cmdRef)->SetMaxRetryCount( _cmdRef, count );
}

// cancel:
//
//

- (IOReturn)cancel:(IOReturn)reason
{
	return (*_cmdRef)->Cancel( _cmdRef, reason );	
}

// commandCallback:
//
//

- (void)commandCallback:(IOReturn)completionStatus
{
	if( _delegate )
		[_delegate completedCommand:(id)self withStatus:completionStatus];
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

@end
