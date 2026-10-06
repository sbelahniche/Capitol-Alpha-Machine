#import "RefreshSchedule.h"
int main(void) {
    @autoreleasepool {
        NSCalendar *calendar = [NSCalendar calendarWithIdentifier:NSCalendarIdentifierGregorian];
        calendar.timeZone = [NSTimeZone timeZoneWithName:@"Europe/Berlin"];
        NSDateFormatter *format = [NSDateFormatter new];
        format.locale = [NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
        format.timeZone = calendar.timeZone;
        format.dateFormat = @"yyyy-MM-dd HH:mm:ss";
        NSArray *cases = @[
            @[@"2026-10-05 11:59:59", @"2026-09-28 12:00:00", @"2026-10-05 12:00:00"],
            @[@"2026-10-05 12:00:00", @"2026-10-05 12:00:00", @"2026-10-12 12:00:00"],
            @[@"2026-10-07 16:00:00", @"2026-10-05 12:00:00", @"2026-10-12 12:00:00"],
            @[@"2026-10-24 16:00:00", @"2026-10-19 12:00:00", @"2026-10-26 12:00:00"],
            @[@"2026-03-28 16:00:00", @"2026-03-23 12:00:00", @"2026-03-30 12:00:00"]
        ];
        for (NSArray *test in cases) {
            NSDate *now = [format dateFromString:test[0]];
            for (NSUInteger next = 0; next < 2; next++) {
                NSString *actual = [format stringFromDate:PolicyPublicationDate(now, calendar, next)];
                if (![actual isEqualToString:test[next + 1]]) {
                    NSLog(@"FAIL %@: got %@ expected %@", test[0], actual, test[next + 1]);
                    return 1;
                }
            }
        }
        NSLog(@"Passed 10 weekly scheduling checks, including exact noon and both DST transitions.");
    }
    return 0;
}
