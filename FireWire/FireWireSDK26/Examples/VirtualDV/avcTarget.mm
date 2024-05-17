/*
	File:		avcTarget.mm

 Synopsis: This is the source file for the avcTarget C++ object.

	Copyright: 	© Copyright 2001-2005 Apple Computer, Inc. All rights reserved.

	Written by: ayanowitz

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

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/firewire/IOFireWireLibIsoch.h>
#include <IOKit/avc/IOFireWireAVCLib.h>

#import "AVHDD.h"
#import "AVCTapeTgt.h"

#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#include "avcTarget.h"

#import "avcCommandVerboseLog.h"

#define VERBOSE_AVC 1

/////////////////////////////////////////////////////////
// Declaration of static member variables of this class
/////////////////////////////////////////////////////////
AVHDD *AVCTarget::avhddUI;
bool AVCTarget::transmitStarted;
bool AVCTarget::receiveStarted;

//////////////////////////////////////////////////////
// Constructor
//////////////////////////////////////////////////////
AVCTarget::AVCTarget(AVHDD *userInterface)
{
    nodeCFPlugInInterface = nil;
    nodeAVCCFPlugInInterface = nil;
    nodeNubInterface = nil;
    nodeAVCProtocolInterface = nil;
    transmitStarted = false;
	receiveStarted = false;

    avhddUI = userInterface;
}

//////////////////////////////////////////////////////
// Destructor
//////////////////////////////////////////////////////
AVCTarget::~AVCTarget(void)
{
	printf("AVCTarget Desctructor\n");

    // Cleanup these interfaces
    if (nodeAVCProtocolInterface)
    {
        (*nodeAVCProtocolInterface)->Release(nodeAVCProtocolInterface) ;
    }

    if (nodeNubInterface)
    {
        (*nodeNubInterface)->Close(nodeNubInterface) ;
        (*nodeNubInterface)->Release(nodeNubInterface) ;
    }

    if (nodeAVCCFPlugInInterface)
    {
        IODestroyPlugInInterface(nodeAVCCFPlugInInterface) ;
    }

    if (nodeCFPlugInInterface)
    {
        IODestroyPlugInInterface(nodeCFPlugInInterface) ;
    }
}

//////////////////////////////////////////////////////
// setupLocalNodeAVC
//////////////////////////////////////////////////////
IOReturn AVCTarget::setupLocalNodeAVC(void)
{
    // Local Vars
    IOReturn result = kIOReturnSuccess ;
    SInt32 theScore ;
    mach_port_t masterPort = 0 ;
    io_service_t theService = 0 ;
    io_iterator_t iterator	= 0 ;

    // Get the IO Kit master port
    result = IOMasterPort(MACH_PORT_NULL,&masterPort) ;
    if (result != kIOReturnSuccess)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"IOMasterPort Error: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Find the Local node in the IO registry
    result = IOServiceGetMatchingServices(masterPort,
                                          IOServiceMatching("IOFireWireLocalNode"),
                                          &iterator) ;

    // Make sure we found the local node
    if (!iterator)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"Unable to find local FireWire Node: 0x%08X\n",result]];
#endif
        return result ;
    }

    theService = IOIteratorNext(iterator) ;
    if (!theService)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"IOIteratorNext Error: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Add a user-interface plugin for the local node
    result = IOCreatePlugInInterfaceForService( theService,
                                                kIOFireWireLibTypeID, kIOCFPlugInInterfaceID,
                                                &nodeCFPlugInInterface, & theScore) ;
    if (result != kIOReturnSuccess)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"IOCreatePlugInInterfaceForService (kIOFireWireLibTypeID) Error: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Use the IUnknown interface to get the FireWireNub Interface
    // and return a pointer to it in the pointer passed into this function
    result = (*nodeCFPlugInInterface)->QueryInterface(nodeCFPlugInInterface,
                                                      CFUUIDGetUUIDBytes( kIOFireWireNubInterfaceID ),
                                                      (void**) &nodeNubInterface ) ;
    if ( result != S_OK )
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"Error querying for FireWire Nub Interface: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Add a user-interface plugin for the AVC Protocol (AVC Target services for the mac)
    result = IOCreatePlugInInterfaceForService( theService,
                                                kIOFireWireAVCLibProtocolTypeID, kIOCFPlugInInterfaceID,
                                                &nodeAVCCFPlugInInterface, & theScore) ;
    if (result != kIOReturnSuccess)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"IOCreatePlugInInterfaceForService (kIOFireWireAVCLibProtocolTypeID) Error: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Use the IUnknown interface to get the AVC Protocol Interface
    // and return a pointer to it in the pointer passed into this function
    result = (*nodeAVCCFPlugInInterface)->QueryInterface(nodeAVCCFPlugInInterface,
                                                         CFUUIDGetUUIDBytes( kIOFireWireAVCLibProtocolInterfaceID ),
                                                         (void**) &nodeAVCProtocolInterface ) ;
    if ( result != S_OK )
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"Error querying for AV/C Protocol Interface: 0x%08X\n",result]];
#endif
        return result ;
    }

    // Call Open for the nub interface
    result = (*nodeNubInterface)->Open( nodeNubInterface ) ;
    if (result != kIOReturnSuccess)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"Error opening firewire nub interface: 0x%08X\n",result]];
#endif
        return result ;
    }

	// Initialize the Tape Subunit
	result = AVCTapeTgtInit(nodeAVCProtocolInterface);
    if (result != kIOReturnSuccess)
    {
#ifdef VERBOSE_AVC
		[avhddUI addToAVCLog:[NSString stringWithFormat:@"Error initializing tape subunit: 0x%08X\n",result]];
#endif
        return result ;
    }
	
	// Add the callback dispatchers to the current thread's run loop
    (*nodeAVCProtocolInterface)->addCallbackDispatcherToRunLoop(nodeAVCProtocolInterface,CFRunLoopGetCurrent());
    (*nodeNubInterface)->AddCallbackDispatcherToRunLoop(nodeNubInterface,CFRunLoopGetCurrent());
	(*nodeNubInterface)->TurnOnNotification(nodeNubInterface);

    return result;
}


//////////////////////////////////////////////////////////
// publishConfigRom
//////////////////////////////////////////////////////////
IOReturn AVCTarget::publishConfigRom(void)
{
	return (*nodeAVCProtocolInterface)->publishAVCUnitDirectory(nodeAVCProtocolInterface);
}

