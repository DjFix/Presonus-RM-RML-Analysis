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

//
// Bus Reset Handler - FireWire Developer Sample Code.
// This file contains all the code needed to take action on each FireWire bus reset.
// The code makes one call to the viewHandler object to update the counter window.
// The code also receives a call to dealloc() from viewHandler.
// 

#import "resetHandler.h"
#import "viewHandler.h"

#ifndef kIOFWMessageTopologyChanged
#define kIOFWMessageTopologyChanged						(UInt32)iokit_fw_err(2002)
#endif


@implementation ResetHandler

io_object_t	notification;

// creates the interest notification and attaches it to the runloop
- (void)startResetWatch: (IOFireWireLibDeviceRef) localDevice
{
	IOReturn			result = kIOReturnSuccess;
	gNotificationPort = NULL;
	
	if (0 == ( gNotificationPort = IONotificationPortCreate( kIOMasterPortDefault ) )) {
		result = kIOReturnError;
	}
	
	io_object_t device = (*localDevice)->GetDevice(localDevice);

	// add the 'kIOGeneralInterest' to the notification port with the callback 'MyDeviceInterestCallback'
	result = IOServiceAddInterestNotification(gNotificationPort, device, kIOGeneralInterest, (IOServiceInterestCallback) MyDeviceInterestCallback, (void*) viewHandler /* obj-c refcon */, & notification);
	assert( result == kIOReturnSuccess );
	
	// add the 'general-firewire-interest-listening' runloop source to the current runloop so that we will be notified
	CFRunLoopSourceRef runLoopSource;
	runLoopSource = IONotificationPortGetRunLoopSource( gNotificationPort );
	CFRunLoopAddSource( CFRunLoopGetCurrent(), runLoopSource, kCFRunLoopDefaultMode );
}

// This function is used to remove the notification from the current runloop and destroy the notification port.
- (void)dealloc
{
	NSLog(@"applicationWillTerminate\n");
	
	CFRunLoopSourceRef runLoopSource;
	if(gNotificationPort) {
		// Gets the runloop with the notification.
		runLoopSource = IONotificationPortGetRunLoopSource( gNotificationPort );
		
		// Removes the source from the current runloop.
		CFRunLoopRemoveSource( CFRunLoopGetCurrent(), runLoopSource, kCFRunLoopDefaultMode );
		
		// Destroys the notification port used to receive general service notifications from the localnode.
		IONotificationPortDestroy(gNotificationPort) ;
	}
	
	[ super dealloc ] ;
}


@end

//This C function is used as the interest notification callback function.
//The refcon received here is the Objective-C object that was set during IOServiceAddInterestNotification.
void MyDeviceInterestCallback( void * refcon, io_service_t service, natural_t messageType, void * messageArgument )
{
	// The refcon is a function pointer to the objective-c object "viewHandler."
	// Setting it to an "id" type allows us to make the objective-c call below.
	//	id object = (id)refcon;
	
	NSLog(@"Service %x says: ", service);

	switch(messageType)
	{
		case kIOMessageServiceIsSuspended:
			// Handle bus reset begin here.
			
			// This is the sneaky part. An objective-C call in a plain C function. Magic.
			// object = the viewHandler object
			[(ViewHandler*)refcon updateCounter];
			
			NSLog(@"Bus Reset BEGIN (kIOMessageServiceIsSuspended)\n");
			break ;
		
		case kIOMessageServiceIsResumed:
			// Handle bus reset done
			NSLog(@"Bus Reset DONE (kIOMessageServiceIsResumed)\n");
			break ;

		case kIOFWMessageTopologyChanged:
			NSLog(@"kIOFWMessageTopologyChanged\n") ;
			break ;
			
		case kIOFWMessageServiceIsRequestingClose:
			NSLog(@"kIOFWMessageServiceIsRequestingClose\n") ;
			break ;
		default:
			NSLog(@"??? (0x%x)\n", messageType) ;
			break ;

	}

}
