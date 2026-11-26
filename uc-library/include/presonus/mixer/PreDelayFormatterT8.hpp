#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"
#include <cstdint>
#include <new>
namespace Presonus::Mixer {
// Original RTTI establishes this parent; native ARM layout remains unresolved.
class PreDelayFormatterT8 : public PreDelayFormatter {
public:
  struct SourcePortTag {};
  // Independent portable setup; no original constructor identity is claimed.
  explicit PreDelayFormatterT8(SourcePortTag) { name = "predelayT8"; }
  ~PreDelayFormatterT8() override;
  std::uint8_t sourcePortInitializationByte() const {
    return initializationByte_;
  }
  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }

private:
  // Original initializer writes byte +8 = 7; semantics are unresolved.
  std::uint8_t initializationByte_ = 7;
};
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT8>();
} // namespace Presonus::Mixer
