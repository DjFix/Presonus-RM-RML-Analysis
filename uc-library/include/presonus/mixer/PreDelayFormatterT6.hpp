#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"
#include <cstdint>
#include <new>
namespace Presonus::Mixer {
// Original RTTI establishes this parent; native ARM layout remains unresolved.
class PreDelayFormatterT6 : public PreDelayFormatter {
public:
  struct SourcePortTag {};
  // Independent portable setup; no original constructor identity is claimed.
  explicit PreDelayFormatterT6(SourcePortTag) { name = "predelayT6"; }
  ~PreDelayFormatterT6() override;
  std::uint8_t sourcePortInitializationByte() const {
    return initializationByte_;
  }
  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }

private:
  // Original initializer writes byte +8 = 5; semantics are unresolved.
  std::uint8_t initializationByte_ = 5;
};
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT6>();
} // namespace Presonus::Mixer
