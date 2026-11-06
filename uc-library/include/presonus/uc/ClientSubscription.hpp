#pragma once

#include "core/public/corestringbuffer.h"

namespace Presonus::UC {
// Partial application source port, not the native class layout or lifecycle.
// The three independent values correspond only to getter-observed native byte
// ranges +0x58 (app), +0x98 (device), and +0x118 (display), each 64 bytes.
// No original inheritance, ownership or ARM ABI is established. Constructor
// writes are recovered as portable values; string tails are not sanitized.
class ClientSubscription {
public:
  struct SourcePortValues {};
  // Portable scalar/state correspondences only. Native +4 is untouched and
  // deliberately has no invented initialized source-port field.
  explicit ClientSubscription(int identifier);
  int sourcePortIdentifier() const { return identifier_; }
  const Core::CStringBuffer<64> &sourcePortName() const { return name_; }
  const Core::CStringBuffer<64> &sourcePortIdentity() const {
    return identity_;
  }
  void sourcePortSetName(const Core::CStringBuffer<64> &v) { name_ = v.str(); }
  void sourcePortSetIdentity(const Core::CStringBuffer<64> &v) {
    identity_ = v.str();
  }
  void sourcePortSetApp(const Core::CStringBuffer<64> &v) { app_ = v.str(); }
  void sourcePortSetDevice(const Core::CStringBuffer<64> &v) {
    device_ = v.str();
  }
  void sourcePortSetDisplay(const Core::CStringBuffer<64> &v) {
    display_ = v.str();
  }
  const Core::CStringBuffer<64> &sourcePortSixth() const { return sixth_; }
  bool sourcePortInitialState() const {
    return word8_ == 0 && word12_ == 0 && byte16_ == 0 && word20_ == 0 &&
           sixth_.isEmpty();
  }
  explicit ClientSubscription(SourcePortValues,
                              const Core::CStringBuffer<64> &app,
                              const Core::CStringBuffer<64> &device,
                              const Core::CStringBuffer<64> &display)
      : ClientSubscription(0) {
    app_ = app;
    device_ = device;
    display_ = display;
  }
  const Core::CStringBuffer<64> &sourcePortApp() const { return app_; }
  const Core::CStringBuffer<64> &sourcePortDevice() const { return device_; }
  const Core::CStringBuffer<64> &sourcePortDisplay() const { return display_; }

private:
  int identifier_;
  unsigned word8_, word12_;
  unsigned char byte16_;
  unsigned word20_;
  Core::CStringBuffer<64> name_, identity_, sixth_;
  Core::CStringBuffer<64> app_;
  Core::CStringBuffer<64> device_;
  Core::CStringBuffer<64> display_;
};
} // namespace Presonus::UC
