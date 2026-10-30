#include "presonus/uc/activity_singleton.hpp"

namespace {
presonus::uc::NetworkActivityProjection initialActivityProjection() {
  presonus::uc::NetworkActivityProjection value{};
  // This independent opaque projection retains original ARM little-endian
  // byte meaning: size 136, reserved word zero, 128 zeroed activity bytes.
  value.bytes[0] = 136;
  return value;
}
} // namespace

namespace Presonus::UC {
NetworkActivityManager::NetworkActivityManager()
    : activity_(initialActivityProjection()), listeners_(0) {}
} // namespace Presonus::UC

// Official upstream definition supplies real C++ guard/registration semantics.
// It is source-provided Core, not a decompiled Core implementation.
DEFINE_STATIC_SINGLETON(Presonus::UC::NetworkActivityManager)

namespace presonus::uc {
Presonus::UC::NetworkActivityManager &sourceActivitySingleton() {
  return Core::Portable::StaticSingleton<
      Presonus::UC::NetworkActivityManager>::instance();
}
} // namespace presonus::uc
