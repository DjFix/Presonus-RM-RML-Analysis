#pragma once
#include "presonus/mixer/PreDelayFormatter.hpp"
#include <cstdint>
#include <new>
namespace Presonus::Mixer {
// RTTI-proven original parent; original construction and ARM layout unresolved.
class PreDelayFormatterT9 : public PreDelayFormatter {
public:
  // Independent source-port setup, not a recovered original constructor.
  struct SourcePortTag {};
  explicit PreDelayFormatterT9(SourcePortTag) : PreDelayFormatter() {
    name = "predelayT9";
  }
  // Native initialization writes byte +8 = 8; meaning is unresolved.
  std::uint8_t sourcePortInitializationByte() const {
    return initializationByte_;
  }
  ~PreDelayFormatterT9() override;
  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }

private:
  std::uint8_t initializationByte_ = 8;
};
} // namespace Presonus::Mixer
