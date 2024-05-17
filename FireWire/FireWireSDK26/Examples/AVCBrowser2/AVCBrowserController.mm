/*
	File:		AVCBrowserController.mm
 
 Synopsis: This is the source file for the main application controller object 
 
	Copyright: 	¬© Copyright 2001-2005 Apple Computer, Inc. All rights reserved.
 
	Written by: ayanowitz
 
 Disclaimer:	IMPORTANT:  This Apple software is supplied to you by Apple Computer, Inc.
 ("Apple") in consideration of your agreement to the following terms, and your
 use, installation, modification or redistribution of this Apple software
 constitutes acceptance of these terms.  If you do not agree with these terms,
 please do not use, install, modify or redistribute this Apple software.
 
 In consideration of your agreement to abide by the following terms, and subject
 to these terms, Apple grants you a personal, non-exclusive license, under Apple‚Äôs
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


#include <AVCVideoServices/AVCVideoServices.h>
using namespace AVS;

#import "AVCBrowserController.h"
#import "AVCDeviceControlPanelController.h"

// AVCDeviceController, and AVCDevice callbacks
IOReturn MyAVCDeviceControllerNotification(AVCDeviceController *pAVCDeviceController, void *pRefCon, AVCDevice* pDevice);
IOReturn MyGlobalAVCDeviceMessageNotification (class AVCDevice *pAVCDevice,
										 natural_t messageType,
										 void * messageArgument,
										 void *pRefCon);

// AVCVideoServices based global objects
AVCDeviceController *pAVCDeviceController = nil;
UInt32 currentSelectedDeviceIndex = 0xFFFFFFFF;

@implementation AVCBrowserController


//////////////////////////////////////////////////////
// awakeFromNib
//////////////////////////////////////////////////////
- (void)awakeFromNib
{

	IOReturn err;
	
	// Create a AVCDeviceController
	err = CreateAVCDeviceController(&pAVCDeviceController,MyAVCDeviceControllerNotification, self,MyGlobalAVCDeviceMessageNotification);
	if (!pAVCDeviceController)
	{
		// TODO: This should never happen (unless we've run out of memory), but we should handle it cleanly anyway
	}
	
	[OpenControlPanelButton setEnabled:NO];
	
	[availableDevices setDoubleAction:@selector(OpenDeviceControlPanelButtonPushed:)];

}	

//////////////////////////////////////////////////////
// UpdateDeviceList
//////////////////////////////////////////////////////
- (void)UpdateDeviceList
{
	[availableDevices reloadData];
	[self tableViewSelectionDidChange: nil];
}

//////////////////////////////////////////////////////
// OpenDeviceControlPanelButtonPushed
//////////////////////////////////////////////////////
- (IBAction) OpenDeviceControlPanelButtonPushed:(id)sender
{
	AVCDeviceControlPanelController *pControlPanelController;
	
	if (currentSelectedDeviceIndex != 0xFFFFFFFF)
	{
		AVCDevice *pAVCDevice = (AVCDevice*) CFArrayGetValueAtIndex(pAVCDeviceController->avcDeviceArray,currentSelectedDeviceIndex);
		
		// Only create a control-panel for this device, if one doesn't exist already!
		pControlPanelController = (AVCDeviceControlPanelController*) pAVCDevice->GetClientPrivateData();
		if (!pControlPanelController)
		{
			pControlPanelController = [ [ AVCDeviceControlPanelController withDevice:pAVCDevice ] retain ] ;
			[NSBundle loadNibNamed:@"AVCDeviceControlPanel" owner:pControlPanelController ] ;	
		}
		else
		{
			[pControlPanelController WindowDeminiaturizeAndBringToFront];
		}
	}
}


//////////////////////////////////////////////////////
// TableView methods
//////////////////////////////////////////////////////
- (void)tableViewSelectionDidChange:(NSNotification *)notification
{
	AVCDevice *pAVCDevice;
	int row = [availableDevices selectedRow];
	
	// This function is called whenever the user clicks somewhere on the availableDevices table 
	
	if (row < 0)
	{
		if (CFArrayGetCount(pAVCDeviceController->avcDeviceArray) > 0)
		{	
			row = 0;
			[availableDevices selectRow:row byExtendingSelection:NO];
		}
		else
			return;
	}
	
	// A valid row is selected
	currentSelectedDeviceIndex = row;
	pAVCDevice = (AVCDevice*) CFArrayGetValueAtIndex(pAVCDeviceController->avcDeviceArray,row);
	if (!pAVCDevice)
		return;
	
	if (pAVCDevice->isAttached)
	{
		// This is a device we can capture from
		[OpenControlPanelButton setEnabled:YES];
	}
	else
	{
		// Not a device we can capture from
		[OpenControlPanelButton setEnabled:NO];
	}
}

- (int) numberOfRowsInTableView: (NSTableView*) aTableView
{
	if (pAVCDeviceController)
		return CFArrayGetCount(pAVCDeviceController->avcDeviceArray);
	else
		return 0;
}

- (id) tableView: (NSTableView*) aTableView
objectValueForTableColumn: (NSTableColumn*) aTableColumn
			 row: (int) rowIndex
{
	// Locals
	AVCDevice *pAVCDevice;
	NSString *identifier = [aTableColumn identifier];
	NSString *indexString = NULL;
	UInt8 *pSubunits;
	char subunitString[80];
	int i;
	bool prevFound;
	
	if ((aTableView == availableDevices) && (pAVCDeviceController))
	{
		pAVCDevice = (AVCDevice*) CFArrayGetValueAtIndex(pAVCDeviceController->avcDeviceArray,rowIndex);
		if (!pAVCDevice)
			return NULL;
		
		if ([identifier isEqualToString:@"MODEL"] == YES)
		{
			indexString = [NSString stringWithCString:pAVCDevice->deviceName];
		}
		else if ([identifier isEqualToString:@"VENDOR"] == YES)
		{
			indexString = [NSString stringWithCString:pAVCDevice->vendorName];
		}
		else if ([identifier isEqualToString:@"ATTACHED"] == YES)
		{
			indexString = [NSString stringWithFormat:@"%s",pAVCDevice->isAttached ? "Yes" : "No"];
		}
		else if ([identifier isEqualToString:@"FORMAT"] == YES)
		{
			if (pAVCDevice->capabilitiesDiscovered)
			{
				if (pAVCDevice->isDVDevice)
				{
					indexString = [NSString stringWithFormat:@"DV (0x%02X)",pAVCDevice->dvMode];
				}
				else if (pAVCDevice->isMPEGDevice)
				{
					indexString = [NSString stringWithFormat:@"MPEG2-TS (0x%02X)",pAVCDevice->mpegMode];
				}
				else
				{
					indexString = [NSString stringWithFormat:@"Other/Unknown"];
				}
			}
			else
			{
				indexString = [NSString stringWithFormat:@"Pending..."];
			}
		}
		else if ([identifier isEqualToString:@"SUBUNITS"] == YES)
		{
			if (pAVCDevice->capabilitiesDiscovered)
			{
				pSubunits =  (UInt8*) &pAVCDevice->subUnits;
				strcpy(subunitString,"");
				prevFound = false;
				
				for (i=0;i<4;i++)
				{
					if (pSubunits[i] != 0xFF)
					{
						if (prevFound)
							strcat(subunitString,", ");

						switch (((pSubunits[i] & 0xF8) >> 3))
						{
							case 0:
								strcat(subunitString,"Monitor");
								break;
							case 1:
								strcat(subunitString,"Audio");
								break;
							case 2:
								strcat(subunitString,"Printer");
								break;
							case 3:
								strcat(subunitString,"Disc");
								break;
							case 4:
								strcat(subunitString,"Tape");
								break;
							case 5:
								strcat(subunitString,"Tuner");
								break;
							case 6:
								strcat(subunitString,"CA");
								break;
							case 7:
								strcat(subunitString,"Camera");
								break;
							case 9:
								strcat(subunitString,"Panel");
								break;
							case 0xA:
								strcat(subunitString,"Bulletin-Board");
								break;
							case 0xB:
								strcat(subunitString,"Camera-Storage");
								break;
							case 0xC:
								strcat(subunitString,"Music");
								break;
							case 0x1C:
								strcat(subunitString,"Vendor-Unique");
								break;
							default:
								strcat(subunitString,"Unknown");
								break;
						};
						prevFound = true;
					}
				}
				indexString = [NSString stringWithCString:subunitString];
			}
			else
			{
				indexString = [NSString stringWithFormat:@"Pending..."];
			}
		}
	}
	
	return indexString;
}

- (void) tableView: (NSTableView*) aTableView
	setObjectValue: (id) anObject
	forTableColumn: (NSTableColumn*) aTableColumn
			   row: (int) rowIndex
{
	if (aTableView == availableDevices)
	{
		
	}
	else
	{
		
	}
}

@end

//////////////////////////////////////////////////////////////////////
//
// MyAVCDeviceControllerNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyAVCDeviceControllerNotification(AVCDeviceController *pAVCDeviceController, void *pRefCon, AVCDevice* pDevice)
{	
	AVCBrowserController *pController = (AVCBrowserController*) pRefCon;
	[pController performSelectorOnMainThread:@selector(UpdateDeviceList) withObject:pController waitUntilDone:NO];
	return kIOReturnSuccess;
}	

//////////////////////////////////////////////////////////////////////
//
// MyGlobalAVCDeviceMessageNotification
//
//////////////////////////////////////////////////////////////////////
IOReturn MyGlobalAVCDeviceMessageNotification (class AVCDevice *pAVCDevice,
										 natural_t messageType,
										 void * messageArgument,
										 void *pRefCon)
{
	AVCBrowserController *pController = (AVCBrowserController*) pRefCon;
	[pController performSelectorOnMainThread:@selector(UpdateDeviceList) withObject:pController waitUntilDone:NO];
	return kIOReturnSuccess;
}

