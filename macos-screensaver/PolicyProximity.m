#import <ScreenSaver/ScreenSaver.h>
#import <WebKit/WebKit.h>
#import "RefreshSchedule.h"

@interface WKWebView (PolicyCompatibility)
- (void)_setWindowOcclusionDetectionEnabled:(BOOL)enabled;
@end

#ifndef SAVER_VIEW
#define SAVER_VIEW PolicyProximityView
#endif

static BOOL CapitolValidJSON(NSString *json, NSArray<NSString *> *requiredArrays) {
    if (!json) return NO;
    NSDictionary *payload = [NSJSONSerialization JSONObjectWithData:[json dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];
    if (![payload isKindOfClass:NSDictionary.class] || !requiredArrays.count) return NO;
    for (NSString *key in requiredArrays) {
        if (![payload[key] isKindOfClass:NSArray.class] || [payload[key] count] == 0) return NO;
    }
    return YES;
}

@interface SAVER_VIEW : ScreenSaverView
@property WKWebView *web;
@property NSTimer *refreshTimer;
@property NSURLSessionDataTask *download;
@property NSString *currentJSON;
@property NSString *sceneHTML;
@property NSUInteger runGeneration;
@property NSString *preferencesModule;
@property NSString *dataPlaceholder;
@property NSString *dataPrefix;
@property NSArray<NSString *> *requiredArrays;
@end

@implementation SAVER_VIEW
- (instancetype)initWithFrame:(NSRect)frame isPreview:(BOOL)preview {
    self = [super initWithFrame:frame isPreview:preview];
    if (self) {
        self.animationTimeInterval = 1.0;
        self.wantsLayer = YES;
        self.layer.backgroundColor = NSColor.blackColor.CGColor;
        NSBundle *bundle = [NSBundle bundleForClass:self.class];
        self.preferencesModule = bundle.bundleIdentifier;
        NSString *scene = [bundle objectForInfoDictionaryKey:@"CapitolScene"];
        self.dataPlaceholder = [NSString stringWithFormat:@"window.__CAPITOL_TRADES_%@__", scene];
        self.dataPrefix = [NSString stringWithFormat:@"window.CAPITOL_TRADES_%@=", scene];
        self.requiredArrays = [bundle objectForInfoDictionaryKey:@"CapitolRequiredArrays"];
        self.sceneHTML = [NSString stringWithContentsOfURL:[bundle URLForResource:@"scene" withExtension:@"html"] encoding:NSUTF8StringEncoding error:nil];
    }
    return self;
}
- (BOOL)validJSON:(NSString *)json {
    return CapitolValidJSON(json, self.requiredArrays);
}
- (void)displayValidatedJSON:(NSString *)json {
    if ([json isEqualToString:self.currentJSON]) return;
    self.currentJSON = json;
    // Escape HTML end tags inside data before embedding in the trusted scene.
    NSString *safeJSON = [json stringByReplacingOccurrencesOfString:@"</" withString:@"<\\/"];
    NSString *html = [self.sceneHTML stringByReplacingOccurrencesOfString:self.dataPlaceholder withString:safeJSON];
    [self.web loadHTMLString:html baseURL:nil];
}
- (void)startAnimation {
    [super startAnimation];
    if (self.web) return;
    self.runGeneration++;
    WKWebViewConfiguration *config = [WKWebViewConfiguration new];
    config.websiteDataStore = WKWebsiteDataStore.nonPersistentDataStore;
    self.web = [[WKWebView alloc] initWithFrame:self.bounds configuration:config];
    self.web.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    // macOS 14+ may mark the screensaver's web view as occluded, pausing canvas.
    if ([self.web respondsToSelector:@selector(_setWindowOcclusionDetectionEnabled:)]) {
        [self.web _setWindowOcclusionDetectionEnabled:NO];
    }
    [self addSubview:self.web];
    self.currentJSON = nil;
    NSUserDefaults *prefs = [ScreenSaverDefaults defaultsForModuleWithName:self.preferencesModule];
    NSString *json = [prefs stringForKey:@"lastGoodDataset"];
    if (![self validJSON:json]) {
        json = [NSString stringWithContentsOfURL:[[NSBundle bundleForClass:self.class] URLForResource:@"fallback" withExtension:@"json"] encoding:NSUTF8StringEncoding error:nil];
        if (![self validJSON:json]) return;
    }
    [self displayValidatedJSON:json];
    if (!self.isPreview) {
        [self checkWeeklyUpdate];
        [[NSDistributedNotificationCenter defaultCenter] addObserver:self selector:@selector(saverWillStop:) name:@"com.apple.screensaver.willstop" object:nil];
    }
}
- (void)checkWeeklyUpdate {
    [self.refreshTimer invalidate];
    NSDate *now = [NSDate date];
    NSCalendar *calendar = [NSCalendar calendarWithIdentifier:NSCalendarIdentifierGregorian];
    calendar.timeZone = NSTimeZone.localTimeZone;
    NSDate *due = PolicyPublicationDate(now, calendar, NO);
    NSDate *next = PolicyPublicationDate(now, calendar, YES);
    self.refreshTimer = [[NSTimer alloc] initWithFireDate:next interval:0 target:self selector:@selector(checkWeeklyUpdate) userInfo:nil repeats:NO];
    [[NSRunLoop mainRunLoop] addTimer:self.refreshTimer forMode:NSRunLoopCommonModes];
    NSUserDefaults *prefs = [ScreenSaverDefaults defaultsForModuleWithName:self.preferencesModule];
    NSDate *lastSuccess = [prefs objectForKey:@"lastSuccessfulPublication"];
    if (![lastSuccess isKindOfClass:NSDate.class] || [lastSuccess compare:due] == NSOrderedAscending) {
        [self refreshDataForPublication:due];
    }
}
- (void)refreshDataForPublication:(NSDate *)publication {
    if (self.download) return;
    NSURL *url = [NSURL URLWithString:@"https://capitolalpha.app/capitoltrades_data.js"];
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url cachePolicy:NSURLRequestReloadIgnoringLocalCacheData timeoutInterval:30];
    [request setValue:@"no-cache" forHTTPHeaderField:@"Cache-Control"];
    NSString *prefix = self.dataPrefix;
    NSArray<NSString *> *requiredArrays = self.requiredArrays;
    NSUInteger generation = self.runGeneration;
    __weak SAVER_VIEW *weakSelf = self;
    self.download = [NSURLSession.sharedSession dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
        __block NSString *json = nil;
        if (!error && [(NSHTTPURLResponse *)response statusCode] == 200 && data.length < 20 * 1024 * 1024) {
            NSString *js = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
            [js enumerateLinesUsingBlock:^(NSString *line, BOOL *stop) {
                if (![line hasPrefix:prefix]) return;
                json = [[line substringFromIndex:prefix.length] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
                if ([json hasSuffix:@";"]) json = [json substringToIndex:json.length - 1];
                *stop = YES;
            }];
        }
        // Parse the downloaded payload on the URL session's background queue.
        // The main queue only saves validated data and swaps the web document.
        if (!CapitolValidJSON(json, requiredArrays)) json = nil;
        dispatch_async(dispatch_get_main_queue(), ^{
            SAVER_VIEW *view = weakSelf;
            if (!view || !view.web || view.runGeneration != generation) return;
            view.download = nil;
            if (!json) return;
            NSUserDefaults *prefs = [ScreenSaverDefaults defaultsForModuleWithName:view.preferencesModule];
            if (![json isEqualToString:view.currentJSON]) [prefs setObject:json forKey:@"lastGoodDataset"];
            [prefs setObject:publication forKey:@"lastSuccessfulPublication"];
            [prefs synchronize];
            [view displayValidatedJSON:json];
        });
    }];
    [self.download resume];
}
- (void)saverWillStop:(NSNotification *)notification { [self stopAnimation]; }
- (void)stopAnimation {
    [super stopAnimation];
    self.runGeneration++;
    [self.refreshTimer invalidate];
    self.refreshTimer = nil;
    [self.download cancel];
    self.download = nil;
    [self.web stopLoading];
    [self.web removeFromSuperview];
    self.web = nil;
    self.currentJSON = nil;
    [[NSDistributedNotificationCenter defaultCenter] removeObserver:self];
}
- (NSView *)hitTest:(NSPoint)point { return self; }
- (BOOL)acceptsFirstResponder { return NO; }
- (BOOL)hasConfigureSheet { return NO; }
@end
