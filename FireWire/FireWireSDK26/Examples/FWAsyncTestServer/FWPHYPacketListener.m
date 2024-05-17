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

#import "FWPHYPacketListener.h"

@interface FWPHYPacketListener (Private)

- (void)dataCallback:(FWClientCommandID)commandID data1:(UInt32)data1 data2:(UInt32)data2;
- (void)skippedCallback:(FWClientCommandID)commandID skippedPacketCount:(UInt32)count;

@end

void FWPHyRxDataCallback(
					IOFireWireLibPHYPacketListenerRef	listener,
					FWClientCommandID					commandID,
					UInt32								data1,
					UInt32								data2,
					void *								refCon )
{
    id	object = refCon;    
    [object dataCallback:commandID data1:data1 data2:data2];
}

void FWPHyRxSkippedCallback(
					IOFireWireLibPHYPacketListenerRef	listener,
					FWClientCommandID					commandID,
					UInt32								skippedPacketCount,
					void *								refCon )
{
    id	object = refCon;    
    [object skippedCallback:commandID skippedPacketCount:skippedPacketCount];
}

@implementation FWPHYPacketListener

// initWithDevice:queueCount:
//
//

- (id)initWithDevice:(IOFireWireLibDeviceRef)device queueCount:(UInt32)queue_count
{
	self = [super init];
	
	if( self )
	{
		_interface = (*device)->CreatePHYPacketListener( 
									device, 
									queue_count,
									CFUUIDGetUUIDBytes( kIOFireWirePHYPacketListenerInterfaceID ) );
									
		if( _interface )
		{
			(*_interface)->SetRefCon( _interface, self );
			(*_interface)->SetListenerCallback( _interface, &FWPHyRxDataCallback );
			(*_interface)->SetSkippedPacketCallback( _interface, &FWPHyRxSkippedCallback );
		}
	}
	
	return self;
}

// dealloc
//
//

- (void)dealloc
{
	if( _interface )
	{
		(*_interface)->Release( _interface );
		_interface = NULL;
	}
	
	[super dealloc];
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

// notificationIsOn
//
//

- (BOOL)notificationIsOn
{
	return (*_interface)->NotificationIsOn( _interface );
}

// turnOnNotification
//
//

- (IOReturn)turnOnNotification
{
	return (*_interface)->TurnOnNotification( _interface );
}

// turnOffNotification
//
//

- (void)turnOffNotification
{
	(*_interface)->TurnOffNotification( _interface );
}

// clientCommandIsComplete
//
//

- (void)clientCommandIsComplete:(FWClientCommandID)commandID;
{
	(*_interface)->ClientCommandIsComplete( _interface, commandID );
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

// setFlags:
//
//

- (void)setFlags:(UInt32)flags
{
	(*_interface)->SetFlags( _interface, flags );
}

// getFlags
//
//

- (UInt32)getFlags
{
	return (*_interface)->GetFlags( _interface );
}

// dataCallback
//
//

- (void)dataCallback:(FWClientCommandID)commandID data1:(UInt32)data1 data2:(UInt32)data2
{
	if ([_delegate respondsToSelector:@selector(PHYPacketDataCallback:commandID:data1:data2:)] ) 
	{
		[_delegate PHYPacketDataCallback:(id)self commandID:commandID data1:data1 data2:data2];
	}
}

// skippedCallback
//
//

- (void)skippedCallback:(FWClientCommandID)commandID skippedPacketCount:(UInt32)count
{
	if ([_delegate respondsToSelector:@selector(PHYPacketSkippedCallback:commandID:skippedPacketCount:)] ) 
	{
		[_delegate PHYPacketSkippedCallback:(id)self commandID:commandID skippedPacketCount:count];
	}
}

@end
