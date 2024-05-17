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
// This file contains the code needed for the Bus Reset Handler to display the bus reset count
// in a window. This file is uncessary in the general operation of the reset notification process.
// However, remember that the "MyDeviceInterestCallback" calls the "updateCounter" function below.
//

#import "viewHandler.h"
#import "resetHandler.h"

@interface ViewHandler (Private)

- (void) startCounting;

@end

@implementation ViewHandler

- (id)init
{
    [super init];
    return self;
}

// prepareOHCIMenu
//
//
- (int) prepareOHCIMenu
{
    NSArray * titles;
	int i, pciCount;
        
	// get array of all link names found.
    titles = [fIORegScanner getNameArray];
	
	// how many were there?
	pciCount = [fIORegScanner getTotalEntryCount];
    
	// build up the NSPopUpButton
    [menuOHCI removeAllItems];
    [menuOHCI addItemsWithTitles: titles];
    for (i = 0; i < pciCount; i++)
        [[menuOHCI itemAtIndex: i] setEnabled: YES];
        
	if( pciCount == 1 )
		[self startCounting];

    return i;
}


// pickOHCI
//
//
- (IBAction)pickOHCI:(id)sender
{
    NSString * currentHW;
    int newIndex;
	id selection;
    
	selection = [ menuOHCI selectedItem];
	newIndex = [menuOHCI indexOfItem:selection];

	if (newIndex != -1)
	{
		pciIndex = newIndex;
		currentHW = [menuOHCI itemTitleAtIndex: pciIndex];
		[self startCounting];
	}
	
}

// startCounting
//
//
- (void) startCounting
{
	IOReturn status = kIOReturnSuccess ;

	// OK now let's get IOFireWireFamily library device reference
	status = [fIORegScanner createIOFireWireLibDeviceRefAtIndex:pciIndex returnDevice:&fLocalNodeDevice];
	
	if (status == kIOReturnSuccess)
	{
		// and check to see if it answers
		Boolean	isInited = 	(*fLocalNodeDevice)->InterfaceIsInited(fLocalNodeDevice);
		if( isInited == YES)
		{
			[resetHandler startResetWatch: fLocalNodeDevice];
			[menuOHCI setEnabled:NO];
			[warningText setHidden:YES];
			[numberLabel setHidden:NO];
			[busResetText setHidden:NO];

		}
	}
}


// Tell resetHandler to do it's "thang."
// This function is automatically called by the application when the MainMenu nib is loaded.
- (void)awakeFromNib
{
	fIORegScanner = [[[IORegSearch alloc] init] retain];

    [numberLabel setIntValue:0];
    [theWindow makeKeyAndOrderFront:self];

	[warningText setHidden:NO];
	[numberLabel setHidden:YES];
	[busResetText setHidden:YES];
	[self prepareOHCIMenu];

}

// Callback used by "MyDeviceInterestCallback" in resetHandler to update interface.
- (void)updateCounter
{
    int i = [numberLabel intValue]+1;
    [numberLabel setIntValue:i];
}

// Tells resetHandler to kill it's notification runloop source and port.
// Since viewHandler is the application's delegate (set in Interface Builder),
// this function is automatically called when the application is normally terminating.
- (void)applicationWillTerminate:(NSNotification *)aNotification
{
	[fIORegScanner release];
    [resetHandler dealloc];
    [super dealloc];
}

@end
