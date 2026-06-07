// ARC Mobile Runtime — React Native TurboModule iOS implementation (simulator preview).
//
// SIMULATOR PREVIEW: returns fixture data only. No real camera, microphone, contacts,
// calendar, photos, location, files, health, or OS permission requests. All sensitive OS
// APIs are forbidden in this file (enforced by the recursive forbidden-symbol CI gate).

#import <Foundation/Foundation.h>
#import <React/RCTBridgeModule.h>

@interface ArcMobileRuntime : NSObject <RCTBridgeModule>
@end

@implementation ArcMobileRuntime

RCT_EXPORT_MODULE(ArcMobileRuntime)

// Deterministic fixtures — never touches real device state.
- (NSDictionary *)mockOutputs:(NSString *)capabilityId {
  if ([capabilityId hasPrefix:@"device.location"]) {
    return @{@"latitude": @37.7749, @"longitude": @(-122.4194), @"mock": @YES};
  }
  if ([capabilityId hasPrefix:@"device.camera"]) {
    return @{@"uri": @"fixture://mock-image.jpg", @"mock": @YES};
  }
  return @{@"mock": @YES, @"capability_id": capabilityId};
}

RCT_EXPORT_METHOD(simulateAction:(NSString *)capabilityId
                  inputs:(NSDictionary *)inputs
                  resolve:(RCTPromiseResolveBlock)resolve
                  reject:(RCTPromiseRejectBlock)reject) {
  resolve(@{@"simulated": @YES, @"capability_id": capabilityId, @"mock": @YES,
            @"outputs": [self mockOutputs:capabilityId]});
}

RCT_EXPORT_METHOD(doctor:(RCTPromiseResolveBlock)resolve reject:(RCTPromiseRejectBlock)reject) {
  resolve(@{@"ok": @YES, @"runtime_mode": @"simulator", @"mock_mode": @YES,
            @"capability_count": @13, @"note": @"Simulator preview — no real native bridges."});
}

RCT_EXPORT_METHOD(getPermissionState:(NSString *)capabilityId
                  resolve:(RCTPromiseResolveBlock)resolve
                  reject:(RCTPromiseRejectBlock)reject) {
  // Mock only — never requests real OS permissions.
  resolve(@{@"status": @"not_requested", @"mock": @YES});
}

@end
