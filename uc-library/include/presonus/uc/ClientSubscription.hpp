#pragma once

#include "core/public/corestringbuffer.h"

namespace Presonus::UC {
// Partial application source port, not the native class layout or lifecycle.
// The three independent values correspond only to getter-observed native byte
// ranges +0x58 (app), +0x98 (device), and +0x118 (display), each 64 bytes.
// No original constructor, inheritance, ownership or ARM ABI is established.
class ClientSubscription {
public:
  struct SourcePortValues {};
  explicit ClientSubscription(SourcePortValues,
                              const Core::CStringBuffer<64> &app,
                              const Core::CStringBuffer<64> &device,
                              const Core::CStringBuffer<64> &display)
      : app_(app), device_(device), display_(display) {}
  const Core::CStringBuffer<64> &sourcePortApp() const { return app_; }
  const Core::CStringBuffer<64> &sourcePortDevice() const { return device_; }
  const Core::CStringBuffer<64> &sourcePortDisplay() const { return display_; }

private:
  Core::CStringBuffer<64> app_;
  Core::CStringBuffer<64> device_;
  Core::CStringBuffer<64> display_;
};
} // namespace Presonus::UC
