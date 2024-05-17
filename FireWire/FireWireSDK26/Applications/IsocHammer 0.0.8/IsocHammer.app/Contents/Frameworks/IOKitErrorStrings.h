//
//  IOKitErrorStrings.h
//   IsocHammer
//
//  Created by Russvogel on 6/4/07.
//  Copyright 2007 __MyCompanyName__. All rights reserved.
//

#import <Cocoa/Cocoa.h>

@interface IOKitErrorStrings : NSObject 
{
	NSMutableString *errorString;
}

- (NSString *) findErrorString:(IOReturn)code;


@end
