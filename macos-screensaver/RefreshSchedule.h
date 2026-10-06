#import <Foundation/Foundation.h>

// Calendar arithmetic preserves Monday noon across daylight-saving changes.
static NSDate *PolicyPublicationDate(NSDate *now, NSCalendar *calendar, BOOL next) {
    NSDateComponents *components = [NSDateComponents new];
    components.weekday = 2; // Monday, using Foundation's Sunday-based numbering.
    components.hour = 12;
    components.minute = 0;
    components.second = 0;
    NSCalendarOptions options = NSCalendarMatchNextTime;
    if (!next) options |= NSCalendarSearchBackwards;
    return [calendar nextDateAfterDate:next ? now : [now dateByAddingTimeInterval:1]
                    matchingComponents:components options:options];
}
