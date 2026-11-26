#pragma once
#include "presonus/mixer/NumberPrepender.hpp"
#include <new>
namespace Presonus::Mixer {
// RTTI-proven original parent; original construction and ARM layout unresolved.
class FxReverbNumFormatter : public NumberPrepender {
public:
  // Independent source-port setup, not a recovered original constructor.
  struct SourcePortTag {};
  explicit FxReverbNumFormatter(SourcePortTag, std::uint8_t prefix)
      : NumberPrepender(prefix) {
    name = "reverbnum";
  }
  ~FxReverbNumFormatter() override;
  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }
};
} // namespace Presonus::Mixer
