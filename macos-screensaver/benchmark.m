// Visible WKWebView benchmark. Measures submitted scene work and RAF cadence;
// this is not a benchmark of the locked-screen ScreenSaverEngine host.
#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
@interface Benchmark : NSObject <WKNavigationDelegate>
@property NSWindow *window;
@property WKWebView *web;
@property NSString *snapshotPath;
@end
@implementation Benchmark
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation {
    [web evaluateJavaScript:@"window.samples=[];window.times=[];const originalFrame=frame;frame=function(t){const start=performance.now();originalFrame(t);samples.push(performance.now()-start);times.push(t);};" completionHandler:nil];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 12*NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        [web evaluateJavaScript:@"JSON.stringify((()=>{const s=samples.slice(60).sort((a,b)=>a-b),t=times.slice(60),d=t.slice(1).map((v,i)=>v-t[i]).sort((a,b)=>a-b);return {frames:t.length,fps:1000*(t.length-1)/(t.at(-1)-t[0]),submissionMedianMs:s[Math.floor(s.length*.5)],submissionP95Ms:s[Math.floor(s.length*.95)],intervalP95Ms:d[Math.floor(d.length*.95)],canvas:[cv.width,cv.height]};})())" completionHandler:^(id result,NSError *error){
            printf("%s\n",[(error ? error.description : result) UTF8String]);
            WKSnapshotConfiguration *config=[WKSnapshotConfiguration new];
            [web takeSnapshotWithConfiguration:config completionHandler:^(NSImage *image,NSError *snapshotError){
                if(image){NSBitmapImageRep *rep=[NSBitmapImageRep imageRepWithData:image.TIFFRepresentation];[[rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:self.snapshotPath atomically:YES];}
                [NSApp terminate:nil];
            }];
        }];
    });
}
@end
int main(int argc,const char **argv){@autoreleasepool{
    if(argc<4){fprintf(stderr,"usage: benchmark resources-directory snapshot.png scene-number [width height]\n");return 1;}
    [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    NSString *directory=@(argv[1]);
    NSString *html=[NSString stringWithContentsOfFile:[directory stringByAppendingPathComponent:@"scene.html"] encoding:NSUTF8StringEncoding error:nil];
    NSString *json=[NSString stringWithContentsOfFile:[directory stringByAppendingPathComponent:@"fallback.json"] encoding:NSUTF8StringEncoding error:nil];
    html=[html stringByReplacingOccurrencesOfString:[NSString stringWithFormat:@"window.__CAPITOL_TRADES_SCENE%s__",argv[3]] withString:[json stringByReplacingOccurrencesOfString:@"</" withString:@"<\\/"]];
    Benchmark *runner=[Benchmark new];runner.snapshotPath=@(argv[2]);
    NSRect rect=NSMakeRect(0,0,argc>4?atof(argv[4]):1512,argc>5?atof(argv[5]):982);
    runner.window=[[NSWindow alloc] initWithContentRect:rect styleMask:NSWindowStyleMaskBorderless backing:NSBackingStoreBuffered defer:NO];
    WKWebViewConfiguration *configuration=[WKWebViewConfiguration new];configuration.websiteDataStore=WKWebsiteDataStore.nonPersistentDataStore;
    runner.web=[[WKWebView alloc] initWithFrame:rect configuration:configuration];runner.web.navigationDelegate=runner;
    runner.window.contentView=runner.web;[runner.window orderFrontRegardless];
    [runner.web loadHTMLString:html baseURL:nil];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 30*NSEC_PER_SEC), dispatch_get_main_queue(), ^{fprintf(stderr,"Benchmark timed out\n");exit(2);});
    [NSApp run];
}return 0;}
